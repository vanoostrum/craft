# Copyright (C) 2026 Theo van Oostrum
"""A 👍 on the gate message in chat approves a gate."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "craft" / "skills"
GATE_STEPS = ["plan", "spec", "review"]


def gate_rule() -> str:
    """Return the rule for the gate from `craft:rules`."""
    text = (SKILLS / "rules" / "SKILL.md").read_text(encoding="utf-8")
    return text.split("- **The gate.**", 1)[1].split("\n- **", 1)[0]


def test_gate_rule_accepts_a_thumbs_up() -> None:
    """The rule for the gate counts a 👍 reaction in chat as approval."""
    rule = gate_rule()
    assert "👍" in rule
    assert "🤖 Approved: <gate> (👍 in chat)" in rule


@pytest.mark.parametrize("skill", GATE_STEPS)
def test_pass_step_offers_a_thumbs_up(skill: str) -> None:
    """Each step that stops at a gate tells the owner that 👍 approves."""
    text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "👍" in text
