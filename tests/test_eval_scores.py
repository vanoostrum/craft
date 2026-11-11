# Copyright (C) 2026 Theo van Oostrum
"""The `evals` job prints each case's score and each failed grader to its log."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "eval_scores.py"


def grader(name: str, *, passed: bool, explanation: str) -> dict[str, object]:
    """Return one grader verdict, as `claude plugin eval --json` writes it."""
    return {"name": name, "passed": passed, "explanation": explanation}


def run_script(tmp_path: Path, result: object) -> str:
    """Write `result` to a file, run the script on it, and return its output."""
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    return subprocess.run(  # noqa: S603 - runs the script under test.
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def one_run(trace_path: str | None) -> dict[str, object]:
    """Return an eval result with one passed case whose run has `trace_path`."""
    run = {
        "score": 1,
        "error": None,
        "tracePath": trace_path,
        "graders": [grader("ok", passed=True, explanation="x")],
    }
    return {"costUsd": 0.1, "cases": [{"name": "case", "arms": {"with": [run]}}]}


def tool_use(name: str, tool_input: dict[str, str]) -> str:
    """Return one trace line: an assistant message with one tool call."""
    block = {"type": "tool_use", "name": name, "input": tool_input}
    return json.dumps({"type": "assistant", "message": {"content": [block]}})


def test_prints_the_skill_calls_of_each_run(tmp_path: Path) -> None:
    """Each run's Skill calls show in order; other tools and empty inputs do not."""
    trace = tmp_path / "trace.jsonl"
    lines = [
        json.dumps({"type": "system", "subtype": "init"}),
        tool_use("Skill", {}),
        tool_use("Skill", {"skill": "craft:spec", "args": "CRAFT-999"}),
        tool_use("Skill", {"skill": "craft:rules"}),
        tool_use("Read", {"file_path": "x"}),
        json.dumps({"type": "stream_event", "event": {}}),
        tool_use("Skill", {"skill": "craft:bstack"}),
    ]
    trace.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = run_script(tmp_path, one_run(str(trace)))
    assert "  skills: craft:spec, craft:rules, craft:bstack\n" in out


def test_skips_a_cut_off_trace_line(tmp_path: Path) -> None:
    """A run that stops mid-write leaves a partial last line; it is skipped."""
    trace = tmp_path / "trace.jsonl"
    whole = tool_use("Skill", {"skill": "craft:rules"})
    trace.write_text(whole + "\n" + whole[:20], encoding="utf-8")
    out = run_script(tmp_path, one_run(str(trace)))
    assert "  skills: craft:rules\n" in out


def test_still_prints_the_scores_without_a_trace(tmp_path: Path) -> None:
    """A run without a trace file shows its score, and the script exits 0."""
    out = run_script(tmp_path, one_run(str(tmp_path / "gone.jsonl")))
    assert "case: score 1" in out
    assert "skills: (no trace)" in out
    out = run_script(tmp_path, one_run(None))
    assert "case: score 1" in out


def test_prints_each_case_and_the_failed_graders(tmp_path: Path) -> None:
    """A passed case shows its score; a failed grader shows its explanation."""
    result = {
        "costUsd": 0.19,
        "cases": [
            {
                "name": "good-case",
                "arms": {
                    "with": [
                        {
                            "score": 1,
                            "error": None,
                            "graders": [grader("ok", passed=True, explanation="x")],
                        }
                    ]
                },
            },
            {
                "name": "bad-case",
                "arms": {
                    "with": [
                        {
                            "score": 0.5,
                            "error": None,
                            "graders": [
                                grader("ok", passed=True, explanation="x"),
                                grader("asks", passed=False, explanation="votes: FAIL"),
                            ],
                        }
                    ]
                },
            },
        ],
    }
    out = run_script(tmp_path, result)
    assert "good-case: score 1" in out
    assert "bad-case: score 0.5" in out
    assert "FAILED asks: votes: FAIL" in out
    assert "FAILED ok" not in out
    assert "0.19" in out
