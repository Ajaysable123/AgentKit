"""
AgentKit — Spawn Models
Dataclasses for dynamic agent spawn plans.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------

@dataclass
class AgentTask:
    """A single agent in a spawn plan."""
    task_id: str                      # "t1", "t2", etc — used in depends_on
    role: str                         # "writer"|"reviewer"|"researcher"|"architect"|"tester"|"security"
    model: str                        # claude model constant
    skills: list[str]                 # skill IDs to hint at in the instruction
    description: str                  # what this agent should do
    depends_on: list[str]             # task_ids that must complete first
    fresh_context: bool = False       # True → spawn with no inherited context
    max_tokens: int = 4096
    files: list[str] = field(default_factory=list)  # specific files to focus on


@dataclass
class SpawnPlan:
    """Complete orchestration plan for a multi-agent task."""
    plan_id: str
    original_prompt: str
    strategy: str                     # "parallel" | "sequential" | "dag"
    tasks: list[AgentTask]
    estimated_tokens: int
    reasoning: str                    # why this decomposition was chosen
    spawned_at: float = field(default_factory=time.time)

    @property
    def parallel_groups(self) -> list[list[str]]:
        """Return task_ids grouped by execution wave (tasks with no unmet deps)."""
        completed: set[str] = set()
        remaining = [t for t in self.tasks]
        groups: list[list[str]] = []
        while remaining:
            ready = [t for t in remaining if all(d in completed for d in t.depends_on)]
            if not ready:
                break
            groups.append([t.task_id for t in ready])
            completed.update(t.task_id for t in ready)
            remaining = [t for t in remaining if t.task_id not in completed]
        return groups

    @property
    def agent_count(self) -> int:
        return len(self.tasks)


@dataclass
class AnalysisResult:
    """Output of the task analyzer."""
    is_multi_agent: bool
    strategy: str                     # "single" | "parallel" | "sequential" | "dag"
    confidence: float                 # 0.0–1.0
    detected_roles: list[str]         # roles needed e.g. ["writer", "tester", "reviewer"]
    subtask_hints: list[str]          # coarse descriptions per role
    trigger_reason: str               # human-readable why
    is_subagent: bool = False         # True → skip spawning (already a subagent)
