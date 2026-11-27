# Copyright (C) 2026 Theo van Oostrum
"""The gallery rules allow a page with no primary action."""

import re

from tests.skill_text import ROOT, section

PLUGIN = ROOT / "plugins" / "craft"
GALLERY = PLUGIN / "skills" / "rules" / "gallery.md"

OLD_RULES = (
    "exactly one primary action",
    "one primary action per page",
    "each page has one primary action",
)


def flat(text: str) -> str:
    """Collapse whitespace, so a rule can wrap over lines."""
    return re.sub(r"\s+", " ", text)


def test_page_rule_allows_at_most_one_primary_action() -> None:
    """A page with a task has one; a page with nothing to do may have none."""
    rules = flat(section(GALLERY.read_text(encoding="utf-8"), "Rules for pages"))
    assert "at most one primary action, and it stands out when there is one" in rules
    assert "A page where the user has a task has one." in rules
    assert "A page where the user has nothing to do" in rules
    assert "may have none" in rules


def test_stage_2_checks_at_most_one_primary_action() -> None:
    """The stage 2 design checks check for at most one primary action."""
    stages = section(GALLERY.read_text(encoding="utf-8"), "Rollout stages")
    stage_2 = flat(stages.split("| 2. ", 1)[1].split("\n", 1)[0])
    assert "at most one primary action, which stands out when there is one" in stage_2


def test_no_skill_text_keeps_the_old_rule() -> None:
    """No file of the plugin still says a page has exactly one primary action."""
    found = [
        f"{path.relative_to(ROOT)}: {old}"
        for path in PLUGIN.rglob("*")
        if path.is_file()
        for old in OLD_RULES
        if old in flat(path.read_text(encoding="utf-8", errors="ignore")).lower()
    ]
    assert found == []
