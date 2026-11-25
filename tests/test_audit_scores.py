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
    escapes: Json | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run `scores.py` on an audit file and an optional previous report."""
    audit = tmp_path / "audit.json"
    content: Json = {
        "rubrics": rubrics or ["review"],
        "tickets": tickets,
        "per_version": per_version or [],
    }
    if escapes is not None:
        content["escapes"] = escapes
    audit.write_text(json.dumps(content), encoding="utf-8")
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
        *(("all", item) for item in items),
    ]
    assert {r["Rubric version"] for r in table(out)} == {"2"}


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


def test_a_custom_rubric_gets_its_rows(tmp_path: Path) -> None:
    """A custom rubric's checks, per ticket and per craft version."""
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
    items = [
        (r["Rubric"], r["Rubric version"], r["Craft version"], r["Item"])
        for r in table(out)
    ]
    assert items == [
        ("Speed", "3", "2.9.0", "Phase score"),
        ("Speed", "3", "2.9.0", "Quick"),
        ("Speed", "3", "2.9.0", "Hooks"),
        ("Speed", "3", "all", "Phase score"),
        ("Speed", "3", "all", "Quick"),
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
    older = first.replace("| Review | 2 |", "| Review | 1 |")
    second = scores(tmp_path, [ticket(2, judged("2.9.0"))], previous=older)
    assert {r["At last audit"] for r in table(second)} == {"—"}


def test_a_new_craft_version_gives_dashes(tmp_path: Path) -> None:
    """No row for 2.9.1 in the previous report."""
    first = scores(tmp_path, [ticket(1, judged("2.9.0"))])
    second = scores(tmp_path, [ticket(2, judged("2.9.1"))], previous=first)
    per_version = [r for r in table(second) if r["Craft version"] != "all"]
    assert {r["At last audit"] for r in per_version} == {"—"}


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


# CRAFT-91 criterion 9: the Review and the Build rubric in one audit file.


def build_results(  # noqa: PLR0913 - one argument per result in the fixture.
    version: str,
    *,
    first: str = "pass",
    behavior: str = "pass",
    bent: str = "pass",
    evidence: str = "fail",
    environment: str = "partial",
    work: float | None = 30,
) -> Json:
    """Return one ticket's results for the Build rubric."""
    return {
        "craft_version": version,
        "checks": {
            "Tests first": first,
            "Tests check behavior": behavior,
            "Tests not bent": bent,
            "App evidence": evidence,
            "Environment failures": environment,
        },
        "measures": {
            "Attempts": {"Failed attempts": 1, "CI reds": 2, "Work minutes": work},
            "Feedback speed": {"Verify minutes": 3, "CI minutes": None},
        },
    }


def test_both_rubrics_print_their_rows_from_one_audit_file(tmp_path: Path) -> None:
    """A Build Phase score from its per-ticket checks only, and its Process logic."""
    both: Json = {
        "project": "Demo",
        "ticket": "CRAFT-1",
        "pr": 1,
        "rubrics": {"review": judged("2.9.2"), "build": build_results("2.9.2")},
    }
    no_build: Json = {
        "project": "Other",
        "ticket": "CRAFT-2",
        "pr": 2,
        "rubrics": {
            "review": judged("2.9.2"),
            "build": build_results(
                "2.9.2",
                first="no data",
                behavior="fail",
                bent="no data",
                evidence="no data",
                environment="no data",
                work=None,
            ),
        },
    }
    out = scores(
        tmp_path,
        [both, no_build],
        rubrics=["review", "build"],
        per_version=[
            {"rubric": rubric, "craft_version": "2.9.2", "item": "Process logic"}
            | {"result": result}
            for rubric, result in (("review", "pass"), ("build", "fail"))
        ],
    )
    assert {r["Rubric"] for r in table(out)} == {"Review", "Build"}
    phase = row(out, "2.9.2", "Phase score", "Build")
    assert (phase["Judged"], phase["Value"], phase["Pass/partial/fail"]) == (
        "6",
        "0.50",
        "3/1/2",
    )
    assert row(out, "2.9.2", "Process logic", "Build")["Value"] == "fail"
    assert row(out, "2.9.2", "Process logic", "Review")["Value"] == "pass"
    work = row(out, "2.9.2", "Attempts: Work minutes", "Build")
    assert (work["Judged"], work["Value"]) == ("1", "30")
    assert row(out, "2.9.2", "Attempts: CI reds", "Build")["Judged"] == "2"
    assert row(out, "2.9.2", "Feedback speed: CI minutes", "Build")["Value"] == (
        "no data"
    )


# CRAFT-92 criterion 7: the escape rows.

BLIND_SPOTS = "Blind spots"
NO_RUBRIC = "No rubric"
PHASES = ("plan", "spec", "build", "review")


def searched(
    number: int,
    version: str = "2.9.2",
    *,
    spec: bool = True,
    **versions: str,
) -> Json:
    """Return one searched ticket, at one craft version in every phase."""
    return {
        "ticket": f"CRAFT-{number}",
        "pr": number,
        "spec": spec,
        "versions": {phase: versions.get(phase, version) for phase in PHASES},
    }


def trace(number: int, phase: str = "review", answer: str = "escape") -> Json:
    """Return one trace of a fix PR candidate."""
    found: Json = {
        "ticket": f"CRAFT-{number}",
        "source": f"vanoostrum/demo#{number + 100}",
        "answer": answer,
    }
    if answer == "escape":
        found["phase"] = phase
    else:
        found["reason"] = "planned change"
    return found


def escapes(tickets: list[Json], traces: list[Json]) -> Json:
    """Return the `escapes` key of `audit.json`."""
    return {"searched": tickets, "traces": traces}


def escape_rows(out: str) -> list[tuple[str, str, str, str, str, str, str]]:
    """Return the escape rows: rubric, rubric version, craft version, item, cells."""
    return [
        (
            r["Rubric"],
            r["Rubric version"],
            r["Craft version"],
            r["Item"],
            r["Judged"],
            r["Value"],
            r["Pass/partial/fail"],
        )
        for r in table(out)
        if r["Item"] == BLIND_SPOTS or r["Rubric"] == NO_RUBRIC
    ]


def test_an_escape_row_is_a_rate_per_searched_ticket(tmp_path: Path) -> None:
    """One escape in 4 searched tickets is 0.25, with no pass/partial/fail."""
    out = scores(
        tmp_path,
        [],
        escapes=escapes([searched(n) for n in (1, 2, 3, 4)], [trace(2)]),
    )
    blind = row(out, "2.9.2", BLIND_SPOTS)
    assert (blind["Rubric version"], blind["Judged"], blind["Value"]) == (
        "2",
        "4",
        "0.25",
    )
    assert blind["Pass/partial/fail"] == "—"


def test_each_phase_with_no_escape_item_gets_a_no_rubric_row(
    tmp_path: Path,
) -> None:
    """Q3: plan, spec, and build; the review phase has Blind spots."""
    out = scores(tmp_path, [], escapes=escapes([searched(1), searched(2)], []))
    assert escape_rows(out) == [
        ("Review", "2", "2.9.2", BLIND_SPOTS, "2", "0.00", "—"),
        ("Review", "2", "all", BLIND_SPOTS, "2", "0.00", "—"),
        (NO_RUBRIC, "—", "2.9.2", "Escapes: plan", "2", "0.00", "—"),
        (NO_RUBRIC, "—", "all", "Escapes: plan", "2", "0.00", "—"),
        (NO_RUBRIC, "—", "2.9.2", "Escapes: spec", "2", "0.00", "—"),
        (NO_RUBRIC, "—", "all", "Escapes: spec", "2", "0.00", "—"),
        (NO_RUBRIC, "—", "2.9.2", "Escapes: build", "2", "0.00", "—"),
        (NO_RUBRIC, "—", "all", "Escapes: build", "2", "0.00", "—"),
    ]


def test_a_plan_escape_counts_in_the_plan_row(tmp_path: Path) -> None:
    """Review focus 5: a plan ticket's gate feedback, not in Blind spots."""
    plan = searched(1, spec=False)
    out = scores(
        tmp_path,
        [],
        escapes=escapes(
            [plan, searched(2)],
            [
                {
                    "ticket": "CRAFT-1",
                    "source": "plan gate: split it",
                    "answer": "escape",
                }
                | {"phase": "plan"}
            ],
        ),
    )
    plan_row = row(out, "2.9.2", "Escapes: plan", NO_RUBRIC)
    assert (plan_row["Judged"], plan_row["Value"]) == ("2", "0.50")
    blind = row(out, "2.9.2", BLIND_SPOTS)
    assert (blind["Judged"], blind["Value"]) == ("1", "0.00")


@pytest.mark.parametrize("answer", ["not an escape", "not judged"])
def test_only_escape_answers_count(tmp_path: Path, answer: str) -> None:
    """Review focus 1: planned change, owner choice, and not judged add nothing."""
    out = scores(
        tmp_path,
        [],
        escapes=escapes([searched(1)], [trace(1, answer=answer)]),
    )
    assert {r[5] for r in escape_rows(out)} == {"0.00"}


def test_a_ticket_with_no_source_lowers_the_rate(tmp_path: Path) -> None:
    """Review focus 4: no judge, 0 escapes, and still in Judged."""
    out = scores(
        tmp_path,
        [],
        escapes=escapes([searched(1), searched(2)], [trace(1, "build")]),
    )
    build = row(out, "2.9.2", "Escapes: build", NO_RUBRIC)
    assert (build["Judged"], build["Value"]) == ("2", "0.50")


def test_a_review_escape_of_a_ticket_with_no_spec_is_in_no_rate(
    tmp_path: Path,
) -> None:
    """Blind spots judges only tickets with a `## Spec`, as its rubric applies."""
    out = scores(
        tmp_path,
        [],
        escapes=escapes(
            [searched(1, spec=False), searched(2), searched(3)], [trace(1)]
        ),
    )
    blind = row(out, "2.9.2", BLIND_SPOTS)
    assert (blind["Judged"], blind["Value"]) == ("2", "0.00")


def test_a_review_row_with_no_ticket_with_a_spec_has_no_data(
    tmp_path: Path,
) -> None:
    """Judged 0 is no data, as for a check."""
    out = scores(tmp_path, [], escapes=escapes([searched(1, spec=False)], [trace(1)]))
    blind = row(out, "2.9.2", BLIND_SPOTS)
    assert (blind["Judged"], blind["Value"]) == ("0", "no data")


def test_an_escape_counts_at_the_version_of_its_phase(tmp_path: Path) -> None:
    """Criterion 6: one row per phase and craft version."""
    out = scores(
        tmp_path,
        [],
        escapes=escapes(
            [searched(1, "2.9.1", review="2.9.2"), searched(2, "2.9.2")],
            [trace(1, "review"), trace(2, "build")],
        ),
    )
    assert row(out, "2.9.2", BLIND_SPOTS)["Value"] == "0.50"
    assert row(out, "2.9.1", "Escapes: build", NO_RUBRIC)["Value"] == "0.00"
    assert row(out, "2.9.2", "Escapes: build", NO_RUBRIC)["Value"] == "1.00"
    assert [
        r for r in escape_rows(out) if r[3] == BLIND_SPOTS and r[2] == "2.9.1"
    ] == []


def test_blind_spots_follows_the_review_rows_of_its_version(tmp_path: Path) -> None:
    """In rubric order, after Process logic; not in the Phase score."""
    out = scores(
        tmp_path,
        [ticket(1, judged("2.9.2", checks("pass", "pass", "pass")))],
        per_version=[
            {"rubric": "review", "craft_version": "2.9.2", "item": "Process logic"}
            | {"result": "pass"}
        ],
        escapes=escapes([searched(1)], [trace(1)]),
    )
    items = [
        r["Item"]
        for r in table(out)
        if (r["Rubric"], r["Craft version"]) == ("Review", "2.9.2")
    ]
    assert items[-2:] == ["Process logic", BLIND_SPOTS]
    assert row(out, "2.9.2", "Phase score")["Value"] == "1.00"


def test_a_rubric_argument_prints_only_its_escape_row(tmp_path: Path) -> None:
    """Criterion 8: with rubric=build, no Blind spots row; No rubric rows stay."""
    out = scores(
        tmp_path,
        [],
        rubrics=["build"],
        escapes=escapes([searched(1)], [trace(1)]),
    )
    assert [r[3] for r in escape_rows(out) if r[2] != "all"] == [
        "Escapes: plan",
        "Escapes: spec",
        "Escapes: build",
    ]


def test_an_escape_row_has_its_trend(tmp_path: Path) -> None:
    """At last audit from the previous report's same row."""
    audit = escapes([searched(1), searched(2)], [trace(1, "spec")])
    first = scores(tmp_path, [], escapes=audit)
    second = scores(
        tmp_path,
        [],
        escapes=escapes([searched(3)], []),
        previous=first.replace("0.50", "0\\.50"),
    )
    spec = row(second, "2.9.2", "Escapes: spec", NO_RUBRIC)
    assert (spec["Value"], spec["At last audit"]) == ("0.00", "0.50")
    assert row(second, "2.9.2", BLIND_SPOTS)["At last audit"] == "0.00"


@pytest.mark.parametrize(
    ("bad", "error"),
    [
        (escapes([searched(1)], [trace(1, "deploy")]), "phase"),
        (escapes([searched(1)], [trace(2)]), "not a searched ticket"),
        (escapes([searched(1)], [trace(1, answer="maybe")]), "answer"),
        (
            escapes([{"ticket": "CRAFT-1", "pr": 1, "spec": True, "versions": {}}], []),
            "versions",
        ),
        (escapes([searched(1), searched(1)], []), "searched twice"),
    ],
)
def test_a_wrong_escapes_key_fails(tmp_path: Path, bad: Json, error: str) -> None:
    """The script names the problem and prints no table."""
    result = run(tmp_path, [], escapes=bad)
    assert result.returncode == 2  # noqa: PLR2004 - the error code.
    assert error in result.stderr
    assert result.stdout == ""


# CRAFT-93 criterion 1: the audit-wide rows.


def test_audit_wide_rows_follow_the_rows_per_craft_version(tmp_path: Path) -> None:
    """One `all` row per item, after every craft version, with no Process logic."""
    out = scores(
        tmp_path,
        [ticket(1, judged("2.9.1")), ticket(2, judged("2.9.2"))],
        per_version=[
            {"rubric": "review", "craft_version": v, "item": "Process logic"}
            | {"result": "fail"}
            for v in ("2.9.1", "2.9.2")
        ],
        escapes=escapes([searched(1, "2.9.1"), searched(2)], []),
    )
    review = [
        (r["Craft version"], r["Item"]) for r in table(out) if r["Rubric"] == "Review"
    ]
    assert review[-7:] == [
        ("all", "Phase score"),
        ("all", "Read in context"),
        ("all", "Criteria evidence"),
        ("all", "Design and maintainability"),
        ("all", ROUNDS),
        ("all", BLOCKING),
        ("all", BLIND_SPOTS),
    ]
    assert ("all", "Process logic") not in review
    assert {r["Craft version"] for r in table(out)[: len(review) - 7]} == {
        "2.9.1",
        "2.9.2",
    }


def test_an_audit_wide_check_counts_every_ticket(tmp_path: Path) -> None:
    """The share and the counts over all craft versions."""
    out = scores(
        tmp_path,
        [
            ticket(1, judged("2.9.1", checks(design="pass"))),
            ticket(2, judged("2.9.1", checks(design="partial"))),
            ticket(3, judged("2.9.2", checks(design="fail"))),
            ticket(4, judged("2.9.2", checks(design="no data"))),
        ],
    )
    design = row(out, "all", "Design and maintainability")
    assert (design["Judged"], design["Value"], design["Pass/partial/fail"]) == (
        "3",
        "0.33",
        "1/1/1",
    )
    phase = row(out, "all", "Phase score")
    assert (phase["Judged"], phase["Pass/partial/fail"]) == ("11", "9/1/1")


def test_an_audit_wide_median_is_over_the_tickets(tmp_path: Path) -> None:
    """Medians 1 (2.9.1) and 6 (2.9.2), but 5 over the five tickets."""
    out = scores(
        tmp_path,
        [
            ticket(1, judged("2.9.1", rounds=1)),
            ticket(2, judged("2.9.1", rounds=1)),
            ticket(3, judged("2.9.1", rounds=None)),
            ticket(4, judged("2.9.2", rounds=5)),
            ticket(5, judged("2.9.2", rounds=10)),
            ticket(6, judged("2.9.2", rounds=6)),
        ],
    )
    assert row(out, "2.9.1", ROUNDS)["Value"] == "1"
    assert row(out, "2.9.2", ROUNDS)["Value"] == "6"
    audit_wide = row(out, "all", ROUNDS)
    assert (audit_wide["Judged"], audit_wide["Value"]) == ("5", "5")


def test_an_audit_wide_escape_row_sums_its_rows(tmp_path: Path) -> None:
    """Judged is the sum of the Judged per craft version: spec tickets for review."""
    out = scores(
        tmp_path,
        [],
        escapes=escapes(
            [
                searched(1, "2.9.1"),
                searched(2, "2.9.1", spec=False),
                searched(3, "2.9.2"),
                searched(4, "2.9.2"),
            ],
            [trace(1), trace(2), trace(3, "build"), trace(4, "build")],
        ),
    )
    blind = row(out, "all", BLIND_SPOTS)
    assert (blind["Judged"], blind["Value"]) == ("3", "0.33")
    build = row(out, "all", "Escapes: build", NO_RUBRIC)
    assert (build["Judged"], build["Value"]) == ("4", "0.50")


def test_an_audit_wide_escape_row_with_no_judged_ticket_has_no_data(
    tmp_path: Path,
) -> None:
    """Summed Judged 0 is no data, as in its rows per craft version."""
    out = scores(tmp_path, [], escapes=escapes([searched(1, spec=False)], []))
    blind = row(out, "all", BLIND_SPOTS)
    assert (blind["Judged"], blind["Value"]) == ("0", "no data")


def test_a_check_per_craft_version_has_no_audit_wide_row(tmp_path: Path) -> None:
    """Process logic is judged once per craft version, so it stays per version."""
    out = scores(
        tmp_path,
        [ticket(1, judged("2.9.2"))],
        per_version=[
            {"rubric": "review", "craft_version": "2.9.2", "item": "Process logic"}
            | {"result": "fail"}
        ],
    )
    assert [r for r in table(out) if r["Item"] == "Process logic"] == [
        row(out, "2.9.2", "Process logic")
    ]


def test_an_audit_wide_row_has_its_trend(tmp_path: Path) -> None:
    """At last audit reads the previous report's row with `all`."""
    first = scores(tmp_path, [ticket(1, judged("2.9.1", rounds=3))])
    second = scores(
        tmp_path,
        [ticket(2, judged("2.9.2", rounds=4))],
        previous=first,
    )
    audit_wide = row(second, "all", ROUNDS)
    assert (audit_wide["Value"], audit_wide["At last audit"]) == ("4", "3")
    assert row(second, "2.9.2", ROUNDS)["At last audit"] == "—"
