# Copyright (C) 2026 Theo van Oostrum
"""The sous step skills run on the models that `models.md` lists."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "sous" / "skills"
MODELS = SKILLS / "rules" / "models.md"
STEP_ROW = re.compile(r"^\| [^|]+ \| `sous:([a-z]+)` \| ([a-z-]+) \|$", re.MULTILINE)
MODEL_HEADER = re.compile(
    r"\A---\n.*?^model: ([a-z-]+)$.*?^---$", re.DOTALL | re.MULTILINE
)


def step_models() -> dict[str, str]:
    """Return the model per sous step skill from the models table."""
    text = MODELS.read_text(encoding="utf-8")
    steps = text.split("## Steps", 1)[1].split("\n## ", 1)[0]
    return dict(STEP_ROW.findall(steps))


def test_every_step_is_in_the_table() -> None:
    """Each skill with a `model:` header is a step with a row in the models table."""
    skills = {
        path.parent.name
        for path in SKILLS.glob("*/SKILL.md")
        if MODEL_HEADER.search(path.read_text(encoding="utf-8"))
    }
    assert set(step_models()) == skills


@pytest.mark.parametrize(("skill", "model"), sorted(step_models().items()))
def test_step_header_matches_the_table(skill: str, model: str) -> None:
    """The skill's `model:` header is the model the table names."""
    text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
    header = MODEL_HEADER.search(text)
    assert header is not None, f"{skill} has no model: header"
    assert header.group(1) == model
