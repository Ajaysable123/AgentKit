"""
AgentKit — Spawn Hook
UserPromptSubmit hook: analyzes the incoming prompt and, if it warrants
multiple agents, injects a SpawnPlan into Claude's context via stdout.

Claude Code hook stdin format:
{
  "session_id": "...",
  "transcript_path": "...",
  "cwd": "...",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "the user's prompt text"
}

Output contract:
  - stdout: markdown block (Claude sees it as extra context)
  - stderr: debug/log lines (not shown to Claude)
  - exit 0: always (hook failures must be non-blocking)
"""

from __future__ import annotations

import json
import os
import sys

# Resolve repo root so imports work regardless of cwd
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from spawn.analyzer import analyze
from spawn.planner  import build_plan
from spawn.renderer import render


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return

        data = json.loads(raw)
        prompt = data.get("prompt", "").strip()
        if not prompt:
            return

        # Detect if we're already running inside a spawned sub-agent
        is_subagent = (
            os.environ.get("AGENTKIT_IS_SUBAGENT", "").lower() in ("1", "true", "yes")
        )

        analysis = analyze(prompt, is_subagent=is_subagent)

        if not analysis.is_multi_agent:
            _debug(
                f"spawn_hook: single-agent ({analysis.trigger_reason}, "
                f"conf={analysis.confidence:.2f})"
            )
            return

        _debug(
            f"spawn_hook: multi-agent detected — "
            f"roles={analysis.detected_roles}, strategy={analysis.strategy}, "
            f"conf={analysis.confidence:.2f}"
        )

        plan = build_plan(prompt, analysis)
        output = render(plan)
        sys.stdout.write(output + "\n")

    except Exception as exc:
        # Never crash Claude — silently swallow errors
        _debug(f"spawn_hook: error — {exc}")


def _debug(msg: str) -> None:
    print(msg, file=sys.stderr)


if __name__ == "__main__":
    main()
