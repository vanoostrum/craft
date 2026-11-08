# Copyright (C) 2026 Theo van Oostrum
"""Brainstorm turns an idea into a brief, and plan turns the brief into tickets."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "craft" / "skills"


def skill(name: str) -> str:
    """Return the text of a skill's `SKILL.md`."""
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return the body of the `## <heading>` section."""
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def step(text: str, name: str) -> str:
    """Return the numbered step whose bold name is `name`."""
    rest = text.split(f"**{name}**", 1)[1].split("\n## ", 1)[0]
    end = re.search(r"\n\d+\. ", rest)
    return rest[: end.start()] if end else rest


def test_brainstorm_asks_open_questions_before_options() -> None:
    """The brainstorm asks one open question at a time before it offers options."""
    conversation = step(skill("brainstorm"), "The conversation.")
    assert "one question at a time" in conversation.lower()
    assert "no recommended answer" in conversation


def test_brainstorm_writes_the_brief_as_a_linear_document() -> None:
    """The brief is a Linear document in the Linear project that the plan uses."""
    brief = step(skill("brainstorm"), "Write the brief.")
    assert "Linear document" in brief
    assert "Look" in brief


def test_brainstorm_has_no_gate() -> None:
    """The owner approves the brief in chat; the plan gate stays the formal gate."""
    text = skill("brainstorm")
    assert "🤖 Gate:" not in text
    assert "plan gate" in section(text, "Approval")


def test_brainstorm_hands_the_brief_to_plan() -> None:
    """After approval, `craft:plan` runs with the brief in a new session."""
    after = section(skill("brainstorm"), "After approval")
    assert "craft:plan" in after
    assert "new session" in after


def test_plan_takes_a_brief() -> None:
    """`craft:plan` accepts a brief and grills only what it left open."""
    text = skill("plan")
    assert "brief" in section(text, "Input")
    assert "left open" in step(text, "Helicopter grill.")


def test_plan_slices_by_what_the_owner_can_reject() -> None:
    """A ticket is split only where the owner could reject one part."""
    slicing = step(skill("plan"), "Slice the work")
    assert "vertical" in slicing
    assert "reject" in slicing


def test_plan_tickets_name_their_interfaces() -> None:
    """Each ticket names what it consumes and produces, and the reviewer checks them."""
    text = skill("plan")
    assert "Produces" in step(text, "Slice the work")
    assert "Produces" in step(text, "Review in a fresh agent.")


def test_plan_copies_constraints_verbatim() -> None:
    """Hard constraints go to every ticket word for word."""
    text = skill("plan")
    assert "Constraints" in step(text, "Write the plan")
    assert "word for word" in section(text, "After approval")


def test_design_starts_from_the_brief_look() -> None:
    """Project mode starts from the Look section of the brief, if there is one."""
    assert "Look" in step(skill("design"), "Prototype with the owner.")


def test_spec_has_a_review_focus_that_review_checks() -> None:
    """The spec lists failure modes to test, and the reviewer checks each one."""
    assert "Review focus" in step(skill("spec"), "Write the spec")
    assert "Review focus" in skill("review")
