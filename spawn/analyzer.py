"""
AgentKit — Task Analyzer
3-tier classifier that decides if a task needs multiple agents and which roles.

Tier 1: Keyword/structural heuristics (<5ms, no API)
Tier 2: Scoring + dependency inference (<10ms, no API)
Tier 3: Haiku LLM fallback (~50ms, ~$0.0003) for ambiguous cases
"""

from __future__ import annotations

import json
import os
import re
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from spawn.models import AnalysisResult

# ---------------------------------------------------------------------------
# Signal tables
# ---------------------------------------------------------------------------

# Conjunction signals — imply sequential multi-step work
CONJUNCTION_SIGNALS = [
    r"\band then\b", r"\bafter that\b", r"\bfollowed by\b",
    r"\balso make sure\b", r"\bthen review\b", r"\band test\b",
    r"\band deploy\b", r"\bthen verify\b", r"\bthen document\b",
    r"\bonce.*done\b", r"\bfinally\b.*\b(test|review|deploy)\b",
]

# Scope signals — imply large enough task to warrant multiple agents
SCOPE_SIGNALS = [
    r"\bfull feature\b", r"\bend[- ]to[- ]end\b", r"\bfrom scratch\b",
    r"\bentire\b", r"\bcomplete\b.*\b(implementation|system|module|service)\b",
    r"\bfull[- ]stack\b", r"\bproduction[- ]ready\b", r"\bwhole\b.*\b(feature|system)\b",
]

# Role keywords — map to subagent roles
ROLE_PATTERNS: dict[str, list[str]] = {
    "researcher": [
        r"\bresearch\b", r"\binvestigate\b", r"\banalyze\b", r"\bunderstand\b",
        r"\bfind all\b", r"\bexplore\b", r"\bauditing\b",
    ],
    "architect": [
        r"\bdesign\b", r"\barchitect\b", r"\bplan\b.*\b(the|a)\b", r"\bstructure\b",
        r"\bhow should\b", r"\bdata model\b", r"\bschema design\b", r"\bsystem design\b",
    ],
    "writer": [
        r"\bimplement\b", r"\bbuild\b", r"\bcreate\b", r"\bwrite\b.*\b(the|a)\b",
        r"\badd\b.*\b(feature|endpoint|function|class|module)\b",
        r"\bcode\b", r"\bdevelop\b",
    ],
    "tester": [
        r"\btest\b", r"\btests\b", r"\btesting\b", r"\bspec\b", r"\bcoverage\b",
        r"\bunit test\b", r"\bintegration test\b", r"\be2e\b", r"\bplaywright\b",
        r"\bcypress\b", r"\bjest\b", r"\bpytest\b",
    ],
    "security": [
        r"\bsecurity\b", r"\bsecure\b", r"\bvulnerabilit\b", r"\baudit\b",
        r"\bowasp\b", r"\bauth\b.*\bcheck\b", r"\bpenetration\b",
    ],
    "reviewer": [
        r"\breview\b", r"\bcheck\b.*\bcode\b", r"\bcode quality\b",
        r"\brefactor\b.*\breview\b", r"\blook.*over\b", r"\bfeedback\b",
    ],
}

# Dependency rules: role A must complete before role B
DEPENDENCY_RULES: list[tuple[str, str]] = [
    ("researcher", "architect"),   # research informs design
    ("researcher", "writer"),      # research informs implementation
    ("architect",  "writer"),      # design informs implementation
    ("writer",     "tester"),      # can't test before writing
    ("writer",     "reviewer"),    # can't review before writing
    ("writer",     "security"),    # can't audit before writing
    ("tester",     "reviewer"),    # reviewers look at tests too
]

# Minimum prompt length for multi-agent consideration
MIN_PROMPT_LENGTH = 120
CONFIDENCE_THRESHOLD = 0.55
HAIKU_FALLBACK_THRESHOLD = 0.40   # below this → call Haiku for clarity

# Role → skill IDs hints
ROLE_SKILL_HINTS: dict[str, list[str]] = {
    "researcher":  ["clean-code"],
    "architect":   ["clean-code", "rest-api"],
    "writer":      ["clean-code", "tdd-workflow"],
    "tester":      ["tdd-workflow", "pytest-workflow"],
    "reviewer":    ["clean-code", "code-review"],
    "security":    ["owasp-top10", "api-security"],
}

# Role → model
ROLE_MODELS: dict[str, str] = {
    "researcher": "claude-haiku-4-5-20251001",
    "architect":  "claude-opus-4-6",
    "writer":     "claude-haiku-4-5-20251001",
    "tester":     "claude-haiku-4-5-20251001",
    "reviewer":   "claude-sonnet-4-6",
    "security":   "claude-sonnet-4-6",
}

ROLE_MAX_TOKENS: dict[str, int] = {
    "researcher": 2048,
    "architect":  8192,
    "writer":     8192,
    "tester":     4096,
    "reviewer":   8192,
    "security":   4096,
}

ROLE_FRESH_CONTEXT: dict[str, bool] = {
    "reviewer":  True,
    "security":  True,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(prompt: str, is_subagent: bool = False) -> AnalysisResult:
    """
    Analyze a prompt and determine if multi-agent spawning is needed.
    Returns AnalysisResult with is_multi_agent=False for single-agent tasks.
    """
    # Never spawn from within a spawned agent — prevents infinite recursion
    if is_subagent:
        return AnalysisResult(
            is_multi_agent=False, strategy="single", confidence=1.0,
            detected_roles=[], subtask_hints=[],
            trigger_reason="skipped: already running as subagent",
            is_subagent=True,
        )

    # Very short prompts are never multi-agent
    if len(prompt.strip()) < MIN_PROMPT_LENGTH:
        return _single(reason="prompt too short for multi-agent task")

    # Tier 1 + 2: structural analysis
    result = _tier1_tier2(prompt)

    # Tier 3: Haiku fallback for ambiguous cases
    if result.confidence < HAIKU_FALLBACK_THRESHOLD and len(prompt) > 200:
        result = _haiku_fallback(prompt, result)

    return result


# ---------------------------------------------------------------------------
# Tier 1 + 2: Heuristic analysis
# ---------------------------------------------------------------------------

def _tier1_tier2(prompt: str) -> AnalysisResult:
    p = prompt.lower()
    score = 0.0
    reasons = []

    # --- Conjunction signals (each adds 0.2)
    conj_hits = sum(1 for pat in CONJUNCTION_SIGNALS if re.search(pat, p))
    if conj_hits:
        score += min(conj_hits * 0.2, 0.4)
        reasons.append(f"conjunction signals ({conj_hits})")

    # --- Scope signals (each adds 0.25)
    scope_hits = sum(1 for pat in SCOPE_SIGNALS if re.search(pat, p))
    if scope_hits:
        score += min(scope_hits * 0.25, 0.5)
        reasons.append(f"scope signals ({scope_hits})")

    # --- Numbered / bulleted list detection (0.3 if 3+ items)
    numbered = re.findall(r"(?:^|\n)\s*(?:\d+[.)]\s+|-\s+|\*\s+)", prompt)
    if len(numbered) >= 3:
        score += 0.3
        reasons.append(f"structured list ({len(numbered)} items)")

    # --- Detect roles
    detected_roles: list[str] = []
    for role, patterns in ROLE_PATTERNS.items():
        if any(re.search(pat, p) for pat in patterns):
            detected_roles.append(role)

    # Ensure at least "writer" is always present for implementation tasks
    if not detected_roles and re.search(r"\b(build|create|implement|add|make)\b", p):
        detected_roles.append("writer")

    # 2+ distinct roles is a strong multi-agent signal
    if len(detected_roles) >= 2:
        score += 0.3 + (len(detected_roles) - 2) * 0.1
        reasons.append(f"roles detected: {', '.join(detected_roles)}")

    # --- Determine strategy
    strategy = _infer_strategy(detected_roles)

    # --- Build subtask hints
    subtask_hints = _build_subtask_hints(prompt, detected_roles)

    is_multi = score >= CONFIDENCE_THRESHOLD and len(detected_roles) >= 2

    return AnalysisResult(
        is_multi_agent=is_multi,
        strategy=strategy if is_multi else "single",
        confidence=min(score, 1.0),
        detected_roles=detected_roles,
        subtask_hints=subtask_hints,
        trigger_reason=", ".join(reasons) if reasons else "no signals detected",
    )


def _infer_strategy(roles: list[str]) -> str:
    """Determine execution strategy from role set."""
    if len(roles) <= 1:
        return "single"
    # Check if any role has a dependency on another detected role
    deps = [(a, b) for a, b in DEPENDENCY_RULES if a in roles and b in roles]
    if not deps:
        return "parallel"
    # Check if all deps form a linear chain
    ordered = _topological_sort(roles, deps)
    if ordered:
        # If every role depends on the previous → sequential
        return "sequential" if len(deps) == len(roles) - 1 else "dag"
    return "dag"


def _topological_sort(roles: list[str], deps: list[tuple[str, str]]) -> list[str]:
    """Simple topological sort. Returns ordered list or empty on cycle."""
    from collections import defaultdict, deque
    in_degree = {r: 0 for r in roles}
    graph = defaultdict(list)
    for a, b in deps:
        graph[a].append(b)
        in_degree[b] = in_degree.get(b, 0) + 1
    queue = deque(r for r in roles if in_degree[r] == 0)
    result = []
    while queue:
        node = queue.popleft()
        result.append(node)
        for nxt in graph[node]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                queue.append(nxt)
    return result if len(result) == len(roles) else []


def _build_subtask_hints(prompt: str, roles: list[str]) -> list[str]:
    """Generate a short subtask description per role."""
    hints = []
    for role in roles:
        if role == "researcher":
            hints.append(f"Explore and understand the codebase relevant to: {prompt[:100]}")
        elif role == "architect":
            hints.append(f"Design the architecture and data model for: {prompt[:100]}")
        elif role == "writer":
            hints.append(f"Implement the solution for: {prompt[:120]}")
        elif role == "tester":
            hints.append(f"Write comprehensive tests for the implementation of: {prompt[:100]}")
        elif role == "reviewer":
            hints.append(f"Review the code quality, correctness, and edge cases for: {prompt[:100]}")
        elif role == "security":
            hints.append(f"Perform a security audit of the implementation for: {prompt[:100]}")
    return hints


# ---------------------------------------------------------------------------
# Tier 3: Haiku LLM fallback
# ---------------------------------------------------------------------------

def _haiku_fallback(prompt: str, prior: AnalysisResult) -> AnalysisResult:
    """Call Haiku to clarify if this is a multi-agent task."""
    try:
        import anthropic
        client = anthropic.Anthropic()
        roles_available = list(ROLE_PATTERNS.keys())

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=(
                "You are a task analyzer for an AI coding assistant. "
                "You decide if a user's coding task requires multiple specialized agents or just one. "
                "Available agent roles: " + ", ".join(roles_available) + ". "
                "Respond ONLY with valid JSON — no prose, no markdown."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Analyze this coding task:\n\n{prompt}\n\n"
                    "Reply with JSON:\n"
                    '{"is_multi_agent": bool, "roles": ["role1","role2",...], '
                    '"strategy": "parallel"|"sequential"|"dag", '
                    '"reasoning": "one sentence why"}'
                ),
            }],
        )

        data = json.loads(response.content[0].text.strip())
        roles = [r for r in data.get("roles", []) if r in ROLE_PATTERNS]
        is_multi = bool(data.get("is_multi_agent", False)) and len(roles) >= 2

        return AnalysisResult(
            is_multi_agent=is_multi,
            strategy=data.get("strategy", "sequential") if is_multi else "single",
            confidence=0.85,   # Haiku answered — high confidence
            detected_roles=roles if is_multi else prior.detected_roles,
            subtask_hints=_build_subtask_hints(prompt, roles),
            trigger_reason=f"haiku: {data.get('reasoning', '')}",
        )

    except Exception:
        # If Haiku call fails, fall back to prior result with single-agent
        return _single(reason="haiku fallback failed — defaulting to single agent")


def _single(reason: str = "") -> AnalysisResult:
    return AnalysisResult(
        is_multi_agent=False, strategy="single", confidence=1.0,
        detected_roles=[], subtask_hints=[], trigger_reason=reason,
    )
