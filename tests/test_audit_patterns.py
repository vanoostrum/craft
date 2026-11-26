# Copyright (C) 2026 Theo van Oostrum
"""`patterns.py` finds the patterns of an audit and how earlier proposals moved.

The script runs as a command, as the audit runs it. Every fixture is synthetic:
the rubrics' rows, tickets, and values are made up (`docs/adr/0009`).
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "craft" / "skills" / "audit" / "scripts" / "patterns.py"
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
DESIGN = "Design and maintainability"
LOGIC = "Process logic"

type Cells = tuple[str, str, str, str, str, str, str, str]


def scores(*rows: Cells, escaped: bool = False) -> str:
    """Return a `## Scores` section with these rows, as `scores.py` prints it."""
    lines = [
        "## Scores",
        "",
        "| " + " | ".join(HEADER) + " |",
        "|" + "|".join(" --- " for _ in HEADER) + "|",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    text = "\n".join(lines) + "\n"
    return text.replace(".", "\\.") if escaped else text


def check(  # noqa: PLR0913, PLR0917 - each argument is one cell.
    counts: str,
    judged: str = "5",
    value: str = "0.40",
    version: str = "all",
    item: str = DESIGN,
    rubric: tuple[str, str] = ("Review", "2"),
) -> Cells:
    """Return a per-ticket check row."""
    return (*rubric, version, item, judged, value, counts, "—")


def logic(result: str, version: str = "2.9.1", rubric: str = "Review") -> Cells:
    """Return a Process logic row."""
    return (rubric, "2", version, LOGIC, "—", result, "—", "—")


def measure(
    value: str,
    last: str = "—",
    judged: str = "3",
    item: str = ROUNDS,
    rubric: tuple[str, str] = ("Review", "2"),
) -> Cells:
    """Return an audit-wide measure or escape row."""
    return (*rubric, "all", item, judged, value, "—", last)


def find(tmp_path: Path, now: str, previous: str | None = None) -> list[list[str]]:
    """Run `patterns.py find`, check that it passed, and return its lines as cells."""
    current = tmp_path / "scores.md"
    current.write_text(now, encoding="utf-8")
    args = [sys.executable, str(SCRIPT), "find", str(current)]
    if previous is not None:
        old = tmp_path / "previous.md"
        old.write_text(f"# Audit: 2026-11-18\n\n## Summary\n\nText.\n\n{previous}")
        args.append(str(old))
    result = subprocess.run(args, capture_output=True, text=True, check=False)  # noqa: S603
    assert result.returncode == 0, result.stderr
    return [line.split(" | ") for line in result.stdout.splitlines()]


# Criterion 2: check and Process logic patterns.


def test_three_failing_or_partial_tickets_are_a_check_pattern(tmp_path: Path) -> None:
    """Partials count, in the audit-wide row; the line has its format."""
    lines = find(tmp_path, scores(check("2/1/2")))
    assert lines == [
        [
            "check",
            "Review",
            "2",
            "all",
            DESIGN,
            "0.40",
            "3 of 5 tickets fail or partial",
        ]
    ]


@pytest.mark.parametrize("counts", ["3/0/2", "4/1/0", "5/0/0"])
def test_two_failing_or_partial_tickets_are_no_pattern(
    tmp_path: Path, counts: str
) -> None:
    """The edge: 2 is not enough."""
    assert find(tmp_path, scores(check(counts))) == []


def test_only_the_audit_wide_check_row_counts(tmp_path: Path) -> None:
    """A row per craft version gives no pattern, and neither does the Phase score."""
    rows = (
        check("0/0/3", "3", "0.00", "2.9.1"),
        check("0/0/9", "9", "0.00", "all", "Phase score"),
        check("3/0/0", "3", "1.00"),
    )
    assert find(tmp_path, scores(*rows)) == []


@pytest.mark.parametrize("result", ["fail", "partial"])
def test_a_process_logic_fail_or_partial_is_a_pattern(
    tmp_path: Path, result: str
) -> None:
    """On its own, at any craft version."""
    lines = find(tmp_path, scores(logic(result, "2.8.0"), logic("pass", "2.9.1")))
    assert lines == [
        [
            "process logic",
            "Review",
            "2",
            "2.8.0",
            LOGIC,
            result,
            f"{result} at craft version 2.8.0",
        ]
    ]


def test_a_process_logic_pass_or_no_data_is_no_pattern(tmp_path: Path) -> None:
    """Only fail and partial."""
    assert find(tmp_path, scores(logic("pass"), logic("no data", "2.9.2"))) == []


def test_a_copied_process_logic_fail_is_a_pattern_again(tmp_path: Path) -> None:
    """Review focus 3: the row is there again, so `find` prints it again."""
    first = find(tmp_path, scores(logic("fail", "2.8.0")))
    again = find(
        tmp_path, scores(logic("fail", "2.8.0")), scores(logic("fail", "2.8.0"))
    )
    assert first == again
    assert len(again) == 1


def test_one_process_logic_line_per_rubric_and_item(tmp_path: Path) -> None:
    """CRAFT-99 criteria 1 and 2, Review focus 1: the newest failing version."""
    rows = (
        logic("fail", "2.8.0"),
        logic("pass", "2.9.0"),
        logic("partial", "2.9.1"),
    )
    assert find(tmp_path, scores(*rows)) == [
        [
            "process logic",
            "Review",
            "2",
            "2.9.1",
            LOGIC,
            "partial",
            "partial at craft version 2.9.1; fail at craft version 2.8.0",
        ]
    ]


def test_the_newest_failing_version_is_by_number(tmp_path: Path) -> None:
    """CRAFT-99 criterion 2: 2.10.0 is newer than 2.9.2, in any table order."""
    rows = (logic("fail", "2.10.0"), logic("partial", "2.9.2"))
    lines = find(tmp_path, scores(*rows))
    assert [line[3] for line in lines] == ["2.10.0"]
    assert lines[0][6] == (
        "fail at craft version 2.10.0; partial at craft version 2.9.2"
    )


def test_one_failing_version_prints_the_line_of_today(tmp_path: Path) -> None:
    """CRAFT-99 criterion 3: the same line as with one row."""
    one = find(tmp_path, scores(logic("fail", "2.8.0")))
    with_passes = find(
        tmp_path,
        scores(logic("pass", "2.7.0"), logic("fail", "2.8.0"), logic("pass", "2.9.0")),
    )
    assert one == with_passes
    assert one[0][6] == "fail at craft version 2.8.0"


def test_the_same_item_in_two_rubrics_gives_two_lines(tmp_path: Path) -> None:
    """CRAFT-99 criterion 4, Review focus 2: one line per rubric."""
    rows = (
        logic("fail", "2.8.0"),
        logic("fail", "2.8.0", "Build"),
        logic("partial", "2.9.0"),
        logic("fail", "2.9.0", "Build"),
    )
    lines = find(tmp_path, scores(*rows))
    assert [(line[1], line[3], line[5]) for line in lines] == [
        ("Review", "2.9.0", "partial"),
        ("Build", "2.9.0", "fail"),
    ]


def test_another_rubric_version_gives_its_own_line(tmp_path: Path) -> None:
    """CRAFT-99 criterion 1: lines merge per rubric version too."""
    old = ("Review", "1", "2.8.0", LOGIC, "—", "fail", "—", "—")
    lines = find(tmp_path, scores(old, logic("fail", "2.9.0")))
    assert [(line[2], line[3]) for line in lines] == [("1", "2.8.0"), ("2", "2.9.0")]


# Criterion 3: trend patterns.


def test_a_measure_worse_two_audits_in_a_row_is_a_trend(tmp_path: Path) -> None:
    """2, then 3, then 4, with Judged 3 in both reports."""
    lines = find(tmp_path, scores(measure("4", "3")), scores(measure("3", "2")))
    assert lines == [
        [
            "trend",
            "Review",
            "2",
            "all",
            ROUNDS,
            "4",
            "worse two audits in a row: 2, 3, 4",
        ]
    ]


def test_an_escape_row_worse_two_audits_in_a_row_is_a_trend(tmp_path: Path) -> None:
    """The `No rubric` rows count, and Linear's escapes are undone."""
    row = ("No rubric", "—")
    now = scores(measure("0.50", "0.25", "4", "Escapes: build", row))
    before = scores(measure("0.25", "0.10", "4", "Escapes: build", row), escaped=True)
    assert [line[0] for line in find(tmp_path, now, before)] == ["trend"]


@pytest.mark.parametrize(
    ("now", "before"),
    [
        (measure("4", "3", "2"), measure("3", "2")),
        (measure("4", "3"), measure("3", "2", "2")),
        (measure("4", "3"), measure("3", "—")),
        (measure("4", "3"), measure("3", "no data")),
        (measure("no data", "3"), measure("3", "2")),
        (measure("4", "3"), measure("3", "3")),
        (measure("3", "3"), measure("3", "2")),
        (measure("2", "3"), measure("3", "2")),
    ],
    ids=[
        "judged-2-now",
        "judged-2-before",
        "dash",
        "no-data-before",
        "no-data-now",
        "same-before",
        "same-now",
        "better-now",
    ],
)
def test_a_trend_needs_two_rises_with_judged_3_and_numbers(
    tmp_path: Path, now: Cells, before: Cells
) -> None:
    """Review focus 4 and the edges of criterion 3."""
    assert find(tmp_path, scores(now), scores(before)) == []


def test_a_check_or_phase_score_gives_no_trend(tmp_path: Path) -> None:
    """Lower is worse for a check, but checks lead only through the 3-ticket rule."""
    now = scores(
        ("Review", "2", "all", DESIGN, "5", "0.20", "1/0/4", "0.40"),
        ("Review", "2", "all", "Phase score", "15", "0.20", "3/0/12", "0.40"),
    )
    before = scores(
        ("Review", "2", "all", DESIGN, "5", "0.40", "2/0/3", "0.60"),
        ("Review", "2", "all", "Phase score", "15", "0.40", "6/0/9", "0.60"),
    )
    assert [line[0] for line in find(tmp_path, now, before)] == ["check"]


def test_a_rise_at_one_craft_version_is_no_trend(tmp_path: Path) -> None:
    """Only audit-wide rows have a trend."""
    row: Cells = ("Review", "2", "2.9.1", ROUNDS, "3", "4", "—", "3")
    before: Cells = ("Review", "2", "2.9.1", ROUNDS, "3", "3", "—", "2")
    assert find(tmp_path, scores(row), scores(before)) == []


def test_another_rubric_version_gives_no_trend(tmp_path: Path) -> None:
    """The previous row must have the same rubric version."""
    before = measure("3", "2", rubric=("Review", "1"))
    assert find(tmp_path, scores(measure("4", "3")), scores(before)) == []


def test_the_first_audit_after_this_ships_finds_no_trend(tmp_path: Path) -> None:
    """Review focus 1: no audit-wide rows before; the other patterns still come."""
    before: Cells = ("Review", "2", "2.9.1", ROUNDS, "3", "3", "—", "2")
    now = scores(logic("fail"), check("1/0/4", value="0.20"), measure("4", "3"))
    lines = find(tmp_path, now, scores(before))
    assert [line[0] for line in lines] == ["process logic", "check"]


def test_no_previous_report_finds_no_trend(tmp_path: Path) -> None:
    """Without the second argument, only checks and Process logic."""
    assert find(tmp_path, scores(measure("4", "3"))) == []


def test_a_previous_report_in_the_craft_85_format_finds_no_trend(
    tmp_path: Path,
) -> None:
    """A table with other columns is no audit-wide row."""
    old = "## Scores\n\n| PR | Score |\n| --- | --- |\n| #1 | 3 |\n"
    assert find(tmp_path, scores(measure("4", "3")), old) == []


# Criterion 4: the order, and no pattern.


def test_lines_come_in_kind_order_then_table_order(tmp_path: Path) -> None:
    """Process logic, check, trend; each in the order of `## Scores`."""
    build = ("Build", "1")
    now = scores(
        check("0/0/3", "3", "0.00", item="Read in context"),
        measure("4", "3"),
        check("0/1/2", "3", "0.00"),
        logic("partial", "2.9.2"),
        check("0/0/4", "4", "0.00", item="App evidence", rubric=build),
        logic("fail", "2.9.2", "Build"),
    )
    before = scores(measure("3", "2"))
    lines = find(tmp_path, now, before)
    assert [(line[0], line[1], line[4]) for line in lines] == [
        ("process logic", "Review", LOGIC),
        ("process logic", "Build", LOGIC),
        ("check", "Review", "Read in context"),
        ("check", "Review", DESIGN),
        ("check", "Build", "App evidence"),
        ("trend", "Review", ROUNDS),
    ]


def test_no_pattern_prints_nothing(tmp_path: Path) -> None:
    """An empty output, and exit 0."""
    assert find(tmp_path, scores(check("5/0/0", value="1.00"), logic("pass"))) == []
    assert find(tmp_path, "## Scores\n\nNo tickets judged.\n") == []


# Criterion 5: `moved`.


def proposal(  # noqa: PLR0913 - each argument is one field.
    number: int,
    value: object,
    *,
    released: str | None = "2.10.0",
    state: str = "Done",
    item: str = ROUNDS,
    rubric: tuple[str, str] = ("Review", "2"),
) -> dict[str, object]:
    """Return one earlier proposal."""
    return {
        "ticket": f"CRAFT-{number}",
        "title": f"Change step {number}",
        "state": state,
        "released": released,
        "rubric": rubric[0],
        "rubric_version": rubric[1],
        "item": item,
        "value_at_proposal": value,
    }


def moved(
    tmp_path: Path,
    proposals: list[dict[str, object]],
    now: str,
    ran: str = "Review,Build",
) -> list[dict[str, str]]:
    """Run `patterns.py moved`, check that it passed, and return its rows."""
    found = tmp_path / "proposals.json"
    found.write_text(json.dumps(proposals), encoding="utf-8")
    current = tmp_path / "scores.md"
    current.write_text(now, encoding="utf-8")
    args = [
        sys.executable,
        str(SCRIPT),
        "moved",
        "--ran",
        ran,
        str(found),
        str(current),
    ]
    result = subprocess.run(args, capture_output=True, text=True, check=False)  # noqa: S603
    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.startswith("|")]
    names = [cell.strip() for cell in lines[0].strip("|").split("|")]
    assert names == [
        "Ticket",
        "Title",
        "State",
        "Released in",
        "Measure",
        "Value at proposal",
        "Value now",
        "Moved",
    ]
    return [
        dict(zip(names, (c.strip() for c in line.strip("|").split("|")), strict=True))
        for line in lines[2:]
    ]


def test_moved_prints_one_row_per_proposal(tmp_path: Path) -> None:
    """The columns, with the measure and the value now from the audit-wide row."""
    rows = moved(tmp_path, [proposal(7, 3), proposal(8, "2")], scores(measure("2")))
    assert rows[0] == {
        "Ticket": "CRAFT-7",
        "Title": "Change step 7",
        "State": "Done",
        "Released in": "2.10.0",
        "Measure": f"Review 2: {ROUNDS}",
        "Value at proposal": "3",
        "Value now": "2",
        "Moved": "better",
    }
    assert [r["Ticket"] for r in rows] == ["CRAFT-7", "CRAFT-8"]
    assert rows[1]["Moved"] == "same"


def test_a_higher_measure_moved_worse(tmp_path: Path) -> None:
    """For a measure and an escape rate, higher is worse."""
    rows = moved(tmp_path, [proposal(7, "0.25")], scores(measure("0.50")))
    assert rows[0]["Moved"] == "worse"


def test_a_lower_check_moved_worse(tmp_path: Path) -> None:
    """For a check, lower is worse."""
    rows = moved(
        tmp_path,
        [proposal(7, "0.40", item=DESIGN), proposal(8, "0.20", item=DESIGN)],
        scores(check("1/1/1", "3", "0.33")),
    )
    assert [r["Moved"] for r in rows] == ["worse", "better"]


def test_an_unreleased_proposal_has_not_released(tmp_path: Path) -> None:
    """Open, or Done before a release; Value now is still shown."""
    rows = moved(
        tmp_path,
        [proposal(7, 3, released=None, state="Backlog"), proposal(8, 3, released=None)],
        scores(measure("9")),
    )
    assert [(r["Released in"], r["Value now"], r["Moved"]) for r in rows] == [
        ("—", "9", "not released"),
        ("—", "9", "not released"),
    ]


@pytest.mark.parametrize(
    ("before", "now", "result"),
    [
        ("fail", "partial", "better"),
        ("partial", "pass", "better"),
        ("pass", "fail", "worse"),
        ("partial", "fail", "worse"),
        ("fail", "fail", "same"),
        ("fail", "no data", "no data"),
    ],
)
def test_process_logic_moves_by_result(
    tmp_path: Path, before: str, now: str, result: str
) -> None:
    """Fail is worse than partial, and partial worse than pass; the newest version."""
    rows = moved(
        tmp_path,
        [proposal(7, before, item=LOGIC)],
        scores(logic("pass", "2.9.0"), logic(now, "2.10.0"), logic("pass", "2.9.2")),
    )
    assert (rows[0]["Value now"], rows[0]["Moved"]) == (now, result)


def test_process_logic_value_now_is_from_at_or_after_the_release(
    tmp_path: Path,
) -> None:
    """CRAFT-99 criterion 5, Review focus 3 and 5: by number, the release counts."""
    rows = moved(
        tmp_path,
        [
            proposal(7, "fail", item=LOGIC, released="2.10.0"),
            proposal(8, "fail", item=LOGIC, released="2.9.2"),
        ],
        scores(logic("fail", "2.9.2"), logic("pass", "2.10.0")),
    )
    assert [(r["Value now"], r["Moved"]) for r in rows] == [
        ("pass", "better"),
        ("pass", "better"),
    ]
    rows = moved(
        tmp_path,
        [proposal(7, "fail", item=LOGIC, released="2.9.2")],
        scores(logic("partial", "2.9.2"), logic("pass", "2.9.1")),
    )
    assert (rows[0]["Value now"], rows[0]["Moved"]) == ("partial", "better")


def test_process_logic_with_no_row_since_the_release_has_no_data(
    tmp_path: Path,
) -> None:
    """CRAFT-99 criterion 6, Review focus 3 and 4: never `same`."""
    rows = moved(
        tmp_path,
        [proposal(7, "fail", item=LOGIC, released="2.10.0")],
        scores(logic("fail", "2.9.2"), logic("fail", "2.9.10")),
    )
    assert (rows[0]["Value now"], rows[0]["Moved"]) == (
        "no data (no result since release)",
        "no data",
    )


def test_unreleased_process_logic_has_the_newest_version(tmp_path: Path) -> None:
    """CRAFT-99 criterion 7: Value now from the newest version, not released."""
    rows = moved(
        tmp_path,
        [proposal(7, "fail", item=LOGIC, released=None, state="Backlog")],
        scores(logic("partial", "2.10.0"), logic("fail", "2.9.2")),
    )
    assert (rows[0]["Value now"], rows[0]["Moved"]) == ("partial", "not released")


@pytest.mark.parametrize("released", ["2.10.0", "v2.10.0"])
def test_a_leading_v_in_released_compares_the_same(
    tmp_path: Path, released: str
) -> None:
    """CRAFT-99 criterion 9, Review focus 6: the cell shows `released` as written."""
    rows = moved(
        tmp_path,
        [
            proposal(7, "fail", item=LOGIC, released=released),
            proposal(8, "fail", item=LOGIC, released=f"{released[:-1]}1"),
        ],
        scores(logic("fail", "2.9.2"), logic("pass", "2.10.0")),
    )
    assert [(r["Released in"], r["Value now"], r["Moved"]) for r in rows] == [
        (released, "pass", "better"),
        (f"{released[:-1]}1", "no data (no result since release)", "no data"),
    ]


def test_a_rubric_that_did_not_run_has_no_data(tmp_path: Path) -> None:
    """Value now says why; Moved is no data."""
    build = proposal(7, 2, item="Attempts: CI reds", rubric=("Build", "1"))
    rows = moved(tmp_path, [build], scores(measure("2")), ran="Review")
    assert (rows[0]["Value now"], rows[0]["Moved"]) == (
        "no data (rubric not run)",
        "no data",
    )


def test_another_rubric_version_has_no_data(tmp_path: Path) -> None:
    """The rubric ran, but with another rubric version."""
    old = proposal(7, 2, rubric=("Review", "1"))
    rows = moved(tmp_path, [old], scores(measure("2")))
    assert (rows[0]["Value now"], rows[0]["Moved"]) == (
        "no data (rubric version changed)",
        "no data",
    )


def test_a_missing_row_has_no_data(tmp_path: Path) -> None:
    """Same rubric version, no row for the item."""
    rows = moved(tmp_path, [proposal(7, 2, item="Gone")], scores(measure("2")))
    assert (rows[0]["Value now"], rows[0]["Moved"]) == ("no data", "no data")


def test_a_value_with_no_data_has_no_data(tmp_path: Path) -> None:
    """Value now or Value at proposal that is not a number."""
    rows = moved(
        tmp_path,
        [proposal(7, 2), proposal(8, "no data")],
        scores(measure("no data")),
    )
    assert [r["Moved"] for r in rows] == ["no data", "no data"]


def test_no_rubric_always_counts_as_run(tmp_path: Path) -> None:
    """Plan task 3: a `No rubric` proposal with `--ran Review`."""
    item = "Escapes: build"
    row = measure("0.20", item=item, rubric=("No rubric", "—"))
    rows = moved(
        tmp_path,
        [proposal(7, "0.40", item=item, rubric=("No rubric", "—"))],
        scores(row),
        ran="Review",
    )
    assert (rows[0]["Measure"], rows[0]["Value now"], rows[0]["Moved"]) == (
        f"No rubric: {item}",
        "0.20",
        "better",
    )


def test_no_earlier_proposal_prints_no_row(tmp_path: Path) -> None:
    """The header only."""
    assert moved(tmp_path, [], scores(measure("2"))) == []


def test_a_wrong_command_fails() -> None:
    """The usage text, and exit 2."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), "guess"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2  # noqa: PLR2004 - the error code.
    assert "Usage" in result.stderr


def test_the_usage_text_says_the_rules_of_craft_99() -> None:
    """CRAFT-99 criterion 10: one line per item, results since the release, `v`."""
    result = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        check=False,
    )
    usage = " ".join(result.stderr.split())
    assert "It gives one line per rubric, rubric version, and item" in usage
    assert "only craft versions at or after `released` count, by version order" in usage
    assert "`no data (no result since release)`" in usage
    assert "It may have a leading `v`, such as `v2.10.0`" in usage


# CRAFT-99 criterion 8: `scores.py`, then `patterns.py find`.


def test_find_reads_what_scores_prints(tmp_path: Path) -> None:
    """A check pattern, and one merged Process logic pattern for two versions."""
    checks = {
        "Read in context": "pass",
        "Criteria evidence": "pass",
        DESIGN: "fail",
    }
    tickets = [
        {
            "project": "Demo",
            "ticket": f"CRAFT-{number}",
            "pr": number,
            "rubrics": {
                "review": {
                    "craft_version": version,
                    "checks": checks,
                    "measures": {
                        "Findings rounds": {
                            "Rounds until PASS": 1,
                            "Blocking per round": 0,
                        }
                    },
                }
            },
        }
        for number, version in ((1, "2.9.2"), (2, "2.10.0"), (3, "2.10.0"))
    ]
    audit = tmp_path / "audit.json"
    audit.write_text(
        json.dumps(
            {
                "rubrics": ["review"],
                "tickets": tickets,
                "per_version": [
                    {
                        "rubric": "review",
                        "craft_version": version,
                        "item": LOGIC,
                        "result": "fail",
                    }
                    for version in ("2.9.2", "2.10.0")
                ],
            }
        ),
        encoding="utf-8",
    )
    printed = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT.with_name("scores.py")), str(audit)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert printed.returncode == 0, printed.stderr
    lines = find(tmp_path, printed.stdout)
    assert lines == [
        [
            "process logic",
            "Review",
            "2",
            "2.10.0",
            LOGIC,
            "fail",
            "fail at craft version 2.10.0; fail at craft version 2.9.2",
        ],
        [
            "check",
            "Review",
            "2",
            "all",
            DESIGN,
            "0.00",
            "3 of 3 tickets fail or partial",
        ],
    ]
