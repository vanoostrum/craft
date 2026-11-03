# Copyright (C) 2026 Theo van Oostrum
"""The spec grill skips near-certain questions and lists them at the pass."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "plugins" / "sous" / "skills" / "spec" / "SKILL.md"


def step(text: str, name: str) -> str:
    """Return the numbered step of `sous:spec` whose bold name is `name`."""
    rest = text.split(f"**{name}**", 1)[1].split("\n## ", 1)[0]
    end = re.search(r"\n\d+\. ", rest)
    return rest[: end.start()] if end else rest


def test_grill_asks_only_uncertain_questions() -> None:
    """The grill asks only when chef might not pick the recommended answer."""
    grill = step(SPEC.read_text(encoding="utf-8"), "Grill.")
    assert "certainty is high" in grill
    assert "(default)" in grill


def test_pass_lists_the_defaults() -> None:
    """The spec pass lists the `(default)` decisions on the ticket and in chat."""
    spec_pass = step(SPEC.read_text(encoding="utf-8"), "Pass.")
    assert "(default)" in spec_pass
    assert "In chat" in spec_pass
