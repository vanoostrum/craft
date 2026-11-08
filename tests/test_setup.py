# Copyright (C) 2026 Theo van Oostrum
"""Setup describes the environments in a brief, and plan turns it into tickets."""

from tests.test_brainstorm import SKILLS, section, skill, step

BRIEFS = ("Brief: Dev environment", "Brief: Staging and production")


def setup_file(name: str) -> str:
    """Return the text of a file next to the setup skill."""
    return (SKILLS / "setup" / name).read_text(encoding="utf-8")


def test_setup_has_a_dev_and_a_deploy_mode() -> None:
    """Each mode writes its own brief, and plan takes both."""
    text = skill("setup")
    for brief in BRIEFS:
        assert f"`{brief}`" in text
        assert brief in section(skill("plan"), "Input")
    places = step(text, "Write the brief.")
    for place in ("Local", "Cloud agents", "CI", "Staging", "Production", "Rollback"):
        assert f"**{place}**" in places


def test_setup_has_a_checklist_for_each_part() -> None:
    """The parts checklist covers the kinds of project the owner builds."""
    parts = setup_file("parts.md")
    for part in ("Web frontend", "Mobile app", "Backend API", "Storage"):
        assert f"\n## {part}\n" in parts
    assert "parts.md" in step(skill("setup"), "Read what exists.")


def test_setup_prefers_vercel_within_the_hobby_plan() -> None:
    """The owner prefers Vercel, and setup reads the Hobby plan limits live."""
    preferences = setup_file("preferences.md")
    assert "Hobby" in preferences
    assert "https://vercel.com/docs/plans/hobby" in preferences
    assert "Preview protection" in preferences
    assert "preferences.md" in step(skill("setup"), "The conversation.")


def test_setup_does_not_commit() -> None:
    """Setup has no ticket, so plan writes `.claude/craft.md` in its own PR."""
    assert "does not commit" in skill("setup")
    assert ".claude/craft.md" in step(skill("plan"), "Commit")


def test_owner_items_reach_the_owner_when_needed() -> None:
    """Owner items are sorted by when they are needed, and each step acts on them."""
    assert "Before the plan" in step(skill("setup"), "Owner checklist.")
    assert "Before the plan" in section(skill("setup"), "Approval")
    assert "Owner first" in section(skill("plan"), "After approval")
    assert "Owner first" in step(skill("build"), "Check that the ticket is ready.")
    assert "Owner after" in skill("merge")


def test_setup_hands_the_brief_to_plan() -> None:
    """After approval, `craft:plan` runs with the environment brief in a new session."""
    after = section(skill("setup"), "After approval")
    assert "craft:plan" in after
    assert "new session" in after


def test_brainstorm_starts_setup_for_a_new_project() -> None:
    """A new project describes its dev environment before the product is planned."""
    text = skill("brainstorm")
    assert "craft:setup dev" in section(text, "After approval")
    assert "craft:setup dev" in section(text, "Done when")


def test_plan_starts_an_environment_plan_with_a_skeleton() -> None:
    """Environment tickets serve the developer, and a skeleton ticket comes first."""
    text = skill("plan")
    tickets = step(text, "Slice the work")
    assert "agents that build the project" in tickets
    for skeleton in ("walking skeleton", "deploy skeleton"):
        assert skeleton in tickets
        assert skeleton in step(text, "Review in a fresh agent.")


def test_the_walking_skeleton_proves_its_own_values() -> None:
    """The ticket that fills a `none yet` value uses it for its own checks."""
    rules = skill("rules")
    assert "`none yet`" in rules
    assert "its own branch" in rules
    assert "its own branch" in step(skill("merge"), "Check CI.")


def test_merging_the_walking_skeleton_plans_the_product() -> None:
    """The product brief gets its plan once the dev environment works."""
    merge = step(skill("merge"), "Next.")
    assert "walking skeleton" in merge
    assert "Product brief" in merge


def test_v1_offers_the_deploy_setup() -> None:
    """The milestone checkpoint offers `craft:setup deploy` at v1."""
    assert "craft:setup deploy" in section(skill("next"), "Milestone checkpoint")
