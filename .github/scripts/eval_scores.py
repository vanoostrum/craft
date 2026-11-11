# Copyright (C) 2026 Theo van Oostrum
"""Print each smoke case's score, Skill calls, and failed graders from an eval result.

Usage: `python3 .github/scripts/eval_scores.py <result.json>`, the file that
`claude plugin eval --json` writes. The `evals` job runs it so that a red run
shows in its log which case and which grader failed, and which skills the
agent loaded. The Skill calls come from each run's `tracePath`, which exists
only when the suite ran with `--keep-temp`.
"""

import json
import sys
from pathlib import Path


def skill_calls(trace_path: str | None) -> str:
    """Return the skills that a run's trace loads, in order, or `(no trace)`."""
    if trace_path is None or not Path(trace_path).is_file():
        return "(no trace)"
    skills: list[str] = []
    for line in Path(trace_path).read_text(encoding="utf-8").splitlines():
        message = json.loads(line)
        if message.get("type") != "assistant":
            continue
        for block in message["message"].get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "Skill":
                skill = block.get("input", {}).get("skill")
                if isinstance(skill, str):
                    skills.append(skill)
    return ", ".join(skills) if skills else "(none)"


def main() -> int:
    """Print the scores; the suite step already sets the job's result."""
    result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for case in result["cases"]:
        for run in case["arms"]["with"]:
            print(f"{case['name']}: score {run['score']}")  # noqa: T201
            print(f"  skills: {skill_calls(run.get('tracePath'))}")  # noqa: T201
            if run.get("error"):
                print(f"  error: {run['error']}")  # noqa: T201
            for grader in run["graders"]:
                if not grader["passed"]:
                    print(f"  FAILED {grader['name']}: {grader['explanation']}")  # noqa: T201
    print(f"cost: {result.get('costUsd')} USD")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
