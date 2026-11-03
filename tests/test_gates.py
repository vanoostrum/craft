# Copyright (C) 2026 Theo van Oostrum
"""A 👍 on the pass message in chat approves a pass."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "sous" / "skills"
PASS_STEPS = ["plan", "spec", "review"]


def pass_rule() -> str:
    """Return the rule for the pass from `sous:rules`."""
    text = (SKILLS / "rules" / "SKILL.md").read_text(encoding="utf-8")
    return text.split("- **The pass.**", 1)[1].split("\n- **", 1)[0]


def test_pass_rule_accepts_a_thumbs_up() -> None:
    """The rule for the pass counts a 👍 reaction in chat as approval."""
    rule = pass_rule()
    assert "👍" in rule
    assert "🤖 Approved: <pass> (👍 in chat)" in rule


@pytest.mark.parametrize("skill", PASS_STEPS)
def test_pass_step_offers_a_thumbs_up(skill: str) -> None:
    """Each step that stops at a pass tells chef that 👍 approves."""
    text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "👍" in text
