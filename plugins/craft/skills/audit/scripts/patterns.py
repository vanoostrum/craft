#!/usr/bin/env python3
# Copyright (C) 2026 Theo van Oostrum
"""Find the patterns of an audit, and how the measures of earlier proposals moved.

Usage:
  patterns.py find <scores.md> [<previous report>]
  patterns.py moved --ran <rubric names, comma-separated> <proposals.json> <scores.md>

`scores.md` is the `## Scores` section that `scores.py` printed. The previous
report is the previous audit report's Markdown, as printed or as Linear returns
it.

`find` prints one line per pattern, in the kind order `process logic`, `check`,
`trend`, and within a kind in table order:

    <kind> | <rubric> | <rubric version> | <craft version> | <item> | <value> | <why>

- `process logic`: a check judged once per craft version, with the result
  fail or partial, at any craft version.
- `check`: a per-ticket check whose audit-wide row (craft version `all`) has 3
  or more tickets with fail or partial.
- `trend`: an audit-wide measure value or escape row that is higher than at the
  last audit, when the previous report's same row was also higher than its own
  last audit. This row and the previous report's row each need Judged of at
  least 3, and all three values must be numbers. The Phase score and check rows
  give no trend.

It prints nothing when there is no pattern.

`moved` reads the earlier proposals, a JSON list with one entry per proposal:

    [{"ticket": "CRAFT-101", "title": "Make craft:review read the callers",
      "state": "Backlog", "released": null, "rubric": "Review",
      "rubric_version": "2", "item": "Design and maintainability",
      "value_at_proposal": "0.40"}]

`released` is the craft version of the first release that holds the proposal's
change, or null. `--ran` names the rubric titles of `## Scores` that ran, such
as `Review,Build`; `No rubric` always counts as run. It prints a table with one
row per proposal: Ticket, Title, State, Released in, Measure, Value at
proposal, Value now, and Moved. Value now is this audit's audit-wide row, or for
a check judged once per craft version the row of the newest craft version; else
`no data (rubric not run)`, `no data (rubric version changed)`, or `no data`.
Moved is `not released` before a release, else `better`, `worse`, or `same`
(higher is worse for a measure or an escape rate, lower is worse for a check,
and fail is worse than partial, partial worse than pass), or `no data` when a
value is not a number or a result.
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from scores import ALL, DASH, NO_RUBRIC, SEPARATOR, cells, version_order

MIN_FAILING = 3
MIN_JUDGED = 3
RANK = {"fail": 0, "partial": 1, "pass": 2}
COUNTS = re.compile(r"^(\d+)/(\d+)/(\d+)$")
NO_DATA = "no data"
COLUMNS = (
    "Ticket",
    "Title",
    "State",
    "Released in",
    "Measure",
    "Value at proposal",
    "Value now",
    "Moved",
)


@dataclass(frozen=True)
class Row:
    """One row of a `## Scores` table."""

    rubric: str
    rubric_version: str
    craft_version: str
    item: str
    judged: str
    value: str
    counts: str
    last: str

    @property
    def per_version(self) -> bool:
        """A check judged once per craft version, such as Process logic."""
        return self.judged == DASH

    @property
    def check(self) -> bool:
        """A per-ticket check or the Phase score: it has pass/partial/fail counts."""
        return COUNTS.match(self.counts) is not None

    @property
    def key(self) -> tuple[str, str, str, str]:
        """The rubric, rubric version, craft version, and item."""
        return (self.rubric, self.rubric_version, self.craft_version, self.item)

    def line(self, kind: str, why: str) -> str:
        """Return the pattern line of this row."""
        return " | ".join((kind, *self.key, self.value, why))


def rows(text: str) -> list[Row]:
    """Return the rows of the `## Scores` table in `text`, in table order."""
    if "\n## Scores\n" in f"\n{text}":
        text = f"\n{text}".split("\n## Scores\n", 1)[1].split("\n## ", 1)[0]
    found: list[Row] = []
    names: list[str] | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("|") or SEPARATOR.match(line):
            continue
        values = cells(line)
        if names is None:
            names = values
            continue
        row = dict(zip(names, values, strict=False))
        try:
            found.append(
                Row(
                    row["Rubric"],
                    row["Rubric version"],
                    row["Craft version"],
                    row["Item"],
                    row["Judged"],
                    row["Value"],
                    row["Pass/partial/fail"],
                    row["At last audit"],
                )
            )
        except KeyError:
            # A report in another format, such as CRAFT-85's, has no such rows.
            return []
    return found


def value(text: object) -> float | None:
    """Return a cell as a number, or None for a dash, no data, or a result."""
    try:
        return float(str(text))
    except ValueError:
        return None


def judged(row: Row) -> bool:
    """Whether a row's Judged is at least 3."""
    count = value(row.judged)
    return count is not None and count >= MIN_JUDGED


def process_logic(row: Row) -> str | None:
    """Return the why of a Process logic pattern, or None."""
    if row.per_version and row.value in ("fail", "partial"):
        return f"{row.value} at craft version {row.craft_version}"
    return None


def check(row: Row) -> str | None:
    """Return the why of a check pattern, or None."""
    match = COUNTS.match(row.counts)
    if row.craft_version != ALL or row.item == "Phase score" or match is None:
        return None
    failing = int(match[2]) + int(match[3])
    if failing < MIN_FAILING:
        return None
    return f"{failing} of {row.judged} tickets fail or partial"


def trend(row: Row, previous: dict[tuple[str, str, str, str], Row]) -> str | None:
    """Return the why of a trend pattern, or None."""
    if row.craft_version != ALL or row.check or row.per_version:
        return None
    before = previous.get(row.key)
    if before is None or not judged(row) or not judged(before):
        return None
    oldest, last, now = value(before.last), value(before.value), value(row.value)
    if oldest is None or last is None or now is None or not oldest < last < now:
        return None
    return f"worse two audits in a row: {before.last}, {before.value}, {row.value}"


def find(now: list[Row], previous: list[Row]) -> list[str]:
    """Return the pattern lines, in kind order, then table order."""
    earlier = {row.key: row for row in previous}
    finders = (
        ("process logic", process_logic),
        ("check", check),
        ("trend", lambda row: trend(row, earlier)),
    )
    return [
        row.line(kind, why)
        for kind, finder in finders
        for row in now
        if (why := finder(row)) is not None
    ]


def value_now(proposal: dict[str, object], now: list[Row], ran: set[str]) -> str:
    """Return the Value now of one earlier proposal."""
    rubric, version, item = (
        str(proposal["rubric"]),
        str(proposal["rubric_version"]),
        str(proposal["item"]),
    )
    if rubric != NO_RUBRIC and rubric not in ran:
        return "no data (rubric not run)"
    of_rubric = [row for row in now if row.rubric == rubric]
    same = [row for row in of_rubric if row.rubric_version == version]
    if of_rubric and not same:
        return "no data (rubric version changed)"
    matching = [row for row in same if row.item == item]
    per_version = [row for row in matching if row.per_version]
    if per_version:
        newest = max(per_version, key=lambda row: version_order(row.craft_version))
        return newest.value
    audit_wide = [row for row in matching if row.craft_version == ALL]
    return audit_wide[0].value if audit_wide else NO_DATA


def moved_value(before: object, now: str, *, check: bool) -> str:
    """Return better, worse, same, or no data: higher is worse unless a check."""
    if str(before) in RANK and now in RANK:
        old, new = RANK[str(before)], RANK[now]
    else:
        old_number, new_number = value(before), value(now)
        if old_number is None or new_number is None:
            return NO_DATA
        old, new = (old_number, new_number) if check else (-old_number, -new_number)
    if new == old:
        return "same"
    return "better" if new > old else "worse"


def moved(proposals: list[dict[str, object]], now: list[Row], ran: set[str]) -> str:
    """Return the table of the earlier proposals."""
    lines = [
        "| " + " | ".join(COLUMNS) + " |",
        "|" + "|".join(" --- " for _ in COLUMNS) + "|",
    ]
    for proposal in proposals:
        current = value_now(proposal, now, ran)
        rubric, version = str(proposal["rubric"]), str(proposal["rubric_version"])
        measure = f"{rubric}: " if version == DASH else f"{rubric} {version}: "
        is_check = any(
            row.check
            for row in now
            if (row.rubric, row.rubric_version, row.item)
            == (rubric, version, proposal["item"])
        )
        released = proposal["released"]
        movement = (
            "not released"
            if released is None
            else moved_value(proposal["value_at_proposal"], current, check=is_check)
        )
        cells_ = (
            str(proposal["ticket"]),
            str(proposal["title"]),
            str(proposal["state"]),
            DASH if released is None else str(released),
            f"{measure}{proposal['item']}",
            str(proposal["value_at_proposal"]),
            current,
            movement,
        )
        lines.append("| " + " | ".join(cells_) + " |")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    """Run a command, or print the usage text and exit 2."""
    args = argv[1:]
    if args[:1] == ["find"] and len(args) in (2, 3):
        now = rows(Path(args[1]).read_text(encoding="utf-8"))
        previous = (
            rows(Path(args[2]).read_text(encoding="utf-8")) if len(args) == 3 else []  # noqa: PLR2004 - find, scores, previous.
        )
        lines = find(now, previous)
        sys.stdout.write("".join(f"{line}\n" for line in lines))
        return 0
    if args[:2] == ["moved", "--ran"] and len(args) == 5:  # noqa: PLR2004 - the usage.
        ran = {name.strip() for name in args[2].split(",") if name.strip()}
        proposals = json.loads(Path(args[3]).read_text(encoding="utf-8"))
        now = rows(Path(args[4]).read_text(encoding="utf-8"))
        sys.stdout.write(moved(proposals, now, ran))
        return 0
    sys.stderr.write(f"{__doc__}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
