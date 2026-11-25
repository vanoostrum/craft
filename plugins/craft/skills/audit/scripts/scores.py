#!/usr/bin/env python3
# Copyright (C) 2026 Theo van Oostrum
"""Print the `## Scores` table of an audit report.

Usage: scores.py [--rubrics <rubrics dir>] <audit.json> [<previous report>]

`audit.json` holds the rubrics that ran, by name, each audited ticket with its
results per rubric, and the results of the checks judged once per craft version:

    {"rubrics": ["review"],
     "tickets": [{"project": "Craft", "ticket": "CRAFT-72", "pr": 47,
                  "rubrics": {"review": {
                      "craft_version": "2.9.1",
                      "checks": {"Read in context": "pass", ...},
                      "measures": {"Findings rounds": {"Rounds until PASS": 2,
                                                       "Blocking per round": 0.5}}}}}],
     "per_version": [{"rubric": "review", "craft_version": "2.9.1",
                      "item": "Process logic", "result": "pass"}]}

A check result is `pass`, `partial`, `fail`, or `no data`. A measure holds the
`values` that its script printed, or `{}` for no data. A rubric that does not
judge a ticket holds `"not in this phase"` instead of results.

The table has one row per rubric, rubric version, craft version, and item: the
Phase score (the share of per-ticket checks passed), each per-ticket check, one
row per measure value (the median), and each check judged once per craft
version. An Escape item gets no row. "At last audit" is the Value of the same
row in the previous report, with the same rubric version, else a dash. The
previous file is the previous report's Markdown, or only its `## Scores` table,
as printed here or as Linear returns it.
"""

import json
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rubric import RUBRICS, Item, Rubric, RubricError, find, parse

RESULTS = ("pass", "partial", "fail")
NO_DATA = "no data"
NOT_IN_PHASE = "not in this phase"
PHASE_SCORE = "Phase score"
DASH = "—"
HEADER = (
    "Rubric",
    "Rubric version",
    "Craft version",
    "Item",
    "Tickets",
    "Value",
    "Pass/partial/fail",
    "At last audit",
)
ESCAPED = re.compile(r"\\([!-/:-@\[-`{-~])")
SEPARATOR = re.compile(r"^\|(\s*:?-+:?\s*\|)+$")

type Json = dict[str, Any]  # Parsed JSON, checked in `load`.
type RowKey = tuple[str, str, str, str]


class AuditError(Exception):
    """The audit file does not match the rubrics or itself."""


type Cells = tuple[str, str, str]  # Tickets, Value, and Pass/partial/fail.
type Row = tuple[str, str, Cells]  # Craft version, item, and cells.


def number(value: float) -> str:
    """Return a whole number as is, else with two decimals."""
    return str(int(value)) if float(value).is_integer() else f"{value:.2f}"


def check_cells(results: list[str]) -> Cells:
    """Return the cells of a check: pass counts 1, partial and fail 0."""
    judged = [r for r in results if r != NO_DATA]
    counts = "/".join(str(judged.count(r)) for r in RESULTS)
    if not judged:
        return "0", NO_DATA, counts
    return str(len(judged)), f"{judged.count('pass') / len(judged):.2f}", counts


def measure_cells(values: list[float | None]) -> Cells:
    """Return the cells of one measure value: the median over tickets with data."""
    known = [v for v in values if v is not None]
    median = number(statistics.median(known)) if known else NO_DATA
    return str(len(known)), median, DASH


def check_result(name: str, result: str) -> str:
    """Return a check result, or raise `AuditError`."""
    if result not in (*RESULTS, NO_DATA):
        message = f"result {result!r} of {name!r} is not one of {RESULTS} or no data"
        raise AuditError(message)
    return result


@dataclass
class Version:
    """The results of one rubric at one craft version."""

    checks: dict[str, list[str]] = field(default_factory=dict)
    measures: dict[str, dict[str, list[float | None]]] = field(default_factory=dict)
    per_version: dict[str, str] = field(default_factory=dict)


@dataclass
class Results:
    """The results of one rubric, per craft version."""

    rubric: Rubric
    versions: dict[str, Version] = field(default_factory=dict)

    def item(self, name: str, kind: str, *, per_version: bool = False) -> Item:
        """Return an item of the rubric with this kind, or raise `AuditError`."""
        for item in self.rubric.items:
            if (item.name, item.kind, item.per_version) == (name, kind, per_version):
                return item
        what = {
            ("Check", False): "a per-ticket check",
            ("Check", True): "a check per craft version",
        }.get((kind, per_version), f"a {kind}")
        message = f"{name!r} is not {what} of the {self.rubric.name} rubric"
        raise AuditError(message)

    def version(self, craft_version: object) -> Version:
        """Return the results at one craft version."""
        return self.versions.setdefault(str(craft_version), Version())

    def add(self, results: Json) -> None:
        """Add one ticket's results, checked against the rubric."""
        version = self.version(results["craft_version"])
        for name, result in results.get("checks", {}).items():
            self.item(name, "Check")
            version.checks.setdefault(name, []).append(check_result(name, result))
        for name, values in results.get("measures", {}).items():
            self.item(name, "Measure")
            measure = version.measures.setdefault(name, {})
            for value_name, value in values.items():
                known = None if value is None else float(value)
                measure.setdefault(value_name, []).append(known)

    def add_per_version(self, entry: Json) -> None:
        """Add the result of one check judged once per craft version."""
        name = entry["item"]
        self.item(name, "Check", per_version=True)
        result = check_result(name, entry["result"])
        self.version(entry["craft_version"]).per_version[name] = result

    def rows(self) -> list[Row]:
        """Return the rows of this rubric, in table order."""
        rows: list[Row] = []
        for craft_version in sorted(self.versions, key=version_order):
            version = self.versions[craft_version]
            per_ticket = [r for results in version.checks.values() for r in results]
            if per_ticket:
                rows.append((craft_version, PHASE_SCORE, check_cells(per_ticket)))
            for item in self.rubric.items:
                if item.name in version.checks:
                    cells = check_cells(version.checks[item.name])
                    rows.append((craft_version, item.name, cells))
                for value_name, values in version.measures.get(item.name, {}).items():
                    label = f"{item.name}: {value_name}"
                    rows.append((craft_version, label, measure_cells(values)))
                if item.name in version.per_version:
                    cells = (DASH, version.per_version[item.name], DASH)
                    rows.append((craft_version, item.name, cells))
        return rows


def version_order(version: str) -> tuple[tuple[int, int | str], ...]:
    """Sort craft versions by number, such as 2.9.0 before 2.10.0."""
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part) for part in version.split(".")
    )


def load(audit: Json, rubrics: Path) -> list[Results]:
    """Return the results per rubric, in run order, checked."""
    found: dict[str, Results] = {}
    for name in audit["rubrics"]:
        try:
            found[name] = Results(parse(find(name, rubrics)))
        except RubricError as error:
            raise AuditError(str(error)) from error
    for ticket in audit["tickets"]:
        for name, results in ticket["rubrics"].items():
            if name not in found:
                message = f"{ticket['ticket']}: {name!r} is not a rubric of this run"
                raise AuditError(message)
            if results != NOT_IN_PHASE:
                found[name].add(results)
    for entry in audit.get("per_version", []):
        if entry["rubric"] not in found:
            message = f"{entry['rubric']!r} is not a rubric of this run"
            raise AuditError(message)
        found[entry["rubric"]].add_per_version(entry)
    return list(found.values())


def cells(line: str) -> list[str]:
    """Return the cells of a table line, with Linear's escapes undone."""
    return [ESCAPED.sub(r"\1", cell).strip() for cell in line.strip()[1:-1].split("|")]


def previous_values(text: str) -> dict[RowKey, str]:
    """Return the Value per row key from a previous `## Scores` table."""
    if "\n## Scores\n" in f"\n{text}":
        text = f"\n{text}".split("\n## Scores\n", 1)[1].split("\n## ", 1)[0]
    found: dict[RowKey, str] = {}
    names: list[str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or SEPARATOR.match(line):
            continue
        row = cells(line)
        if names is None:
            names = row
            continue
        values = dict(zip(names, row, strict=False))
        try:
            key = (
                values["Rubric"],
                values["Rubric version"],
                values["Craft version"],
                values["Item"],
            )
            found[key] = values["Value"]
        except KeyError:
            # A report in another format, such as CRAFT-85's, gives no trend.
            continue
    return found


def render(results: list[Results], previous: dict[RowKey, str]) -> str:
    """Return the `## Scores` section."""
    rows = [
        (rubric.rubric.title, rubric.rubric.version, version, item, cells)
        for rubric in results
        for version, item, cells in rubric.rows()
    ]
    lines = [
        "## Scores",
        "",
        "| " + " | ".join(HEADER) + " |",
        "|" + "|".join(" --- " for _ in HEADER) + "|",
    ]
    for title, rubric_version, version, item, cells in rows:
        key = (title, rubric_version, version, item)
        line = [*key, *cells, previous.get(key, DASH)]
        lines.append("| " + " | ".join(line) + " |")
    if not rows:
        lines += ["", "No tickets judged."]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    """Print the table, or an error and exit 2."""
    args = argv[1:]
    rubrics = RUBRICS
    if args[:1] == ["--rubrics"] and len(args) > 1:
        rubrics, args = Path(args[1]), args[2:]
    if len(args) not in (1, 2):
        sys.stderr.write(f"{__doc__}\n")
        return 2
    audit = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    previous = (
        previous_values(Path(args[1]).read_text(encoding="utf-8"))
        if len(args) == 2  # noqa: PLR2004 - the audit file and the previous report.
        else {}
    )
    try:
        results = load(audit, rubrics)
    except AuditError as error:
        sys.stderr.write(f"scores.py: {error}\n")
        return 2
    sys.stdout.write(render(results, previous))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
