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
                      "item": "Process logic", "result": "pass"}],
     "escapes": {"searched": [{"ticket": "CRAFT-72", "pr": 47, "spec": true,
                               "versions": {"plan": "2.9.0", "spec": "2.9.1",
                                            "build": "2.9.1", "review": "2.9.1"}}],
                 "traces": [{"ticket": "CRAFT-72", "source": "vanoostrum/craft#48",
                             "answer": "escape", "phase": "review"},
                            {"ticket": "CRAFT-72", "source": "merge gate: rename it",
                             "answer": "not an escape", "reason": "owner choice"}]}}

A check result is `pass`, `partial`, `fail`, or `no data`. A measure holds the
`values` that its script printed, or `{}` for no data. A rubric that does not
judge a ticket holds `"not in this phase"` instead of results.

The table has one row per rubric, rubric version, craft version, and item: the
Phase score (the share of per-ticket checks passed), each per-ticket check, one
row per measure value (the median), and each check judged once per craft
version. Judged counts what the value is based on: the check answers other
than no data, or the tickets with data for a measure value.

`escapes` holds the searched tickets, one entry per ticket, each with `spec`
(whether its description has a `## Spec`) and its craft version per phase
(`plan`, `spec`, `build`, `review`), and the escape traces, each with `answer`
`escape` (with the `phase` it traces to), `not an escape`, or `not judged` (with
a `reason`).
Each phase gets one escape row per craft version: the row of the Escape item
of the rubric whose `Phase:` is that phase, when that rubric ran, or a
`No rubric` row, Item `Escapes: <phase>`, when no rubric file has an Escape
item for it. Judged is the searched tickets at that craft version in that
phase; with `Applies to: tickets with a spec`, only those with a spec. Value
is the traces with the answer `escape` of the tickets in Judged, divided by
Judged, or no data when Judged is 0. "At last audit" is the Value of the same
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

from rubric import APPLIES_TO, RUBRICS, Item, Rubric, RubricError, find, parse, paths

RESULTS = ("pass", "partial", "fail")
NO_DATA = "no data"
NOT_IN_PHASE = "not in this phase"
PHASE_SCORE = "Phase score"
DASH = "—"
PHASES = ("plan", "spec", "build", "review")
ESCAPE = "escape"
ANSWERS = (ESCAPE, "not an escape", "not judged")
NO_RUBRIC = "No rubric"
HEADER = (
    "Rubric",
    "Rubric version",
    "Craft version",
    "Item",
    "Judged",
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


type Cells = tuple[str, str, str]  # Judged, Value, and Pass/partial/fail.
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


def escape_cells(judged: int, escapes: int) -> Cells:
    """Return the cells of an escape row: the escapes per judged ticket."""
    if not judged:
        return "0", NO_DATA, DASH
    return str(judged), f"{escapes / judged:.2f}", DASH


def check_escapes(escapes: Json) -> None:
    """Raise `AuditError` when the `escapes` key does not have its shape."""
    tickets = set()
    for entry in escapes["searched"]:
        versions = entry["versions"]
        if set(versions) != set(PHASES):
            message = f"{entry['ticket']}: versions must name {', '.join(PHASES)}"
            raise AuditError(message)
        if entry["ticket"] in tickets:
            message = f"{entry['ticket']} is searched twice: one entry per ticket"
            raise AuditError(message)
        tickets.add(entry["ticket"])
    for found in escapes["traces"]:
        if found["ticket"] not in tickets:
            message = f"{found['ticket']} is not a searched ticket"
            raise AuditError(message)
        if found["answer"] not in ANSWERS:
            message = f"answer {found['answer']!r} is not one of {ANSWERS}"
            raise AuditError(message)
        if found["answer"] == ESCAPE and found.get("phase") not in PHASES:
            message = f"phase {found.get('phase')!r} is not one of {PHASES}"
            raise AuditError(message)


def escape_rates(escapes: Json, phase: str, *, spec_only: bool) -> dict[str, Cells]:
    """Return the escape cells of one phase, per craft version."""
    counts: dict[str, list[int]] = {}
    for entry in escapes["searched"]:
        count = counts.setdefault(str(entry["versions"][phase]), [0, 0])
        if spec_only and not entry["spec"]:
            continue
        count[0] += 1
        count[1] += sum(
            1
            for t in escapes["traces"]
            if (t["ticket"], t["answer"], t.get("phase"))
            == (entry["ticket"], ESCAPE, phase)
        )
    return {version: escape_cells(*count) for version, count in counts.items()}


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
    escape: Cells | None = None


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
                if item.kind == "Escape" and version.escape is not None:
                    rows.append((craft_version, item.name, version.escape))
        return rows


def version_order(version: str) -> tuple[tuple[int, int | str], ...]:
    """Sort craft versions by number, such as 2.9.0 before 2.10.0."""
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part) for part in version.split(".")
    )


def escape_owners(rubrics: Path) -> dict[str, Rubric]:
    """Return the rubric with an Escape item per phase, from every rubric file."""
    owners: dict[str, Rubric] = {}
    for path in paths(rubrics):
        try:
            rubric = parse(path)
        except RubricError as error:
            message = f"{path.name}: {error}"
            raise AuditError(message) from error
        if any(item.kind == "Escape" for item in rubric.items):
            owners[rubric.phase] = rubric
    return owners


def add_escapes(found: dict[str, Results], escapes: Json, rubrics: Path) -> list[Row]:
    """Add the escape rows to the rubrics that ran; return the `No rubric` rows."""
    check_escapes(escapes)
    owners = escape_owners(rubrics)
    rows: list[Row] = []
    for phase in PHASES:
        owner = owners.get(phase)
        spec_only = owner is not None and owner.applies_to == APPLIES_TO
        rates = escape_rates(escapes, phase, spec_only=spec_only)
        if owner is None:
            rows += [
                (version, f"Escapes: {phase}", rates[version])
                for version in sorted(rates, key=version_order)
            ]
        elif owner.name in found:
            for version, cells in rates.items():
                found[owner.name].version(version).escape = cells
    return rows


def load(audit: Json, rubrics: Path) -> tuple[list[Results], list[Row]]:
    """Return the checked results per rubric, in run order, and `No rubric` rows."""
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
    no_rubric = (
        add_escapes(found, audit["escapes"], rubrics) if "escapes" in audit else []
    )
    return list(found.values()), no_rubric


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


def render(
    results: list[Results], no_rubric: list[Row], previous: dict[RowKey, str]
) -> str:
    """Return the `## Scores` section."""
    rows = [
        (rubric.rubric.title, rubric.rubric.version, version, item, cells)
        for rubric in results
        for version, item, cells in rubric.rows()
    ] + [(NO_RUBRIC, DASH, version, item, cells) for version, item, cells in no_rubric]
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
        results, no_rubric = load(audit, rubrics)
    except AuditError as error:
        sys.stderr.write(f"scores.py: {error}\n")
        return 2
    sys.stdout.write(render(results, no_rubric, previous))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
