# Copyright (C) 2026 Theo van Oostrum
"""Brainstorm turns an idea into a brief, and plan turns the brief into tickets."""

from tests.skill_text import SKILLS, numbered_step, section, skill


def test_brainstorm_asks_open_questions_before_options() -> None:
    """The brainstorm asks one open question at a time before it offers options."""
    conversation = numbered_step(skill("brainstorm"), "The conversation.")
    assert "one question at a time" in conversation.lower()
    assert "no recommended answer" in conversation


def test_brainstorm_writes_the_brief_as_a_linear_document() -> None:
    """The brief is a Linear document in the Linear project that the plan uses."""
    brief = numbered_step(skill("brainstorm"), "Write the brief.")
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
    assert "left open" in numbered_step(text, "Helicopter grill.")


def test_plan_slices_by_what_the_owner_can_reject() -> None:
    """A ticket is split only where the owner could reject one part."""
    slicing = numbered_step(skill("plan"), "Slice the work")
    assert "vertical" in slicing
    assert "reject" in slicing


def test_plan_tickets_name_their_interfaces() -> None:
    """Each ticket names what it consumes and produces, and the reviewer checks them."""
    text = skill("plan")
    assert "Produces" in numbered_step(text, "Slice the work")
    assert "Produces" in numbered_step(text, "Review in a fresh agent.")


def test_plan_copies_constraints_verbatim() -> None:
    """Hard constraints go to every ticket word for word."""
    text = skill("plan")
    assert "Constraints" in numbered_step(text, "Write the plan")
    assert "word for word" in section(text, "After approval")


def test_design_starts_from_the_brief_look() -> None:
    """Project mode starts from the Look section of the brief, if there is one."""
    assert "Look" in numbered_step(skill("design"), "Prototype with the owner.")


def test_spec_has_a_review_focus_that_review_checks() -> None:
    """The spec lists failure modes to test, and the reviewer checks each one."""
    assert "Review focus" in numbered_step(skill("spec"), "Write the spec")
    assert "Review focus" in skill("review")


PLAN_ARGUMENTS = ("design-variants=", "platforms=", "mode=<gated|one-shot>", "note=")


def test_brainstorm_asks_for_the_plan_arguments_at_approval() -> None:
    """The approval lists each plan argument; "approve" or 👍 keeps the defaults."""
    approval = section(skill("brainstorm"), "Approval")
    for argument in PLAN_ARGUMENTS:
        assert f"`{argument}" in approval
    assert "default" in approval
    assert "keeps the defaults" in approval


def test_brainstorm_carries_the_plan_arguments_in_the_brief() -> None:
    """The owner's arguments go into the brief; the prompt holds only the link."""
    after = section(skill("brainstorm"), "After approval")
    assert "**Steering**" in after
    assert "only the arguments the owner gave" in after
    assert "`Run craft:plan on <brief link>.`" in after
    assert "would replace" in after
    assert "product brief" in after


def test_brainstorm_adds_an_approval_note_to_the_brief_notes() -> None:
    """A note given at approval joins the notes already in Steering."""
    after = section(skill("brainstorm"), "After approval")
    assert "added to the notes already in **Steering**" in after


def test_brainstorm_asks_again_for_an_unknown_argument() -> None:
    """An unknown argument or value is not an approval."""
    approval = section(skill("brainstorm"), "Approval")
    assert "not an approval" in approval
    assert "ask again" in approval


def test_brainstorm_owns_the_look() -> None:
    """Brainstorm settles the direction, the identity, and the defining screens."""
    look = numbered_step(skill("brainstorm"), "Look and feel.")
    assert "identity" in look
    assert "defining screens" in look
    assert "craft:design" in look


def test_brief_look_lists_identity_and_screens() -> None:
    """The Look section names the identity values and the screens it drew."""
    brief = numbered_step(skill("brainstorm"), "Write the brief.")
    assert "**Identity:**" in brief
    assert "**Screens:**" in brief


def test_design_freezes_the_brief_look_without_a_new_round() -> None:
    """With a Look, project mode freezes it and draws only the screens it lacks."""
    prototype = numbered_step(skill("design"), "Prototype with the owner.")
    assert "Do not prototype again" in prototype
    assert "only the screens that the Look does not cover" in prototype


def test_variants_apply_only_to_new_screens_after_a_brief() -> None:
    """After a brainstorm, `design-variants` covers only screens the Look lacks."""
    prototype = numbered_step(skill("design"), "Prototype with the owner.")
    assert "not in the Look" in prototype
    rules = (SKILLS / "rules" / "SKILL.md").read_text(encoding="utf-8")
    assert "not in the brief's **Look**" in rules
