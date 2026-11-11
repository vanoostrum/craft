# Copyright (C) 2026 Theo van Oostrum
"""Decide whether the `evals` job runs the smoke suite on this PR.

Usage: `python3 .github/scripts/evals_gate.py <base sha>`, in the PR checkout.

It fails when the secret `ANTHROPIC_API_KEY` is empty, on every PR. Otherwise
it writes `run=true` to `$GITHUB_OUTPUT` when the PR changes a file under one
of `WATCHED`, and `run=false` when it does not.
"""

import os
import subprocess
import sys
from pathlib import Path

KEY = "ANTHROPIC_API_KEY"
WATCHED = ("plugins/", ".claude-plugin/", ".github/workflows/")


def changed_files(base: str) -> list[str]:
    """Return the files that the head commit changes since `base`."""
    diff = subprocess.run(  # noqa: S603 - the base SHA comes from the PR event.
        ["git", "diff", "--name-only", "--no-renames", f"{base}...HEAD"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    )
    return diff.stdout.split()


def main() -> int:
    """Check the secret, then write whether the suite runs."""
    if not os.environ.get(KEY, "").strip():
        print(  # noqa: T201
            f"The secret {KEY} is empty. Add it on the repository in Settings, "
            "Secrets and variables, Actions."
        )
        return 1
    run = any(path.startswith(WATCHED) for path in changed_files(sys.argv[1]))
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
        output.write(f"run={str(run).lower()}\n")
    print(f"run={str(run).lower()}")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
