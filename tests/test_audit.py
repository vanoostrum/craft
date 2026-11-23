# Copyright (C) 2026 Theo van Oostrum
"""`craft:audit` scores merged craft PRs in a blind audit.

These tests check the text that the audit step reads: its skill, the core
rubric, and the lines in `craft:rules`, `craft:bstack`, and `models.md`.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "craft" / "skills"
AUDIT = SKILLS / "audit"
ITEMS = ("Design", "Complexity", "Duplication", "Naming", "Tests")


def rubric() -> str:
    """Return the text of the core rubric."""
    return (AUDIT / "rubric.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return the body of the `## <heading>` section of `text`."""
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


# Criterion 2: the core rubric.


def test_the_rubric_has_version_1() -> None:
    """The rubric names its version on its own line."""
    assert re.search(r"^Rubric version: 1$", rubric(), re.MULTILINE)


def test_the_rubric_has_exactly_the_five_items() -> None:
    """Design, complexity, duplication, naming, and tests, in that order."""
    items = re.findall(r"^### (.+)$", section(rubric(), "Items"), re.MULTILINE)
    assert tuple(items) == ITEMS


def test_each_item_says_what_to_look_for() -> None:
    """Each item has a `Look for:` line."""
    for body in section(rubric(), "Items").split("\n### ")[1:]:
        assert "Look for:" in body, body.splitlines()[0]


def test_the_rubric_defines_major_and_minor() -> None:
    """Major asks for a change before merge; minor still approves."""
    text = section(rubric(), "Severity")
    assert "**major**: a careful reviewer would ask for a change before merge" in text
    assert "**minor**: worth a comment, but the reviewer would still approve" in text
