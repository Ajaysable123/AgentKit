"""
AgentKit — Spawn Planner
Converts an AnalysisResult into a concrete SpawnPlan with task IDs,
model assignments, skill hints, and dependency edges.
"""

from __future__ import annotations

import os
import sys
import uuid

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from spawn.models import AgentTask, SpawnPlan, AnalysisResult
from spawn.analyzer import (
    DEPENDENCY_RULES,
    ROLE_MODELS,
    ROLE_MAX_TOKENS,
    ROLE_SKILL_HINTS,
    ROLE_FRESH_CONTEXT,
)

# Rough token budget per role (for estimated_tokens calc)
_ROLE_TOKEN_ESTIMATE: dict[str, int] = {
    "researcher": 3000,
    "architect":  6000,
    "writer":     7000,
    "tester":     4000,
    "reviewer":   5000,
    "security":   4000,
}


def build_plan(prompt: str, analysis: AnalysisResult) -> SpawnPlan:
    """
    Convert an AnalysisResult into a concrete SpawnPlan.

    - Assigns task_ids (t1, t2, …) in topological order
    - Resolves depends_on edges from DEPENDENCY_RULES
    - Assigns model, skills, max_tokens, fresh_context per role
    - Builds a short description per task from subtask_hints
    """
    roles = analysis.detected_roles

    # Assign task_ids in a stable topological order so dependencies make sense
    ordered_roles = _topological_order(roles)
    role_to_tid: dict[str, str] = {
        role: f"t{i+1}" for i, role in enumerate(ordered_roles)
    }

    tasks: list[AgentTask] = []
    for role in ordered_roles:
        tid = role_to_tid[role]

        # Resolve depends_on: which other detected roles must finish first?
        deps = [
            role_to_tid[a]
            for a, b in DEPENDENCY_RULES
            if b == role and a in role_to_tid
        ]

        # Find the subtask hint for this role
        hint_prefix = _role_hint_prefix(role)
        description = next(
            (h for h in analysis.subtask_hints if hint_prefix in h.lower()),
            f"{role.capitalize()} task for: {prompt[:100]}",
        )

        tasks.append(AgentTask(
            task_id=tid,
            role=role,
            model=ROLE_MODELS.get(role, "claude-sonnet-4-6"),
            skills=ROLE_SKILL_HINTS.get(role, []),
            description=description,
            depends_on=deps,
            fresh_context=ROLE_FRESH_CONTEXT.get(role, False),
            max_tokens=ROLE_MAX_TOKENS.get(role, 4096),
        ))

    estimated_tokens = sum(
        _ROLE_TOKEN_ESTIMATE.get(r, 4000) for r in roles
    )

    return SpawnPlan(
        plan_id=str(uuid.uuid4())[:8],
        original_prompt=prompt,
        strategy=analysis.strategy,
        tasks=tasks,
        estimated_tokens=estimated_tokens,
        reasoning=analysis.trigger_reason,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _topological_order(roles: list[str]) -> list[str]:
    """Return roles in dependency-respecting order (sources first)."""
    from collections import defaultdict, deque

    deps = [(a, b) for a, b in DEPENDENCY_RULES if a in roles and b in roles]
    in_degree = {r: 0 for r in roles}
    graph: dict[str, list[str]] = defaultdict(list)
    for a, b in deps:
        graph[a].append(b)
        in_degree[b] += 1

    queue = deque(r for r in roles if in_degree[r] == 0)
    result: list[str] = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for nxt in graph[node]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)

    # Append any roles not reached (shouldn't happen without cycles)
    for r in roles:
        if r not in result:
            result.append(r)
    return result


def _role_hint_prefix(role: str) -> str:
    """Return a keyword fragment to match against subtask_hints."""
    return {
        "researcher": "explore",
        "architect":  "design",
        "writer":     "implement",
        "tester":     "write comprehensive",
        "reviewer":   "review",
        "security":   "security audit",
    }.get(role, role)
