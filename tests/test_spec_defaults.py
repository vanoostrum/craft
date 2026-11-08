# Copyright (C) 2026 Theo van Oostrum
"""The spec grill skips near-certain questions and lists them at the gate."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "plugins" / "craft" / "skills" / "spec" / "SKILL.md"


def step(text: str, name: str) -> str:
    """Return the numbered step of `craft:spec` whose bold name is `name`."""
    rest = text.split(f"**{name}**", 1)[1].split("\n## ", 1)[0]
    end = re.search(r"\n\d+\. ", rest)
    return rest[: end.start()] if end else rest


def test_grill_asks_only_uncertain_questions() -> None:
    """The grill asks only when the owner might not pick the recommended answer."""
    grill = step(SPEC.read_text(encoding="utf-8"), "Grill.")
    assert "certainty is high" in grill
    assert "(default)" in grill


def test_gate_lists_the_defaults() -> None:
    """The spec gate lists the `(default)` decisions on the ticket and in chat."""
    spec_gate = step(SPEC.read_text(encoding="utf-8"), "Gate.")
    assert "(default)" in spec_gate
    assert "In chat" in spec_gate
