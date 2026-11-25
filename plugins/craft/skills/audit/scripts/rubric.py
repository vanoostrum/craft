#!/usr/bin/env python3
# Copyright (C) 2026 Theo van Oostrum
"""Read and check the rubric files of `craft:audit`.

Usage:
    rubric.py names [<rubrics dir>]   the rubrics a run judges, one per line
    rubric.py find <name> [<rubrics dir>]   the path of one rubric
    rubric.py check <file>...   check that each file follows the format

The rubrics dir defaults to `rubrics/` next to this script's folder. A rubric
is a `*.md` file in it or in its `custom/` folder. A file whose name starts
with `_` is a template: `names` and `find` skip it. `find` on an unknown name
exits 2 and lists the rubric names.
"""

import re
import sys
from dataclasses import dataclass
from pathlib import Path

RUBRICS = Path(__file__).resolve().parents[1] / "rubrics"
KINDS = ("Check", "Measure", "Escape")
APPLIES_TO = "tickets with a spec"
PER_VERSION = "craft version"
CHECK_LINES = ("Pass", "Partial", "Fail")
TITLE = re.compile(r"\A# (.+) rubric\n")
FIELD = re.compile(r"^([A-Z][a-z ]*): (.+)$", re.MULTILINE)
SCRIPT = re.compile(r"`scripts/[a-z_]+\.py`")


class RubricError(Exception):
    """A rubric file does not follow the format."""


@dataclass(frozen=True)
class Item:
    """One rubric item."""

    name: str
    kind: str
    per_version: bool


@dataclass(frozen=True)
class Rubric:
    """One rubric file, parsed."""

    name: str
    title: str
    version: str
    phase: str
    applies_to: str | None
    items: tuple[Item, ...]


def fields(text: str) -> dict[str, str]:
    """Return the `Key: value` lines of a block of text."""
    return {key: value.strip() for key, value in FIELD.findall(text)}


def parse_item(block: str) -> Item:
    """Return one item from its `### <name>` block."""
    name, _, body = block.partition("\n")
    name = name.strip()
    lines = fields(body)
    kind = lines.get("Kind")
    if kind not in KINDS:
        message = f"item {name!r}: Kind must be one of {', '.join(KINDS)}"
        raise RubricError(message)
    for key in ("Reads", "Score"):
        if key not in lines:
            message = f"item {name!r}: no {key}: line"
            raise RubricError(message)
    per = lines.get("Per")
    if per is not None and (kind != "Check" or per != PER_VERSION):
        message = f"item {name!r}: Per: {PER_VERSION} is only for a Check"
        raise RubricError(message)
    if kind == "Check":
        for key in CHECK_LINES:
            if key not in lines:
                message = f"item {name!r}: a Check needs a {key}: line"
                raise RubricError(message)
    if kind == "Measure" and not SCRIPT.search(lines["Score"]):
        message = f"item {name!r}: a Measure names its script in Score:"
        raise RubricError(message)
    return Item(name, kind, per_version=per is not None)


def parse(path: Path) -> Rubric:
    """Return the rubric in a file, or raise `RubricError`."""
    text = path.read_text(encoding="utf-8")
    title = TITLE.match(text)
    if title is None:
        message = "no title line `# <Name> rubric`"
        raise RubricError(message)
    head, found, items = text.partition("\n## Items\n")
    if not found:
        message = "no `## Items` section"
        raise RubricError(message)
    lines = fields(head)
    version = lines.get("Rubric version", "")
    if not version.isdigit():
        message = "no Rubric version: line with a whole number"
        raise RubricError(message)
    phase = lines.get("Phase", "")
    if not re.fullmatch(r"[a-z]+", phase):
        message = "no Phase: line with a phase, such as review, or custom"
        raise RubricError(message)
    applies_to = lines.get("Applies to")
    if applies_to not in (None, APPLIES_TO):
        message = f"Applies to: can only be {APPLIES_TO!r}"
        raise RubricError(message)
    blocks = items.split("\n## ", 1)[0].split("\n### ")[1:]
    if not blocks:
        message = "no items under `## Items`"
        raise RubricError(message)
    return Rubric(
        name=path.stem,
        title=title.group(1),
        version=version,
        phase=phase,
        applies_to=applies_to,
        items=tuple(parse_item(block) for block in blocks),
    )


def paths(rubrics: Path = RUBRICS) -> list[Path]:
    """Return the rubric files that a run judges: phase rubrics, then custom."""
    found = sorted(rubrics.glob("*.md")) + sorted((rubrics / "custom").glob("*.md"))
    return [path for path in found if not path.name.startswith("_")]


def find(name: str, rubrics: Path = RUBRICS) -> Path:
    """Return the file of one rubric, or raise `RubricError` with the names."""
    for path in paths(rubrics):
        if path.stem == name:
            return path
    names = ", ".join(path.stem for path in paths(rubrics))
    message = f"unknown rubric {name!r}; the rubrics are: {names}"
    raise RubricError(message)


def main(argv: list[str]) -> int:
    """Run one command."""
    command, args = (argv[1], argv[2:]) if len(argv) > 1 else ("", [])
    if command == "names" and len(args) <= 1:
        for path in paths(*map(Path, args)):
            sys.stdout.write(f"{path.stem}\n")
        return 0
    if command == "find" and len(args) in (1, 2):
        try:
            sys.stdout.write(f"{find(args[0], *map(Path, args[1:]))}\n")
        except RubricError as error:
            sys.stderr.write(f"rubric.py: {error}\n")
            return 2
        return 0
    if command == "check" and args:
        failed = 0
        for arg in args:
            try:
                parse(Path(arg))
            except RubricError as error:
                sys.stdout.write(f"{arg}: {error}\n")
                failed = 1
        return failed
    sys.stderr.write(f"{__doc__}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
