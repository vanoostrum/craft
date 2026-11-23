# Copyright (C) 2026 Theo van Oostrum
"""`scores.py` prints the `## Scores` table of an audit report.

The script runs as a command, as the audit runs it. Every fixture is synthetic:
the projects, PRs, and findings are made up (`docs/adr/0009`).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

type Json = dict[str, object]

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "craft" / "skills" / "audit" / "scripts" / "scores.py"
ITEMS = ("Design", "Complexity", "Duplication", "Naming", "Tests")
HEADER = (
    "Group",
    "Project",
    "Craft version",
    "Rubric version",
    "PRs",
    "Major",
    "Minor",
    "Major per PR",
    "Major per PR at last audit",
    *ITEMS,
)


def pr(project: str, number: int, version: str, group: str = "Apps") -> Json:
    """Return one audited PR."""
    return {
        "project": project,
        "group": group,
        "pr": number,
        "craft_version": version,
    }


def finding(project: str, number: int, item: str, severity: str) -> Json:
    """Return one audit finding on a PR."""
    return {
        "project": project,
        "pr": number,
        "item": item,
        "severity": severity,
        "file": "src/app.py:10",
        "text": "A made-up finding.",
    }


def run(
    tmp_path: Path,
    prs: list[Json],
    findings: list[Json],
    previous: str | None = None,
    rubric_version: str = "1",
) -> subprocess.CompletedProcess[str]:
    """Run `scores.py` on an audit file and an optional previous table."""
    audit = tmp_path / "audit.json"
    audit.write_text(
        json.dumps(
            {"rubric_version": rubric_version, "prs": prs, "findings": findings}
        ),
        encoding="utf-8",
    )
    args = [sys.executable, str(SCRIPT), str(audit)]
    if previous is not None:
        old = tmp_path / "previous.md"
        old.write_text(previous, encoding="utf-8")
        args.append(str(old))
    return subprocess.run(  # noqa: S603
        args, capture_output=True, text=True, check=False
    )


def table(output: str) -> list[dict[str, str]]:
    """Return the rows of the printed table, each as a dict by header name."""
    lines = [line for line in output.splitlines() if line.startswith("|")]
    names = [cell.strip() for cell in lines[0].strip("|").split("|")]
    return [
        dict(zip(names, (c.strip() for c in line.strip("|").split("|")), strict=True))
        for line in lines[2:]
    ]


def row(
    rows: list[dict[str, str]], group: str, project: str, version: str
) -> dict[str, str]:
    """Return the row with this key."""
    matches = [
        r
        for r in rows
        if (r["Group"], r["Project"], r["Craft version"]) == (group, project, version)
    ]
    assert len(matches) == 1, f"no single row {group}/{project}/{version}"
    return matches[0]


PRS = [
    pr("Shop", 1, "2.9.0"),
    pr("Shop", 2, "2.9.0"),
    pr("Shop", 3, "2.9.1"),
    pr("Notes", 7, "2.9.1"),
    pr("Craft", 40, "2.9.1", group="Craft"),
]
FINDINGS = [
    finding("Shop", 1, "Design", "major"),
    finding("Shop", 1, "Naming", "minor"),
    finding("Shop", 3, "Tests", "major"),
    finding("Shop", 3, "Tests", "minor"),
    finding("Notes", 7, "Duplication", "major"),
    finding("Craft", 40, "Complexity", "minor"),
]


@pytest.fixture
def first(tmp_path: Path) -> str:
    """Return the output of a first audit, with no previous table."""
    result = run(tmp_path, PRS, FINDINGS)
    assert result.returncode == 0, result.stderr
    return result.stdout


# Criterion 7: the rows and their columns.


def test_the_table_has_a_heading_and_the_columns(first: str) -> None:
    """The output is a `## Scores` table with every column the spec names."""
    assert first.startswith("## Scores\n")
    header = next(line for line in first.splitlines() if line.startswith("|"))
    assert tuple(c.strip() for c in header.strip("|").split("|")) == HEADER


def test_a_row_per_project_and_craft_version(first: str) -> None:
    """Each project and craft version has a row with its own counts."""
    rows = table(first)
    old = row(rows, "Apps", "Shop", "2.9.0")
    assert (old["PRs"], old["Major"], old["Minor"]) == ("2", "1", "1")
    assert old["Major per PR"] == "0.50"
    assert (old["Design"], old["Naming"], old["Tests"]) == ("1/0", "0/1", "0/0")
    new = row(rows, "Apps", "Shop", "2.9.1")
    assert (new["PRs"], new["Major"], new["Minor"], new["Tests"]) == (
        "1",
        "1",
        "1",
        "1/1",
    )
    assert all(r["Rubric version"] == "1" for r in rows)


def test_an_audited_pr_with_no_findings_counts(first: str) -> None:
    """PR 2 has no findings, and still counts in the PRs of its rows."""
    rows = table(first)
    assert row(rows, "Apps", "Shop", "2.9.0")["PRs"] == "2"
    assert row(rows, "Apps", "Shop", "Total")["PRs"] == "3"


def test_a_total_row_per_project(first: str) -> None:
    """The project total adds up the project's version rows."""
    total = row(table(first), "Apps", "Shop", "Total")
    assert (total["PRs"], total["Major"], total["Minor"]) == ("3", "2", "2")
    assert total["Major per PR"] == "0.67"
    assert total["Tests"] == "1/1"


def test_a_total_row_per_group(first: str) -> None:
    """Apps and Craft each get a total, and craft's PRs stay apart from the apps."""
    rows = table(first)
    apps = row(rows, "Apps", "Total", "Total")
    assert (apps["PRs"], apps["Major"], apps["Minor"]) == ("4", "3", "2")
    assert apps["Major per PR"] == "0.75"
    craft = row(rows, "Craft", "Total", "Total")
    assert (craft["PRs"], craft["Major"], craft["Minor"]) == ("1", "0", "1")
    assert craft["Complexity"] == "0/1"


def test_rows_come_in_a_fixed_order(first: str) -> None:
    """Apps before Craft; per project its versions, then its total; then the group."""
    keys = [(r["Group"], r["Project"], r["Craft version"]) for r in table(first)]
    assert keys == [
        ("Apps", "Notes", "2.9.1"),
        ("Apps", "Notes", "Total"),
        ("Apps", "Shop", "2.9.0"),
        ("Apps", "Shop", "2.9.1"),
        ("Apps", "Shop", "Total"),
        ("Apps", "Total", "Total"),
        ("Craft", "Craft", "2.9.1"),
        ("Craft", "Craft", "Total"),
        ("Craft", "Total", "Total"),
    ]


def test_with_no_previous_table_the_trend_is_a_dash(first: str) -> None:
    """A first audit has nothing to compare with."""
    assert {r["Major per PR at last audit"] for r in table(first)} == {"—"}


def test_no_audited_prs_prints_the_header_and_a_line(tmp_path: Path) -> None:
    """Review focus 1: with no PRs, the header and `No PRs audited.`."""
    result = run(tmp_path, [], [])
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("## Scores\n")
    assert table(result.stdout) == []
    assert "No PRs audited." in result.stdout


def test_a_finding_on_a_pr_that_is_not_audited_fails(tmp_path: Path) -> None:
    """A finding must belong to an audited PR, so no count goes astray."""
    result = run(tmp_path, PRS, [finding("Shop", 99, "Design", "major")])
    assert result.returncode != 0
    assert "Shop #99" in result.stderr


def test_an_unknown_rubric_item_fails(tmp_path: Path) -> None:
    """A finding names one of the rubric's items."""
    result = run(tmp_path, PRS, [finding("Shop", 1, "Style", "major")])
    assert result.returncode != 0
    assert "Style" in result.stderr


# Criterion 8: the trend from the previous table.


def second(
    tmp_path: Path, previous: str, rubric_version: str = "1"
) -> list[dict[str, str]]:
    """Return the rows of a second audit that reads `previous`."""
    prs = [pr("Shop", 10, "2.9.1"), pr("Craft", 50, "2.9.2", group="Craft")]
    result = run(tmp_path, prs, [], previous, rubric_version)
    assert result.returncode == 0, result.stderr
    return table(result.stdout)


def test_the_trend_comes_from_the_row_with_the_same_key(
    tmp_path: Path, first: str
) -> None:
    """A version row, a project total, and a group total each find their own row."""
    rows = second(tmp_path, first)
    assert row(rows, "Apps", "Shop", "2.9.1")["Major per PR at last audit"] == "1.00"
    assert row(rows, "Apps", "Shop", "Total")["Major per PR at last audit"] == "0.67"
    assert row(rows, "Apps", "Total", "Total")["Major per PR at last audit"] == "0.75"
    assert row(rows, "Craft", "Total", "Total")["Major per PR at last audit"] == "0.00"


def test_a_row_with_no_previous_row_gets_a_dash(tmp_path: Path, first: str) -> None:
    """Craft 2.9.2 is new, so its version row has nothing to compare with."""
    rows = second(tmp_path, first)
    assert row(rows, "Craft", "Craft", "2.9.2")["Major per PR at last audit"] == "—"


def test_another_rubric_version_is_never_compared(tmp_path: Path, first: str) -> None:
    """Review focus 5: after a rubric change, every row shows a dash."""
    rows = second(tmp_path, first, rubric_version="2")
    assert {r["Major per PR at last audit"] for r in rows} == {"—"}
    assert {r["Rubric version"] for r in rows} == {"2"}


def test_the_previous_table_is_found_in_a_whole_report(
    tmp_path: Path, first: str
) -> None:
    """The audit can pass the whole previous report, not only its table."""
    report = (
        f"## Summary\n\n| Project | Major |\n| --- | --- |\n| Shop | 9 |\n\n{first}"
    )
    report += "\n## Findings\n\n| Project | PR |\n| --- | --- |\n| Shop | 1 |\n"
    rows = second(tmp_path, report)
    assert row(rows, "Apps", "Shop", "Total")["Major per PR at last audit"] == "0.67"


def linear_form(markdown: str) -> str:
    r"""Return a table as Linear returns it after a round trip.

    Linear writes separator rows as `| -- |` and escapes Markdown characters
    with a backslash, such as `\#` and `\_`. Synthetic project names with
    those characters show that the key still matches.
    """
    lines = []
    for line in markdown.splitlines():
        if line.startswith("| ---"):
            cells = line.strip("|").split("|")
            lines.append("|" + "|".join(" -- " for _ in cells) + "|")
        else:
            lines.append(line.replace("#", "\\#").replace("_", "\\_"))
    return "\n".join(lines) + "\n"


def test_the_previous_table_is_read_in_the_form_linear_returns(
    tmp_path: Path,
) -> None:
    """Escaped characters and short separators still match the same key."""
    prs = [pr("Shop_v2", 1, "2.9.1"), pr("App #2", 2, "2.9.1")]
    findings = [finding("Shop_v2", 1, "Design", "major")]
    first = run(tmp_path, prs, findings)
    assert first.returncode == 0, first.stderr
    previous = linear_form(first.stdout)
    assert "\\_" in previous
    assert "\\#" in previous
    assert "| -- |" in previous
    result = run(tmp_path, prs, [], previous)
    assert result.returncode == 0, result.stderr
    rows = table(result.stdout)
    assert row(rows, "Apps", "Shop_v2", "2.9.1")["Major per PR at last audit"] == (
        "1.00"
    )
    assert row(rows, "Apps", "App #2", "Total")["Major per PR at last audit"] == "0.00"


def test_unknown_columns_in_the_previous_table_are_ignored(
    tmp_path: Path, first: str
) -> None:
    """A later audit may add a column, such as a miss rate; the trend still works."""
    lines = first.splitlines()
    changed = []
    for line in lines:
        if line.startswith("| Group"):
            changed.append("| Miss rate " + line)
        elif line.startswith("| ---"):
            changed.append("| --- " + line)
        elif line.startswith("|"):
            changed.append("| 10% " + line)
        else:
            changed.append(line)
    rows = second(tmp_path, "\n".join(changed) + "\n")
    assert row(rows, "Apps", "Shop", "Total")["Major per PR at last audit"] == "0.67"


def test_the_output_is_its_own_previous_table(tmp_path: Path, first: str) -> None:
    """Rerun with the same input and its own output: the trend equals the score."""
    result = run(tmp_path, PRS, FINDINGS, first)
    assert result.returncode == 0, result.stderr
    for r in table(result.stdout):
        assert r["Major per PR at last audit"] == r["Major per PR"]
