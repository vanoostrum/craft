# Copyright (C) 2026 Theo van Oostrum
"""PreToolUse hook: a spec session never runs the build steps.

Claude Code runs this before every Skill tool call and passes the call as JSON
on stdin. A Skill call to `craft:build`, `craft:review`, or `craft:merge` is
denied in a spec session.

The session's step is the first step skill it loads, by the Skill tool or by a
typed `/craft:<step>` command. A spec session is a session whose step is
`craft:spec`. A later typed `/craft:build`, `/craft:review`, or `/craft:merge`
makes it a build session: that is the owner's own choice. Other skills, such as
`craft:rules`, do not decide the step, and a compaction does not reset it.
Without a readable transcript the hook cannot tell, so it allows the call.
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

SPEC_STEP = "craft:spec"
BUILD_STEPS = ("craft:build", "craft:review", "craft:merge")
STEPS = (
    "craft:brainstorm",
    "craft:setup",
    "craft:plan",
    SPEC_STEP,
    "craft:design",
    *BUILD_STEPS,
    "craft:next",
)
SLASH_COMMAND = re.compile(r"<command-name>/([^<]+)</command-name>")
REASON = (
    "This session ran craft:spec, so it does not run craft:build, craft:review, "
    "or craft:merge. Run craft:next instead: it starts the build in a new "
    "session. Then end this session."
)


def typed_step(entry: dict[str, Any]) -> str | None:
    """Return the step skill that a user entry types as a slash command."""
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        texts = [content]
    else:
        texts = [
            block.get("text") or ""
            for block in content or []
            if isinstance(block, dict) and block.get("type") == "text"
        ]
    for text in texts:
        for name in SLASH_COMMAND.findall(text):
            if name in STEPS:
                return name
    return None


def called_steps(entry: dict[str, Any]) -> list[str]:
    """Return the step skills that an assistant entry loads with the Skill tool."""
    content = (entry.get("message") or {}).get("content")
    if not isinstance(content, list):
        return []
    return [
        name
        for block in content
        if isinstance(block, dict)
        and block.get("type") == "tool_use"
        and block.get("name") == "Skill"
        and (name := (block.get("input") or {}).get("skill")) in STEPS
    ]


def session_step(transcript: Path) -> str | None:
    """Return the session's step: its first step skill, or a typed build step."""
    step = None
    for line in transcript.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        if entry.get("type") == "user":
            typed = typed_step(entry)
            if typed and (step is None or typed in BUILD_STEPS):
                step = typed
        elif entry.get("type") == "assistant" and step is None:
            step = next(iter(called_steps(entry)), None)
    return step


def main() -> None:
    """Deny a build step Skill call in a spec session."""
    call = json.load(sys.stdin)
    skill = (call.get("tool_input") or {}).get("skill") or ""
    if skill not in BUILD_STEPS:
        return
    transcript = Path(call.get("transcript_path") or "")
    if not transcript.is_file() or session_step(transcript) != SPEC_STEP:
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
