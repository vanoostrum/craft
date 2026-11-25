# Copyright (C) 2026 Theo van Oostrum
"""`scores.py` prints the `## Scores` table of an audit report.

The script runs as a command, as the audit runs it. Every fixture is synthetic:
the projects, tickets, and results are made up (`docs/adr/0009`).
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

type Json = dict[str, object]

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "craft" / "skills" / "audit" / "scripts" / "scores.py"
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
ROUNDS = "Findings rounds: Rounds until PASS"
BLOCKING = "Findings rounds: Blocking per round"

SPEED = """# Speed rubric

Rubric version: 3
Phase: custom

## Items

### Quick

Kind: Check
Reads: The digest.
Score: The share that passes.
Pass: Quick.
Partial: Slow.
Fail: Very slow.

### Late bugs

Kind: Escape
Reads: Later fix PRs.
Score: The count per ticket.

### Hooks

Kind: Check
Per: craft version
Reads: The hooks.
Score: Once per craft version.
Pass: Right.
Partial: Partly right.
Fail: Wrong.
"""


def checks(
    read: str = "pass", criteria: str = "pass", design: str = "fail"
) -> dict[str, str]:
    """Return the per-ticket check results of the Review rubric."""
    return {
        "Read in context": read,
        "Criteria evidence": criteria,
        "Design and maintainability": design,
    }


def judged(
    version: str,
    results: dict[str, str] | None = None,
    rounds: float | None = 1,
    blocking: float = 0,
) -> Json:
    """Return one ticket's results for the Review rubric."""
    values = {
        "Rounds until PASS": rounds,
        "Blocking per round": None if rounds is None else blocking,
    }
    return {
        "craft_version": version,
        "checks": checks() if results is None else results,
        "measures": {"Findings rounds": values},
    }


def ticket(number: int, review: Json | str, project: str = "Demo") -> Json:
    """Return one audited ticket."""
    return {
        "project": project,
        "ticket": f"CRAFT-{number}",
        "pr": number,
        "rubrics": {"review": review},
    }


def run(  # noqa: PLR0913 - each argument is one part of the fixture.
    tmp_path: Path,
    tickets: list[Json],
    *,
    per_version: list[Json] | None = None,
    previous: str | None = None,
    rubrics: list[str] | None = None,
    rubrics_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `scores.py` on an audit file and an optional previous report."""
    audit = tmp_path / "audit.json"
    audit.write_text(
        json.dumps(
            {
                "rubrics": rubrics or ["review"],
                "tickets": tickets,
                "per_version": per_version or [],
            }
        ),
        encoding="utf-8",
    )
    args = [sys.executable, str(SCRIPT)]
    if rubrics_dir is not None:
        args += ["--rubrics", str(rubrics_dir)]
    args.append(str(audit))
    if previous is not None:
        old = tmp_path / "previous.md"
        old.write_text(previous, encoding="utf-8")
        args.append(str(old))
    return subprocess.run(  # noqa: S603
        args, capture_output=True, text=True, check=False
    )


def table(output: str) -> list[dict[str, str]]:
    """Return the data rows of the printed table, keyed by column."""
    lines = [line for line in output.splitlines() if line.startswith("|")]
    names = [cell.strip() for cell in lines[0].strip("|").split("|")]
    return [
        dict(zip(names, (c.strip() for c in line.strip("|").split("|")), strict=True))
        for line in lines[2:]
    ]


def row(output: str, version: str, item: str, rubric: str = "Review") -> dict[str, str]:
    """Return the row of one rubric, craft version, and item."""
    rows = [
        r
        for r in table(output)
        if (r["Rubric"], r["Craft version"], r["Item"]) == (rubric, version, item)
    ]
    assert len(rows) == 1, (version, item, output)
    return rows[0]


def scores(tmp_path: Path, tickets: list[Json], **kwargs: Any) -> str:  # noqa: ANN401 - passed on to `run`.
    """Run `scores.py`, check that it passed, and return its output."""
    result = run(tmp_path, tickets, **kwargs)
    assert result.returncode == 0, result.stderr
    return result.stdout


# Criterion 9: the rows.


def test_the_table_has_its_heading_and_columns(tmp_path: Path) -> None:
    """A `## Scores` section with the fixed columns."""
    out = scores(tmp_path, [ticket(1, judged("2.9.0"))])
    assert out.startswith("## Scores\n\n")
    assert tuple(table(out)[0]) == HEADER


def test_one_row_per_rubric_version_craft_version_and_item(tmp_path: Path) -> None:
    """Phase score first, then the items in rubric order, per craft version."""
    out = scores(
        tmp_path,
        [ticket(1, judged("2.10.0")), ticket(2, judged("2.9.0"))],
        per_version=[
            {"rubric": "review", "craft_version": v, "item": "Process logic"}
            | {"result": "pass"}
            for v in ("2.10.0", "2.9.0")
        ],
    )
    keys = [(r["Craft version"], r["Item"]) for r in table(out)]
    items = [
        "Phase score",
        "Read in context",
        "Criteria evidence",
        "Design and maintainability",
        ROUNDS,
        BLOCKING,
    ]
    assert keys == [
        *(("2.9.0", item) for item in items),
        ("2.9.0", "Process logic"),
        *(("2.10.0", item) for item in items),
        ("2.10.0", "Process logic"),
    ]
    assert {r["Rubric version"] for r in table(out)} == {"1"}


def test_a_check_row_shows_its_share_and_counts(tmp_path: Path) -> None:
    """Pass counts 1; partial and fail count 0; no data is not in the share."""
    out = scores(
        tmp_path,
        [
            ticket(1, judged("2.9.0", checks(read="pass"))),
            ticket(2, judged("2.9.0", checks(read="partial"))),
            ticket(3, judged("2.9.0", checks(read="fail"))),
            ticket(4, judged("2.9.0", checks(read="no data"))),
        ],
    )
    read = row(out, "2.9.0", "Read in context")
    assert (read["Judged"], read["Value"], read["Pass/partial/fail"]) == (
        "3",
        "0.33",
        "1/1/1",
    )


def test_the_phase_score_counts_only_per_ticket_checks(tmp_path: Path) -> None:
    """Process logic is shown next to it, not in it."""
    out = scores(
        tmp_path,
        [ticket(1, judged("2.9.0", checks("pass", "pass", "fail")))],
        per_version=[
            {"rubric": "review", "craft_version": "2.9.0", "item": "Process logic"}
            | {"result": "fail"}
        ],
    )
    phase = row(out, "2.9.0", "Phase score")
    assert (phase["Judged"], phase["Value"], phase["Pass/partial/fail"]) == (
        "3",
        "0.67",
        "2/0/1",
    )
    logic = row(out, "2.9.0", "Process logic")
    assert (logic["Value"], logic["Judged"], logic["Pass/partial/fail"]) == (
        "fail",
        "—",
        "—",
    )


def test_measures_are_medians_per_craft_version(tmp_path: Path) -> None:
    """One row per value; no data is left out of the median."""
    out = scores(
        tmp_path,
        [
            ticket(1, judged("2.9.0", rounds=1, blocking=0)),
            ticket(2, judged("2.9.0", rounds=2, blocking=1)),
            ticket(3, judged("2.9.0", rounds=5, blocking=0.5)),
            ticket(4, judged("2.9.0", rounds=None)),
        ],
    )
    assert row(out, "2.9.0", ROUNDS)["Value"] == "2"
    assert row(out, "2.9.0", ROUNDS)["Judged"] == "3"
    assert row(out, "2.9.0", BLOCKING)["Value"] == "0.50"


def test_a_version_with_no_data_says_so(tmp_path: Path) -> None:
    """Review focus 1: no transcripts gives no data, not a zero."""
    no_data = checks("no data", "pass", "no data")
    out = scores(tmp_path, [ticket(1, judged("2.9.0", no_data, rounds=None))])
    assert row(out, "2.9.0", "Read in context")["Value"] == "no data"
    assert row(out, "2.9.0", "Criteria evidence")["Value"] == "1.00"
    assert row(out, "2.9.0", ROUNDS)["Value"] == "no data"
    assert row(out, "2.9.0", ROUNDS)["Judged"] == "0"


def test_a_ticket_not_in_this_phase_counts_nowhere(tmp_path: Path) -> None:
    """Review focus 5: a plan PR is listed, but gets no row."""
    out = scores(tmp_path, [ticket(1, "not in this phase")])
    assert table(out) == []
    assert "No tickets judged." in out


def test_an_escape_item_gets_no_row(tmp_path: Path) -> None:
    """Escapes are not scored yet; a custom rubric's other items are."""
    write = tmp_path / "rubrics" / "custom" / "speed.md"
    write.parent.mkdir(parents=True)
    write.write_text(SPEED, encoding="utf-8")
    speed = {"craft_version": "2.9.0", "checks": {"Quick": "pass"}, "measures": {}}
    out = scores(
        tmp_path,
        [
            {
                "project": "Demo",
                "ticket": "CRAFT-1",
                "pr": 1,
                "rubrics": {"speed": speed},
            }
        ],
        per_version=[
            {"rubric": "speed", "craft_version": "2.9.0", "item": "Hooks"}
            | {"result": "partial"}
        ],
        rubrics=["speed"],
        rubrics_dir=tmp_path / "rubrics",
    )
    items = [(r["Rubric"], r["Rubric version"], r["Item"]) for r in table(out)]
    assert items == [
        ("Speed", "3", "Phase score"),
        ("Speed", "3", "Quick"),
        ("Speed", "3", "Hooks"),
    ]


# Criterion 9: the value at the last audit.


def test_the_last_audit_value_comes_from_the_same_row(tmp_path: Path) -> None:
    """Same rubric, rubric version, craft version, and item; Linear escapes too."""
    first = scores(tmp_path, [ticket(1, judged("2.9.0", checks("pass")))])
    linear = first.replace("1.00", "1\\.00")
    second = scores(
        tmp_path,
        [ticket(2, judged("2.9.0", checks("fail")))],
        previous=f"# Audit\n\n## Summary\n\nText.\n\n{linear}\n## Review\n",
    )
    assert row(second, "2.9.0", "Read in context")["At last audit"] == "1.00"
    assert row(second, "2.9.0", "Read in context")["Value"] == "0.00"
    assert row(second, "2.9.0", ROUNDS)["At last audit"] == "1"


def test_another_rubric_version_gives_dashes(tmp_path: Path) -> None:
    """Scores are compared only within one rubric version."""
    first = scores(tmp_path, [ticket(1, judged("2.9.0"))])
    older = first.replace("| Review | 1 |", "| Review | 0 |")
    second = scores(tmp_path, [ticket(2, judged("2.9.0"))], previous=older)
    assert {r["At last audit"] for r in table(second)} == {"—"}


def test_a_new_craft_version_gives_dashes(tmp_path: Path) -> None:
    """No row for 2.9.1 in the previous report."""
    first = scores(tmp_path, [ticket(1, judged("2.9.0"))])
    second = scores(tmp_path, [ticket(2, judged("2.9.1"))], previous=first)
    assert {r["At last audit"] for r in table(second)} == {"—"}


CRAFT_85 = """# Audit: 2026-11-23

## Summary

Rubric version 1.

## Scores

| Group | Project | Craft version | Rubric version | PRs | Major per PR | Design |
| --- | --- | --- | --- | --- | --- | --- |
| Craft | Craft | 2.9.0 | 1 | 2 | 0.50 | 1/0 |

## PRs

Window: 2026-11-16T10:00:00Z to 2026-11-23T10:00:00Z
"""


def test_a_craft_85_report_gives_dashes(tmp_path: Path) -> None:
    """Review focus 2: the old table has no Rubric or Item column."""
    out = scores(tmp_path, [ticket(1, judged("2.9.0"))], previous=CRAFT_85)
    assert {r["At last audit"] for r in table(out)} == {"—"}


# Errors in the audit file.


@pytest.mark.parametrize(
    ("tickets", "per_version", "error"),
    [
        ([ticket(1, judged("2.9.0", {"Speed": "pass"}))], [], "not a per-ticket"),
        ([ticket(1, judged("2.9.0", checks(read="maybe")))], [], "result"),
        (
            [ticket(1, judged("2.9.0") | {"measures": {"X": {}}})],
            [],
            "not a Measure",
        ),
        (
            [ticket(1, judged("2.9.0"))],
            [{"rubric": "review", "craft_version": "2.9.0", "item": "Read in context"}],
            "not a check per craft version",
        ),
        (
            [{"project": "D", "ticket": "CRAFT-1", "pr": 1, "rubrics": {"x": "y"}}],
            [],
            "not a rubric of this run",
        ),
    ],
)
def test_a_wrong_audit_file_fails(
    tmp_path: Path, tickets: list[Json], per_version: list[Json], error: str
) -> None:
    """The script names the problem and prints no table."""
    for entry in per_version:
        entry.setdefault("result", "pass")
    result = run(tmp_path, tickets, per_version=per_version)
    assert result.returncode == 2  # noqa: PLR2004 - the error code.
    assert error in result.stderr
    assert result.stdout == ""
