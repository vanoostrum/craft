# Copyright (C) 2026 Theo van Oostrum
"""PreToolUse hook: block pstack skills until bstack is loaded in the session.

Claude Code runs this before every Skill tool call and passes the call as JSON
on stdin. A `pstack:` skill is denied unless the transcript shows that
`craft:bstack` was loaded after the last compaction, by the Skill tool or by
`/craft:bstack`. The name `bstack`, from before the plugin, counts too.
"""

import json
import sys
from pathlib import Path
from typing import Any

BUDGET_SKILL = "craft:bstack"
BUDGET_SKILLS = (BUDGET_SKILL, "bstack")
GATED_PREFIX = "pstack:"
SLASH_COMMANDS = tuple(
    f"<command-name>/{name}</command-name>" for name in BUDGET_SKILLS
)
REASON = (
    f"Load the {BUDGET_SKILL} skill with the Skill tool first, follow it, "
    "then retry this pstack skill."
)


def loads_budget_skill(entry: dict[str, Any]) -> bool:
    """Return whether a transcript entry loads the budget skill."""
    content = (entry.get("message") or {}).get("content")
    if entry.get("type") == "user":
        if isinstance(content, str):
            return any(command in content for command in SLASH_COMMANDS)
        texts = [
            block.get("text") or ""
            for block in content or []
            if block.get("type") == "text"
        ]
        return any(command in text for text in texts for command in SLASH_COMMANDS)
    if entry.get("type") == "assistant" and isinstance(content, list):
        return any(
            block.get("type") == "tool_use"
            and block.get("name") == "Skill"
            and (block.get("input") or {}).get("skill") in BUDGET_SKILLS
            for block in content
        )
    return False


def budget_skill_loaded(transcript: Path) -> bool:
    """Return whether the budget skill was loaded since the last compaction."""
    loaded = False
    for line in transcript.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        if entry.get("subtype") == "compact_boundary":
            loaded = False
        elif loads_budget_skill(entry):
            loaded = True
    return loaded


def main() -> None:
    """Deny a pstack Skill call when the budget skill is not loaded."""
    call = json.load(sys.stdin)
    skill = (call.get("tool_input") or {}).get("skill") or ""
    if not skill.startswith(GATED_PREFIX):
        return
    transcript = Path(call.get("transcript_path") or "")
    if transcript.is_file() and budget_skill_loaded(transcript):
        return
    decision = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": REASON,
        },
    }
    sys.stdout.write(json.dumps(decision) + "\n")


if __name__ == "__main__":
    main()
