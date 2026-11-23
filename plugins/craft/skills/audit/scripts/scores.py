#!/usr/bin/env python3
# Copyright (C) 2026 Theo van Oostrum
"""Print the `## Scores` table of an audit report.

Usage: scores.py <audit.json> [<previous report or table>]

`audit.json` holds:

    {"rubric_version": "1",
     "prs": [{"project": "...", "group": "Apps", "pr": 12, "craft_version": "2.9.1"}],
     "findings": [{"project": "...", "pr": 12, "item": "Design",
                   "severity": "major", "file": "...", "text": "..."}]}

The previous file is the previous audit report's Markdown, or only its
`## Scores` table, as printed here or as Linear returns it. The table has a row
per project and craft version, a total row per project, and a total row per
group. The column "Major per PR at last audit" comes from the previous row with
the same key and the same rubric version, else it is a dash.
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RUBRIC = Path(__file__).resolve().parents[1] / "rubric.md"
GROUPS = ("Apps", "Craft")
SEVERITIES = ("major", "minor")
TOTAL = "Total"
DASH = "—"
FIXED = (
    "Group",
    "Project",
    "Craft version",
    "Rubric version",
    "PRs",
    "Major",
    "Minor",
    "Major per PR",
    "Major per PR at last audit",
)
ESCAPED = re.compile(r"\\([!-/:-@\[-`{-~])")
SEPARATOR = re.compile(r"^\|(\s*:?-+:?\s*\|)+$")

type Key = tuple[str, str, str]
type PrId = tuple[str, int]
type Json = dict[str, Any]  # Parsed JSON, checked in `parse_audit`.


class AuditError(Exception):
    """The audit file does not match the rubric or itself."""


def rubric_items() -> list[str]:
    """Return the item names under `## Items` in the core rubric."""
    text = RUBRIC.read_text(encoding="utf-8")
    items = text.split("\n## Items\n", 1)[1].split("\n## ", 1)[0]
    headings = re.finditer(r"^### (.+)$", items, re.MULTILINE)
    return [match.group(1) for match in headings]


@dataclass
class Score:
    """The counts of one row."""

    prs: set[PrId] = field(default_factory=set)
    counts: dict[tuple[str, str], int] = field(default_factory=dict)

    def add(self, item: str, severity: str) -> None:
        """Count one finding."""
        self.counts[item, severity] = self.counts.get((item, severity), 0) + 1

    def total(self, severity: str) -> int:
        """Return the number of findings of one severity."""
        return sum(n for (_, s), n in self.counts.items() if s == severity)

    def item(self, item: str) -> str:
        """Return the major and minor count of one item, such as `1/2`."""
        major = self.counts.get((item, "major"), 0)
        return f"{major}/{self.counts.get((item, 'minor'), 0)}"

    def major_per_pr(self) -> str:
        """Return the headline, with two decimals."""
        return f"{self.total('major') / len(self.prs):.2f}"


def version_order(version: str) -> tuple[tuple[int, int | str], ...]:
    """Sort craft versions by number, such as 2.9.0 before 2.10.0."""
    return tuple(
        (0, int(part)) if part.isdigit() else (1, part) for part in version.split(".")
    )


def row_order(key: Key) -> tuple[object, ...]:
    """Order rows: per group, per project its versions then its total."""
    group, project, version = key
    return (
        GROUPS.index(group),
        project == TOTAL,
        project,
        version == TOTAL,
        version_order(version),
    )


@dataclass(frozen=True)
class Finding:
    """One audit finding, as the score counts it."""

    pr: PrId
    item: str
    severity: str


def parse_audit(audit: Json, items: list[str]) -> tuple[dict[PrId, Key], list[Finding]]:
    """Return the version row key per audited PR, and the findings, checked."""
    prs: dict[PrId, Key] = {}
    for pr in audit["prs"]:
        if pr["group"] not in GROUPS:
            message = f"group {pr['group']!r} is not one of {', '.join(GROUPS)}"
            raise AuditError(message)
        prs[pr["project"], int(pr["pr"])] = (
            pr["group"],
            pr["project"],
            str(pr["craft_version"]),
        )
    findings = []
    for raw in audit["findings"]:
        finding = Finding(
            (raw["project"], int(raw["pr"])), raw["item"], raw["severity"]
        )
        if finding.pr not in prs:
            pr_name = f"{finding.pr[0]} #{finding.pr[1]}"
            message = f"finding on {pr_name}, which is not an audited PR"
            raise AuditError(message)
        if finding.item not in items:
            message = f"item {finding.item!r} is not in the rubric"
            raise AuditError(message)
        if finding.severity not in SEVERITIES:
            message = f"severity {finding.severity!r} is not major or minor"
            raise AuditError(message)
        findings.append(finding)
    return prs, findings


def row_keys(version_row: Key) -> list[Key]:
    """Return the keys a PR counts in: its version row, project, and group."""
    group, project, _ = version_row
    return [version_row, (group, project, TOTAL), (group, TOTAL, TOTAL)]


def score_rows(prs: dict[PrId, Key], findings: list[Finding]) -> dict[Key, Score]:
    """Return a score per row key: version rows, project totals, group totals."""
    rows: dict[Key, Score] = {}
    for pr, version_row in prs.items():
        for key in row_keys(version_row):
            rows.setdefault(key, Score()).prs.add(pr)
    for finding in findings:
        for key in row_keys(prs[finding.pr]):
            rows[key].add(finding.item, finding.severity)
    return rows


def cells(line: str) -> list[str]:
    """Return the cells of a table line, with Linear's escapes undone."""
    return [ESCAPED.sub(r"\1", cell).strip() for cell in line.strip()[1:-1].split("|")]


def previous_scores(text: str) -> dict[tuple[str, Key], str]:
    """Return "Major per PR" per rubric version and key from a previous table."""
    if "\n## Scores\n" in f"\n{text}":
        text = f"\n{text}".split("\n## Scores\n", 1)[1].split("\n## ", 1)[0]
    found: dict[tuple[str, Key], str] = {}
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
            key = (values["Group"], values["Project"], values["Craft version"])
            found[values["Rubric version"], key] = values["Major per PR"]
        except KeyError:
            continue
    return found


def render(
    rubric_version: str,
    rows: dict[Key, Score],
    items: list[str],
    previous: dict[tuple[str, Key], str],
) -> str:
    """Return the `## Scores` section."""
    header = [*FIXED, *items]
    lines = [
        "## Scores",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "|".join(" --- " for _ in header) + "|",
    ]
    for key in sorted(rows, key=row_order):
        score = rows[key]
        values = [
            *key,
            rubric_version,
            str(len(score.prs)),
            str(score.total("major")),
            str(score.total("minor")),
            score.major_per_pr(),
            previous.get((rubric_version, key), DASH),
            *(score.item(i) for i in items),
        ]
        lines.append("| " + " | ".join(values) + " |")
    if not rows:
        lines += ["", "No PRs audited."]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    """Print the table, or an error and exit 2."""
    if len(argv) not in (2, 3):
        sys.stderr.write(f"{__doc__}\n")
        return 2
    audit = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    previous = (
        previous_scores(Path(argv[2]).read_text(encoding="utf-8"))
        if len(argv) == 3  # noqa: PLR2004 - the audit file and the previous file.
        else {}
    )
    items = rubric_items()
    try:
        prs, findings = parse_audit(audit, items)
    except AuditError as error:
        sys.stderr.write(f"scores.py: {error}\n")
        return 2
    rows = score_rows(prs, findings)
    sys.stdout.write(render(str(audit["rubric_version"]), rows, items, previous))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
