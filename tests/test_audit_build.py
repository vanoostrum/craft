# Copyright (C) 2026 Theo van Oostrum
"""`build.py` scores the Attempts and Feedback speed measures of the Build rubric.

The script runs as a command, as the audit runs it. Every fixture is made up:
the roles have the shape of real ones but are not copied from transcripts
(`docs/adr/0009`).
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

type Json = dict[str, object]

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "craft" / "skills" / "audit" / "scripts" / "build.py"
REQUIRED = ["checks", "evals"]


def at(minute: int) -> str:
    """Return a time on a made-up day, `minute` minutes after 10:00."""
    return f"2026-11-20T{10 + minute // 60:02d}:{minute % 60:02d}:00Z"


def subagent(role: str, start: int, end: int) -> Json:
    """Return a subagent of a segment that ran from `start` to `end` minutes."""
    return {
        "agent_id": "a1",
        "role": role,
        "started_at": at(start),
        "ended_at": at(end),
    }


def segment(work_seconds: float, *subagents: Json, step: str = "build") -> Json:
    """Return a segment, as `metadata.json` holds it."""
    return {
        "step": step,
        "ticket": "CRAFT-1",
        "started_at": at(0),
        "ended_at": at(90),
        "work_seconds": work_seconds,
        "subagents": list(subagents),
    }


def check_run(
    name: str, conclusion: str | None, start: int = 0, end: int | None = 10
) -> Json:
    """Return a check run, as the GitHub check-runs API returns it."""
    return {
        "name": name,
        "status": "completed" if conclusion is not None else "in_progress",
        "conclusion": conclusion,
        "started_at": at(start),
        "completed_at": None if end is None else at(end),
    }


def comment(body: str) -> Json:
    """Return a Linear comment."""
    return {"body": body, "createdAt": at(0)}


def build(
    tmp_path: Path,
    command: str,
    *,
    comments: list[Json] | None = None,
    check_runs: list[Json] | None = None,
    segments: list[Json] | None = None,
) -> dict[str, Any]:
    """Run `build.py <command>` on an input file and return its values."""
    path = tmp_path / "input.json"
    path.write_text(
        json.dumps(
            {
                "required_checks": REQUIRED,
                "comments": comments or [],
                "check_runs": check_runs or [],
                "segments": segments or [],
            }
        ),
        encoding="utf-8",
    )
    done = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), command, str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(done.stdout)["values"]


# Criterion 6: Attempts.


def test_failed_attempts_count_the_build_retry_comments(tmp_path: Path) -> None:
    """Only craft's `🤖 build: retry` comments; the owner's words do not count."""
    comments = [
        comment("🤖 build: retry 1 of 4 — CI failed on lint"),
        comment("🤖 build: retry 2 of 4 — app driver failed"),
        comment("🤖 build: success — PR https://example.com/pr/1"),
        comment("🤖 review: FAIL — 1 blocking"),
        comment("Please build: retry it"),
    ]
    values = build(tmp_path, "attempts", comments=comments)
    assert values["Failed attempts"] == 2  # noqa: PLR2004


def test_ci_reds_count_failed_runs_of_required_checks(tmp_path: Path) -> None:
    """Failure or timed out, on any commit of the PR; other checks do not count."""
    runs = [
        check_run("checks", "failure"),
        check_run("checks", "success"),
        check_run("evals", "timed_out"),
        check_run("evals", "cancelled"),
        check_run("lint-extra", "failure"),
        check_run("checks", None, end=None),
    ]
    values = build(tmp_path, "attempts", check_runs=runs)
    assert values["CI reds"] == 2  # noqa: PLR2004


def test_work_minutes_sum_every_build_segment(tmp_path: Path) -> None:
    """Review focus 2: a retry after a review FAIL is a build segment too."""
    segments = [
        segment(600),
        segment(900, step="review"),
        segment(300),
    ]
    values = build(tmp_path, "attempts", segments=segments)
    assert values["Work minutes"] == 15  # noqa: PLR2004


def test_no_build_segment_gives_no_work_minutes(tmp_path: Path) -> None:
    """Review focus 1: a LibRag ticket; the other two values are still scored."""
    values = build(
        tmp_path,
        "attempts",
        comments=[comment("🤖 build: retry 1 of 4 — CI failed")],
        check_runs=[check_run("checks", "failure")],
    )
    assert values == {"Failed attempts": 1, "CI reds": 1, "Work minutes": None}


# Criterion 7: Feedback speed.


def test_verify_minutes_is_the_median_of_the_verify_runs(tmp_path: Path) -> None:
    """Over every build segment's verify subagents."""
    segments = [
        segment(60, subagent("Run project-verify", 0, 2)),
        segment(
            60,
            subagent("Run project-verify after the fix", 10, 14),
            subagent("Run Verify again", 20, 30),
        ),
    ]
    values = build(tmp_path, "speed", segments=segments)
    assert values["Verify minutes"] == 4  # noqa: PLR2004


@pytest.mark.parametrize(
    "role",
    [
        "Run verify smoke suite as app driver",
        "App driver: verify the new route",
        "Drive the app to verify the page",
        "Run the verify eval suite",
        "Poll CI for the PR",
    ],
)
def test_other_subagents_are_not_verify_runs(tmp_path: Path, role: str) -> None:
    """Review focus 5: an app driver with "verify" in its role is not counted."""
    segments = [
        segment(60, subagent("Run project-verify", 0, 3), subagent(role, 0, 50))
    ]
    values = build(tmp_path, "speed", segments=segments)
    assert values["Verify minutes"] == 3  # noqa: PLR2004


def test_review_segments_do_not_count_for_speed(tmp_path: Path) -> None:
    """Only build segments."""
    segments = [segment(60, subagent("Run project-verify", 0, 3), step="review")]
    values = build(tmp_path, "speed", segments=segments)
    assert values["Verify minutes"] is None


def test_ci_minutes_is_the_median_of_completed_required_runs(tmp_path: Path) -> None:
    """From `started_at` to `completed_at`; runs that did not complete are out."""
    runs = [
        check_run("checks", "success", 0, 4),
        check_run("evals", "failure", 0, 8),
        check_run("checks", "success", 30, 36),
        check_run("lint-extra", "success", 0, 60),
        check_run("evals", None, 40, None),
    ]
    values = build(tmp_path, "speed", check_runs=runs)
    assert values["CI minutes"] == 6  # noqa: PLR2004


def test_minutes_are_rounded_to_two_decimals(tmp_path: Path) -> None:
    """A run of 70 seconds is 1.17 minutes, not 1.1666…."""
    run = check_run("checks", "success")
    run["completed_at"] = "2026-11-20T10:01:10Z"
    values = build(tmp_path, "speed", check_runs=[run])
    assert values["CI minutes"] == 1.17  # noqa: PLR2004


def test_speed_with_no_runs_is_no_data(tmp_path: Path) -> None:
    """Each value with no run is no data."""
    values = build(tmp_path, "speed", segments=[segment(60)])
    assert values == {"Verify minutes": None, "CI minutes": None}


def test_a_wrong_command_prints_the_usage(tmp_path: Path) -> None:
    """Exit 2 with the usage."""
    done = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), "rounds", str(tmp_path / "input.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == 2  # noqa: PLR2004
    assert "Usage: build.py" in done.stderr
