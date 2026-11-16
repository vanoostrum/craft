# Copyright (C) 2026 Theo van Oostrum
"""A spec session never runs the build: the hook and the skill text say so."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.test_one_shot_lanes import section, skill
from tests.test_require_bstack import skill_call, slash_command

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "plugins" / "craft" / "hooks" / "one_step_per_session.py"
BUILD_STEPS = ["craft:build", "craft:review", "craft:merge"]
COMPACTION = {"subtype": "compact_boundary"}


def run_hook(tmp_path: Path, skill_name: str, entries: list[dict[str, Any]]) -> str:
    """Run the hook for a Skill call after `entries`, and return its output."""
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(
        "".join(json.dumps(entry) + "\n" for entry in entries), encoding="utf-8"
    )
    return run_call(
        {"tool_input": {"skill": skill_name}, "transcript_path": str(transcript)}
    )


def run_call(call: dict[str, Any]) -> str:
    """Run the hook with `call` on stdin, and return its output."""
    result = subprocess.run(  # noqa: S603 - runs the hook under test.
        [sys.executable, str(HOOK)],
        input=json.dumps(call),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def user_text(text: str) -> dict[str, Any]:
    """Return a transcript entry in which the user writes `text`."""
    return {"type": "user", "message": {"content": text}}


def assert_denied(output: str) -> None:
    """Assert that the hook denied the call, and that the reason names the way on."""
    decision = json.loads(output)["hookSpecificOutput"]
    assert decision["hookEventName"] == "PreToolUse"
    assert decision["permissionDecision"] == "deny"
    reason = decision["permissionDecisionReason"]
    assert "craft:next" in reason
    assert "new session" in reason


SPEC_SESSIONS = {
    "skill tool": [skill_call("craft:rules"), skill_call("craft:spec")],
    "slash command": [slash_command("craft:spec"), skill_call("craft:rules")],
    "after compaction": [skill_call("craft:spec"), COMPACTION],
    "rules and bstack first": [
        skill_call("craft:rules"),
        skill_call("craft:bstack"),
        skill_call("craft:spec"),
    ],
    "typed design": [skill_call("craft:spec"), slash_command("craft:design")],
    "typed next": [skill_call("craft:spec"), slash_command("craft:next")],
}


@pytest.mark.parametrize("step", BUILD_STEPS)
@pytest.mark.parametrize("session", sorted(SPEC_SESSIONS))
def test_build_steps_are_denied_in_a_spec_session(
    tmp_path: Path, session: str, step: str
) -> None:
    """In a spec session, build, review, and merge are denied, with the way on."""
    assert_denied(run_hook(tmp_path, step, SPEC_SESSIONS[session]))


OTHER_SESSIONS = {
    "build session": [
        skill_call("craft:build"),
        skill_call("craft:review"),
        skill_call("craft:merge"),
    ],
    "plan session": [skill_call("craft:plan"), skill_call("craft:spec")],
    "typed plan": [slash_command("craft:plan"), skill_call("craft:spec")],
    "typed build": [skill_call("craft:spec"), slash_command("craft:build")],
    "typed review": [skill_call("craft:spec"), slash_command("craft:review")],
    "typed merge": [skill_call("craft:spec"), slash_command("craft:merge")],
    "no step": [skill_call("craft:rules"), skill_call("craft:bstack")],
    "mention only": [
        user_text("Run craft:build on CRAFT-1. Its craft:spec is approved."),
        user_text("Use the Skill tool with craft:spec next."),
    ],
}


@pytest.mark.parametrize("step", BUILD_STEPS)
@pytest.mark.parametrize("session", sorted(OTHER_SESSIONS))
def test_build_steps_run_outside_a_spec_session(
    tmp_path: Path, session: str, step: str
) -> None:
    """Outside a spec session, build, review, and merge are allowed."""
    assert run_hook(tmp_path, step, OTHER_SESSIONS[session]) == ""


@pytest.mark.parametrize(
    "skill_name", ["craft:next", "craft:design", "craft:rules", "pstack:how"]
)
def test_other_skills_run_in_a_spec_session(tmp_path: Path, skill_name: str) -> None:
    """A spec session can load every other skill, such as craft:next."""
    assert run_hook(tmp_path, skill_name, [skill_call("craft:spec")]) == ""


@pytest.mark.parametrize("path", [None, "", "missing.jsonl"])
def test_without_a_transcript_the_call_is_allowed(
    tmp_path: Path, path: str | None
) -> None:
    """Without a readable transcript, the hook cannot tell, so it allows the call."""
    call: dict[str, Any] = {"tool_input": {"skill": "craft:build"}}
    if path is not None:
        call["transcript_path"] = str(tmp_path / path) if path else ""
    assert run_call(call) == ""


def test_broken_lines_are_skipped(tmp_path: Path) -> None:
    """Lines that are not JSON objects do not stop the hook from finding the step."""
    transcript = tmp_path / "session.jsonl"
    transcript.write_text(
        "not json\n[1]\n" + json.dumps(skill_call("craft:spec")) + "\n",
        encoding="utf-8",
    )
    call = {"tool_input": {"skill": "craft:build"}, "transcript_path": str(transcript)}
    assert_denied(run_call(call))


def test_slash_command_in_text_blocks_counts(tmp_path: Path) -> None:
    """A typed command counts when the user message holds a list of text blocks."""
    block = {"type": "text", "text": "<command-name>/craft:spec</command-name>"}
    entry = {"type": "user", "message": {"content": [block]}}
    assert_denied(run_hook(tmp_path, "craft:build", [entry]))


def test_plugin_runs_the_hook_before_each_skill() -> None:
    """The plugin runs the hook on PreToolUse for Skill, next to the bstack hook."""
    hooks_file = HOOK.parent / "hooks.json"
    groups = json.loads(hooks_file.read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    commands = [
        hook["command"]
        for group in groups
        if group["matcher"] == "Skill"
        for hook in group["hooks"]
    ]
    assert commands == [
        'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/require_bstack.py"',
        'python3 "${CLAUDE_PLUGIN_ROOT}/hooks/one_step_per_session.py"',
    ]


def after_approval() -> str:
    """Return the After approval section of `craft:spec`."""
    return section(skill("spec"), "After approval")


def spec_gate_step() -> str:
    """Return step 8, Gate, of `craft:spec`."""
    return skill("spec").split("\n8. **Gate.**", 1)[1].split("\n## ", 1)[0]


@pytest.mark.parametrize("text", [after_approval, spec_gate_step])
def test_spec_ends_at_the_handoff(text: Any) -> None:
    """The spec step says that its session never runs the build steps."""
    body = text()
    for step in BUILD_STEPS:
        assert f"`{step}`" in body
    assert "even when the request" in body
    assert "`craft:next` starts the build in a new session" in body


def one_step_rule() -> str:
    """Return the One step per session rule of `craft:rules`."""
    rules = section(skill("rules"), "Rules for every step")
    return rules.split("- **One step per session.**", 1)[1].split("\n- **", 1)[0]


def work_on_paragraph() -> str:
    """Return the Flow paragraph of `craft:rules` on "work on"."""
    flow = section(skill("rules"), "Flow")
    return next(p for p in flow.split("\n\n") if p.startswith('When asked to "work on"'))


@pytest.mark.parametrize("text", [one_step_rule, work_on_paragraph])
def test_rules_end_a_spec_session_at_its_handoff(text: Any) -> None:
    """The rules end a spec session at its handoff, and a one-shot one at End."""
    body = text()
    assert "spec handoff" in body
    assert "**End** in **One-shot**" in body
    assert "after the last ticket" in body


def test_one_step_rule_names_the_build_session() -> None:
    """The rule says that a build session runs build, review, and merge."""
    rule = one_step_rule()
    for step in BUILD_STEPS:
        assert f"`{step}`" in rule
    assert "after the merge gate" in rule


def test_build_runs_in_a_new_session() -> None:
    """`craft:build` says it runs in a new session, never in the spec session."""
    text = skill("build")
    description = text.split("description:", 1)[1].split("\n", 1)[0]
    for body in (description, section(text, "Input")):
        assert "new session" in body
        assert "never in the session that ran `craft:spec`" in body
