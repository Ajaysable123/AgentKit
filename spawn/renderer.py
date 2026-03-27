"""
AgentKit — Spawn Renderer
Renders a SpawnPlan into a Claude-readable markdown block that is injected
into the conversation via the UserPromptSubmit hook stdout.

Claude reads this block and understands:
  - How many agents are needed and why
  - Execution order / wave groupings
  - What each agent should do (role, model, description)
  - Which tasks depend on which
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from spawn.models import SpawnPlan, AgentTask

# Strategy → human-readable label
_STRATEGY_LABEL = {
    "parallel":   "run all agents in parallel",
    "sequential": "run agents one after another",
    "dag":        "run agents in dependency waves",
    "single":     "single agent",
}


def render(plan: SpawnPlan) -> str:
    """Return the full markdown injection string for the spawn plan."""
    lines: list[str] = []

    lines.append("<!-- AGENTKIT:SPAWN_PLAN -->")
    lines.append(f"## AgentKit — Spawn Plan `{plan.plan_id}`")
    lines.append("")
    lines.append(
        f"**Strategy:** {plan.strategy} "
        f"({_STRATEGY_LABEL.get(plan.strategy, plan.strategy)})  "
    )
    lines.append(f"**Agents:** {plan.agent_count}  ")
    lines.append(f"**Est. tokens:** ~{plan.estimated_tokens:,}  ")
    lines.append(f"**Reason:** {plan.reasoning}")
    lines.append("")

    # Execution waves
    waves = plan.parallel_groups
    if len(waves) > 1:
        lines.append("### Execution Waves")
        lines.append("")
        for i, wave in enumerate(waves, 1):
            task_list = ", ".join(wave)
            lines.append(f"**Wave {i}:** {task_list}")
        lines.append("")

    # Task table
    lines.append("### Tasks")
    lines.append("")
    lines.append("| ID | Role | Model | Depends On | Description |")
    lines.append("|----|------|-------|------------|-------------|")
    for task in plan.tasks:
        deps = ", ".join(task.depends_on) if task.depends_on else "—"
        desc = task.description[:80].replace("|", "\\|")
        model_short = _short_model(task.model)
        lines.append(
            f"| {task.task_id} | {task.role} | {model_short} | {deps} | {desc} |"
        )
    lines.append("")

    # Full task instructions
    lines.append("### Agent Instructions")
    lines.append("")
    for task in plan.tasks:
        lines.append(_render_task(task))

    lines.append("<!-- /AGENTKIT:SPAWN_PLAN -->")
    lines.append("")
    lines.append(
        "> **AgentKit:** Use the Agent tool to spawn the agents above according to "
        "the execution waves. Pass `is_subagent=True` in the environment / system "
        "prompt of each spawned agent so they do not recursively re-spawn."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _render_task(task: AgentTask) -> str:
    skills_str = ", ".join(task.skills) if task.skills else "general"
    fresh = " *(fresh context)*" if task.fresh_context else ""
    deps = (
        f"\n- **Wait for:** {', '.join(task.depends_on)}"
        if task.depends_on else ""
    )
    return (
        f"#### `{task.task_id}` — {task.role.capitalize()}{fresh}\n"
        f"- **Model:** `{task.model}`\n"
        f"- **Max tokens:** {task.max_tokens:,}\n"
        f"- **Skills:** {skills_str}"
        f"{deps}\n"
        f"- **Task:** {task.description}\n"
    )


def _short_model(model: str) -> str:
    """Shorten model ID for table display."""
    return (
        model
        .replace("claude-haiku-4-5-20251001", "haiku-4.5")
        .replace("claude-sonnet-4-6", "sonnet-4.6")
        .replace("claude-opus-4-6", "opus-4.6")
    )
