# Copyright (C) 2026 Theo van Oostrum
"""Helpers for the tests that read the text of craft's skills and rules."""

import re
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "craft" / "skills"
RULES = SKILLS / "rules"
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def skill(name: str) -> str:
    """Return the text of a skill's `SKILL.md`."""
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def findings() -> str:
    """Return the text of `rules/findings.md`."""
    return (RULES / "findings.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return the body of the `## <heading>` section of `text`."""
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def step(text: str, name: str) -> str:
    """Return the numbered step or item whose bold name is `name`."""
    rest = text.split(f"**{name}**", 1)[1].split("\n## ", 1)[0]
    end = re.search(r"\n\s*\d+\. \*\*", rest)
    return rest[: end.start()] if end else rest


def numbered_step(text: str, name: str) -> str:
    """Return the numbered step whose bold name is `name`, up to the next number."""
    rest = text.split(f"**{name}**", 1)[1].split("\n## ", 1)[0]
    end = re.search(r"\n\d+\. ", rest)
    return rest[: end.start()] if end else rest


def one_shot() -> str:
    """Return the One-shot section of `craft:next`."""
    return section(skill("next"), "One-shot")


def frontmatter(path: Path) -> dict[str, Any]:
    """Return the YAML frontmatter of a markdown file."""
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    assert match, f"{path} has no frontmatter"
    return yaml.safe_load(match.group(1))


def reviewer_task() -> str:
    """Return the quoted task that `craft:review` step 2 gives the fresh reviewer."""
    text = step(skill("review"), "Review in a fresh agent.")
    lines = (line.strip() for line in text.splitlines())
    return " ".join(line[1:].strip() for line in lines if line.startswith(">"))
