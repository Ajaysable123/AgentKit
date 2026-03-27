"""
AgentKit — Platform Adapter: Claude Code (Tier 1 — Native)
Full implementation: SKILL.md native, all hooks, memory layer.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from platform.adapter import (
    AgentKitConfig, InstallResult, PlatformAdapter,
    Skill, extract_level, register,
)


@register
class ClaudeCodeAdapter(PlatformAdapter):
    PLATFORM_ID   = "claude-code"
    PLATFORM_NAME = "Claude Code"
    TIER = 1

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect(self) -> bool:
        import shutil as sh
        home = Path.home()
        return (
            (home / ".claude").exists()
            or (self.project_root / ".claude").exists()
            or sh.which("claude") is not None
        )

    # ------------------------------------------------------------------
    # Skill conversion (native — no conversion needed)
    # ------------------------------------------------------------------

    def convert_skill(self, skill: Skill) -> str:
        return skill.content   # SKILL.md is the native format

    # ------------------------------------------------------------------
    # Install
    # ------------------------------------------------------------------

    def install(self, skills: list[Skill], config: AgentKitConfig) -> InstallResult:
        result = InstallResult(platform=self.PLATFORM_ID, success=True)

        # 1. Write SKILL.md files to .claude/agentkit/skills/
        skills_dir = self.project_root / ".claude" / "agentkit" / "skills"
        for skill in skills:
            dest_dir = skills_dir / skill.category
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / f"{skill.id}.md"   # unique per skill, not shared SKILL.md
            dest.write_text(skill.content)
            result.files_written.append(str(dest))

        # 2. Merge hooks into .claude/settings.json
        settings_path = self.project_root / ".claude" / "settings.json"
        settings = {}
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text())
            except Exception:
                pass

        # Resolve package root: prefer explicit config, then env var, then relative to this file
        agentkit_home = config.agentkit_home or os.environ.get("AGENTKIT_HOME") or str(
            Path(__file__).parent.parent.parent.resolve()
        )
        settings = _merge_hooks(settings, agentkit_home)
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps(settings, indent=2))
        result.files_written.append(str(settings_path))

        # 3. Write .agentkit.yaml config
        config_path = self.project_root / ".agentkit.yaml"
        config_path.write_text(_render_agentkit_yaml(config))
        result.files_written.append(str(config_path))

        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _merge_hooks(settings: dict, agentkit_home: str) -> dict:
    """Merge AgentKit hooks into existing settings.json without clobbering."""
    hooks = settings.setdefault("hooks", {})

    def _ensure_hook(event: str, matcher: str | None, command: str) -> None:
        buckets = hooks.setdefault(event, [])
        for bucket in buckets:
            for h in bucket.get("hooks", []):
                if command in h.get("command", ""):
                    return   # already present
        entry: dict = {"hooks": [{"type": "command", "command": command}]}
        if matcher:
            entry["matcher"] = matcher
        buckets.append(entry)

    H = agentkit_home
    _ensure_hook("UserPromptSubmit", None, f"python3 {H}/hooks/spawn_hook.py")
    _ensure_hook("UserPromptSubmit", None, f"python3 {H}/hooks/skill_router_hook.py")
    _ensure_hook("UserPromptSubmit", None, f"bash {H}/hooks/session_start.sh")
    _ensure_hook("UserPromptSubmit", None, f"bash {H}/hooks/memory_inject.sh")
    _ensure_hook("UserPromptSubmit", None, f"bash {H}/hooks/model_router_hook.sh")
    _ensure_hook("UserPromptSubmit", None, f"bash {H}/hooks/thinking_budget.sh")
    _ensure_hook("UserPromptSubmit", None, f"bash {H}/hooks/workflow_state.sh")
    _ensure_hook("PreToolUse",  "Edit|Write|MultiEdit", f"bash {H}/hooks/forced_eval.sh")
    _ensure_hook("PreToolUse",  "Edit|Write|MultiEdit", f"bash {H}/hooks/plan_gate.sh")
    _ensure_hook("PostToolUse", "Read",                 f"bash {H}/hooks/research_gate.sh")
    _ensure_hook("PostToolUse", "Read|Edit|Write|Bash|MultiEdit", f"bash {H}/hooks/memory_recorder.sh")
    _ensure_hook("PostToolUse", "Read|Edit|Write|Bash|MultiEdit", f"bash {H}/hooks/cost_dashboard.sh")
    _ensure_hook("PostToolUse", "Edit|Write|MultiEdit", f"bash {H}/hooks/quality_gates.sh")
    _ensure_hook("Stop",        None,                   f"bash {H}/hooks/session_end.sh")

    return settings


def _render_agentkit_yaml(config: AgentKitConfig) -> str:
    return f"""\
# AgentKit configuration
# Generated by: npx agentkit init

model_routing:
  enabled: {str(config.model_routing_enabled).lower()}
  default: {config.default_model}
  subagent: {config.subagent_model}

memory:
  enabled: {str(config.memory_enabled).lower()}

quality_gates:
  enabled: {str(config.quality_gates_enabled).lower()}
  on_edit: true
  fail_behavior: warn

workflow:
  enabled: {str(config.workflow_enforcement).lower()}
"""
