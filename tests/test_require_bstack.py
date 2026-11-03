# Copyright (C) 2026 Theo van Oostrum
"""The bstack hook blocks pstack skills until sous:bstack is loaded."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "plugins" / "sous" / "hooks" / "require_bstack.py"


def skill_call(name: str) -> dict[str, Any]:
    """Return a transcript entry in which the assistant calls the Skill tool."""
    block = {"type": "tool_use", "name": "Skill", "input": {"skill": name}}
    return {"type": "assistant", "message": {"content": [block]}}


def slash_command(name: str) -> dict[str, Any]:
    """Return a transcript entry in which the user types a slash command."""
    text = f"<command-name>/{name}</command-name>"
    return {"type": "user", "message": {"content": text}}


def run_hook(tmp_path: Path, skill: str, entries: list[dict[str, Any]]) -> str:
    """Run the hook for a Skill call after `entries`, and return its output."""
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(
        "".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8"
    )
    call = {"tool_input": {"skill": skill}, "transcript_path": str(transcript)}
    result = subprocess.run(  # noqa: S603 - runs the hook under test.
        [sys.executable, str(HOOK)],
        input=json.dumps(call),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


@pytest.mark.parametrize(
    "entry",
    [
        skill_call("sous:bstack"),
        skill_call("bstack"),
        slash_command("sous:bstack"),
        slash_command("bstack"),
    ],
)
def test_pstack_runs_after_bstack(tmp_path: Path, entry: dict[str, Any]) -> None:
    """A pstack skill runs once bstack is loaded, by its plugin or its old name."""
    assert run_hook(tmp_path, "pstack:how", [entry]) == ""


def test_pstack_is_denied_without_bstack(tmp_path: Path) -> None:
    """A pstack skill is denied, and the reason names sous:bstack."""
    output = json.loads(run_hook(tmp_path, "pstack:how", [skill_call("sous:spec")]))
    decision = output["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "sous:bstack" in decision["permissionDecisionReason"]


def test_compaction_unloads_bstack(tmp_path: Path) -> None:
    """After a compaction, bstack must be loaded again."""
    entries = [skill_call("sous:bstack"), {"subtype": "compact_boundary"}]
    assert "deny" in run_hook(tmp_path, "pstack:how", entries)


def test_other_skills_pass(tmp_path: Path) -> None:
    """Skills outside pstack are never blocked."""
    assert run_hook(tmp_path, "sous:spec", []) == ""


def test_plugin_runs_the_hook_before_each_skill() -> None:
    """The plugin runs the hook before every Skill call."""
    hooks_file = HOOK.parent / "hooks.json"
    groups = json.loads(hooks_file.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    commands = [
        hook["command"]
        for group in groups
        if group["matcher"] == "Skill"
        for hook in group["hooks"]
    ]
    assert commands == ['python3 "${CLAUDE_PLUGIN_ROOT}/hooks/require_bstack.py"']
