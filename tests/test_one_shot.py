# Copyright (C) 2026 Theo van Oostrum
"""`mode=one-shot` specs every ticket up front, then builds and merges without gates."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "craft" / "skills"


def skill(name: str) -> str:
    """Return the text of a skill's `SKILL.md`."""
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return the body of the `## <heading>` section of `text`."""
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def test_plan_takes_the_mode_argument() -> None:
    """`craft:plan` lists `mode=` in its argument hint."""
    header = skill("plan").split("---", 2)[1]
    assert "mode=<gated|one-shot>" in header


def test_rules_define_the_mode_argument() -> None:
    """The steering table in `craft:rules` defines `mode=` with default `gated`."""
    rows = [
        line
        for line in skill("rules").splitlines()
        if line.strip().startswith("| `mode=")
    ]
    assert len(rows) == 1
    assert "`gated`" in rows[0]


def test_rules_describe_one_shot_mode() -> None:
    """`craft:rules` describes the one-shot flow and its launch gate."""
    text = section(skill("rules"), "One-shot mode")
    assert "🤖 Gate: launch" in text
    assert "staging" in text
    assert "production" in text


def test_launch_gate_is_a_gate() -> None:
    """The gate rule names the launch gate, so 👍 and "approve" work on it."""
    rules = skill("rules")
    gate = rules.split("- **The gate.**", 1)[1].split("\n- **", 1)[0]
    assert "🤖 Gate: launch" in gate


def test_plan_lists_manual_actions_and_paid_services_up_front() -> None:
    """A one-shot plan lists owner actions and paid services before the gate."""
    text = skill("plan")
    assert "**Up front.**" in text
    step = text.split("**Up front.**", 1)[1].split("\n9. ", 1)[0]
    assert "Paid services" in step
    assert "Owner checklist" in step


def test_next_has_the_one_shot_phases() -> None:
    """`craft:next` runs a spec phase, the launch gate, a build phase, and a report."""
    text = section(skill("next"), "One-shot")
    for phase in (
        "Spec phase",
        "Spec review",
        "Launch gate",
        "Build phase",
        "Done report",
    ):
        assert f"**{phase}.**" in text
    assert "👍" in text


@pytest.mark.parametrize("name", ["spec", "review", "merge", "build"])
def test_ticket_steps_handle_one_shot(name: str) -> None:
    """Each ticket step says what changes for a ticket with `mode=one-shot`."""
    assert "`mode=one-shot`" in skill(name)


def test_one_shot_spec_skips_the_spec_gate() -> None:
    """A one-shot spec goes to Ready to build without a spec gate."""
    text = skill("spec")
    step = text.split("**One-shot.**", 1)[1].split("\n## ", 1)[0]
    assert "Ready to build" in step
    assert "Do not post `🤖 Gate: spec`" in step


def test_one_shot_merge_needs_the_launch_gate() -> None:
    """Without a merge gate, `craft:merge` needs the approved launch gate instead."""
    step = skill("merge").split("1. **Check the gate.**", 1)[1].split("\n2. ", 1)[0]
    assert "launch" in step
    assert "PASS" in step


def test_one_shot_build_does_not_need_a_spec_gate() -> None:
    """`craft:build`'s readiness check accepts the launch gate for one-shot tickets."""
    step = skill("build").split("1. **Check that the ticket is ready.**", 1)[1]
    check = step.split("The spec gate must be approved.", 1)[1].split("\n", 1)[0]
    assert "`mode=one-shot`" in check
    assert "🤖 Gate: launch" in check


def test_one_shot_retries_keep_the_run_going() -> None:
    """After the third failure in one-shot mode, Retries starts the next ticket."""
    rules = skill("rules")
    retries = rules.split("- **Retries.**", 1)[1].split("\n- **", 1)[0]
    assert "run `craft:next`" in retries.split("In one-shot mode", 1)[1]


def test_next_finds_the_one_shot_phase_from_the_plan_ticket() -> None:
    """`craft:next` picks the phase from the plan ticket and routes gated tickets."""
    text = section(skill("next"), "One-shot")
    assert "Find the phase" in text
    rows = [line for line in text.splitlines() if line.startswith("| a `🤖 one-shot:`")]
    assert len(rows) == 1
    assert "`mode=gated`" in rows[0]


def test_one_shot_plan_ticket_stays_open() -> None:
    """With one-shot, the plan ticket stays open for the launch gate."""
    after = section(skill("plan"), "After approval")
    assert "For `mode=one-shot`, leave it open" in after


def test_spec_review_checks_each_spec_and_all_specs_together() -> None:
    """The one-shot spec review runs in a fresh agent over every spec at once."""
    text = section(skill("next"), "One-shot")
    step = text.split("**Spec review.**", 1)[1].split("**Launch gate.**", 1)[0]
    assert "`spec reviewer` model" in step
    assert "Check each spec on its own" in step
    assert "Then check the specs together" in step
    assert "back to **Todo**" in step


def test_spec_reviewer_has_a_model() -> None:
    """`models.md` names the model of the spec reviewer."""
    models = (SKILLS / "rules" / "models.md").read_text(encoding="utf-8")
    assert "| spec reviewer |" in models


def test_spec_treats_a_spec_review_as_feedback() -> None:
    """`craft:spec` grills again on the problems the spec review found."""
    assert "`🤖 spec review:` comment" in skill("spec")
