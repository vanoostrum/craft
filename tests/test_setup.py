# Copyright (C) 2026 Theo van Oostrum
"""Setup describes the environments in a brief, and plan turns it into tickets."""

from tests.test_brainstorm import SKILLS, section, skill, step


def test_setup_has_a_dev_and_a_deploy_mode() -> None:
    """Dev covers local, cloud agents, and CI; deploy covers staging and production."""
    text = skill("setup")
    places = step(text, "Write the brief.")
    for place in ("Local", "Cloud agents", "CI", "Staging", "Production"):
        assert f"**{place}**" in places


def test_setup_has_a_checklist_for_each_part() -> None:
    """The parts checklist covers the kinds of project the owner builds."""
    parts = (SKILLS / "setup" / "parts.md").read_text(encoding="utf-8")
    for part in ("Web frontend", "Mobile app", "Backend API", "Storage"):
        assert f"\n## {part}\n" in parts
    assert "parts.md" in step(skill("setup"), "Read what exists.")


def test_setup_prefers_vercel_within_the_hobby_plan() -> None:
    """The owner prefers Vercel, and setup reads the Hobby plan limits live."""
    preferences = (SKILLS / "setup" / "preferences.md").read_text(encoding="utf-8")
    assert "Vercel" in preferences
    assert "Hobby" in preferences
    assert "https://vercel.com/docs/plans/hobby" in preferences
    assert "preferences.md" in step(skill("setup"), "The conversation.")


def test_setup_lists_what_only_the_owner_can_do() -> None:
    """Secrets and settings no agent can reach go on the owner checklist."""
    text = skill("setup")
    assert "Owner checklist" in step(text, "Write the brief.")
    assert "Owner first" in step(skill("build"), "Check that the ticket is ready.")


def test_setup_hands_the_brief_to_plan() -> None:
    """After approval, `craft:plan` runs with the environment brief in a new session."""
    text = skill("setup")
    assert "🤖 Gate:" not in text
    assert "craft:plan" in section(text, "After approval")


def test_brainstorm_starts_setup_for_a_new_project() -> None:
    """A new project describes its dev environment before the product is planned."""
    assert "craft:setup dev" in section(skill("brainstorm"), "After approval")


def test_plan_starts_an_environment_plan_with_a_walking_skeleton() -> None:
    """Environment tickets serve the developer, and the walking skeleton comes first."""
    text = skill("plan")
    tickets = step(text, "Slice the work")
    assert "walking skeleton" in tickets
    assert "agents that build the project" in tickets
    assert "walking skeleton" in step(text, "Review in a fresh agent.")
