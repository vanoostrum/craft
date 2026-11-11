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
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    out = subprocess.run(  # noqa: S603 - runs the script under test.
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "good-case: score 1" in out
    assert "bad-case: score 0.5" in out
    assert "FAILED asks: votes: FAIL" in out
    assert "FAILED ok" not in out
    assert "0.19" in out
