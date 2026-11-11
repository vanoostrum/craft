# Copyright (C) 2026 Theo van Oostrum
"""Print each smoke case's score and each failed grader from an eval result.

Usage: `python3 .github/scripts/eval_scores.py <result.json>`, the file that
`claude plugin eval --json` writes. The `evals` job runs it so that a red run
shows in its log which case and which grader failed.
"""

import json
import sys
from pathlib import Path


def main() -> int:
    """Print the scores; the suite step already sets the job's result."""
    result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for case in result["cases"]:
        for run in case["arms"]["with"]:
            print(f"{case['name']}: score {run['score']}")  # noqa: T201
            if run.get("error"):
                print(f"  error: {run['error']}")  # noqa: T201
            for grader in run["graders"]:
                if not grader["passed"]:
                    print(f"  FAILED {grader['name']}: {grader['explanation']}")  # noqa: T201
    print(f"cost: {result.get('costUsd')} USD")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
