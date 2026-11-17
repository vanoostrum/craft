# Copyright (C) 2026 Theo van Oostrum
"""A ticket gets 5 failed attempts before craft moves it to Needs human."""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "craft" / "skills"


def skill(name: str) -> str:
    """Return the text of a skill's `SKILL.md`."""
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def test_rules_retries_allow_five_failed_attempts() -> None:
    """Retries in `craft:rules` sets the limit at 5, with 4 retries."""
    retries = skill("rules").split("- **Retries.**", 1)[1].split("\n- **", 1)[0]
    assert "at most 5 failed attempts" in retries
    assert "After the fifth failure" in retries
    assert "retry 1 of 4" in retries
    assert "retry 1 of 2" not in retries


@pytest.mark.parametrize("name", ["build", "review", "plan"])
def test_steps_escalate_after_five_failed_attempts(name: str) -> None:
    """The steps with an Escalation line stop after 5 failed attempts."""
    assert "After 5 failed attempts" in skill(name)


@pytest.mark.parametrize("name", ["spec", "next"])
def test_spec_reviews_stop_at_the_fifth_fail(name: str) -> None:
    """The one-shot spec reviews stop at the fifth FAIL."""
    assert "fifth FAIL" in skill(name)


def test_next_done_report_waits_for_the_fifth_fail() -> None:
    """Both the plan-scope review and the done report in `craft:next` use 5."""
    review, report = skill("next").split("**Done report.**", 1)
    assert "fifth FAIL" in review
    assert "fifth FAIL" in report.split("\n", 1)[0]


@pytest.mark.parametrize(
    "path", sorted(SKILLS.rglob("*.md")), ids=lambda p: str(p.relative_to(SKILLS))
)
def test_no_skill_keeps_the_old_limit(path: Path) -> None:
    """No skill file still stops after 3 failed attempts."""
    text = path.read_text(encoding="utf-8")
    for phrase in ("3 failed attempts", "third FAIL", "third failure"):
        assert phrase not in text


def test_build_keeps_three_fixes_per_task() -> None:
    """The count of fixes inside one attempt is not a failed-attempt limit."""
    assert "still red after 3 fixes for the same task" in skill("build")
