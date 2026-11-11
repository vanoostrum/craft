# Copyright (C) 2026 Theo van Oostrum
"""The smoke case `spec-loads-rules-first` grades skill order on the trace.

The order grader is a `regex` grader on the `trace` target. The CLI joins the
run's stream messages, each as compact JSON, with newlines, and runs the
pattern on that text. These tests do the same with Python `re`; the pattern
uses only syntax that JS and Python read the same way.
"""

import json
import re
from pathlib import Path

from tests.test_dev_environment import FRONTMATTER, frontmatter

GRADERS = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "craft"
    / "evals"
    / "spec-loads-rules-first"
    / "graders"
)
ORDER = GRADERS / "rules-before-other-skills.md"


def skill_call(skill: str, **extra: str) -> dict[str, object]:
    """Return an assistant message with one Skill call, as the trace holds it."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": f"toolu_{skill}",
                    "name": "Skill",
                    "input": {"skill": skill, **extra},
                }
            ]
        },
        "parent_tool_use_id": None,
    }


def partial_skill_call() -> dict[str, object]:
    """Return the early assistant message of a streamed call: its input is empty."""
    return {
        "type": "assistant",
        "message": {
            "content": [
                {"type": "tool_use", "id": "toolu_x", "name": "Skill", "input": {}}
            ]
        },
    }


def stream_event(partial_json: str) -> dict[str, object]:
    """Return a stream event that carries part of a tool input as escaped JSON."""
    return {
        "type": "stream_event",
        "event": {
            "type": "content_block_delta",
            "delta": {"type": "input_json_delta", "partial_json": partial_json},
        },
    }


def trace(*messages: dict[str, object]) -> str:
    """Return the text that the `trace` target gives a regex grader."""
    head = {"type": "system", "subtype": "init", "skills": ["craft:spec"]}
    lines = [head, *messages, {"type": "result", "subtype": "success"}]
    return "\n".join(json.dumps(m, separators=(",", ":")) for m in lines)


def order_grader_passes(text: str) -> bool:
    """Run the order grader as the CLI does, and return whether it passes."""
    meta = frontmatter(ORDER)
    assert meta["type"] == "regex"
    assert meta["target"] == "trace"
    assert meta["match"] == "not_contains"
    raw = ORDER.read_text(encoding="utf-8")
    head = FRONTMATTER.match(raw)
    assert head
    pattern = raw[head.end() :].strip()
    flags = re.DOTALL if "s" in meta.get("flags", "") else 0
    return re.search(pattern, text, flags) is None


def loads_rules_passes(text: str) -> bool:
    """Run the `loads-rules` grader: at least one Skill call matches `craft:rules`."""
    meta = frontmatter(GRADERS / "loads-rules.md")
    calls = [
        json.dumps(block["input"], separators=(",", ":"))
        for line in text.splitlines()
        if (message := json.loads(line)).get("type") == "assistant"
        for block in message["message"]["content"]
        if block["name"] == meta["tool"]
    ]
    return any(re.search(meta["input_match"], call) for call in calls)


def test_passes_when_no_skill_follows_rules() -> None:
    """The agent loads `craft:rules` and stops: the case passes."""
    text = trace(skill_call("craft:spec", args="CRAFT-999"), skill_call("craft:rules"))
    assert order_grader_passes(text)
    assert loads_rules_passes(text)


def test_passes_when_bstack_follows_rules() -> None:
    """The agent loads `craft:bstack` after `craft:rules`: the case passes."""
    text = trace(
        skill_call("craft:spec", args="CRAFT-999"),
        skill_call("craft:rules"),
        skill_call("craft:bstack"),
    )
    assert order_grader_passes(text)
    assert loads_rules_passes(text)


def test_fails_when_another_skill_comes_first() -> None:
    """The agent loads `craft:bstack` before `craft:rules`: the order grader fails."""
    text = trace(
        skill_call("craft:spec", args="CRAFT-999"),
        skill_call("craft:bstack"),
        skill_call("craft:rules"),
    )
    assert not order_grader_passes(text)


def test_passes_when_rules_is_loaded_again_later() -> None:
    """Only the first `craft:rules` counts: a later second load does not fail."""
    text = trace(
        skill_call("craft:spec", args="CRAFT-999"),
        skill_call("craft:rules"),
        skill_call("craft:bstack"),
        skill_call("craft:rules"),
    )
    assert order_grader_passes(text)


def test_ignores_partial_inputs_and_stream_events() -> None:
    """Streamed partial inputs and escaped stream events are not Skill calls."""
    text = trace(
        skill_call("craft:spec", args="CRAFT-999"),
        partial_skill_call(),
        stream_event('{"skill": "craft:bstack"}'),
        skill_call("craft:rules"),
    )
    assert order_grader_passes(text)
