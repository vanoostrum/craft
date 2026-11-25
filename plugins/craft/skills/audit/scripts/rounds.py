#!/usr/bin/env python3
# Copyright (C) 2026 Theo van Oostrum
"""Score the Findings rounds measure from a PR's comments.

Usage: rounds.py <comments.json>

`comments.json` is the PR's issue comments, as
`gh api repos/<repo>/issues/<n>/comments` returns them. A review round is a
comment with a verdict line: a line that holds only
`PASS — <n> blocking, <m> non-blocking` or `FAIL — <n> blocking, <m> non-blocking`,
optionally followed by ` (follow-up review)`. A comment counts at most once, with
its last verdict line, so a verdict quoted inside a sentence or a quote is not a
round.

Prints JSON: `{"status": ..., "values": {...}}`.

- `PASS`: `Rounds until PASS` counts the rounds up to the first PASS, and
  `Blocking per round` is their blocking findings divided by that count.
- `no PASS`: the same values over all rounds, for a PR that never passed.
- `no data`: no verdict line, such as a review from before craft 2.9.0, which
  ended with a bare PASS or FAIL. Both values are `null`.
"""

import json
import re
import sys
from pathlib import Path

VERDICT = re.compile(
    r"^(PASS|FAIL) — (\d+) blocking, \d+ non-blocking(?: \(follow-up review\))?$",
    re.MULTILINE,
)
VALUES = ("Rounds until PASS", "Blocking per round")


def verdicts(comments: list[dict[str, str]]) -> list[tuple[str, int]]:
    """Return the verdict and blocking count of each review round, in order."""
    found: list[tuple[str, int]] = []
    for comment in sorted(comments, key=lambda comment: comment["created_at"]):
        lines = VERDICT.findall(comment.get("body") or "")
        if lines:
            verdict, blocking = lines[-1]
            found.append((str(verdict), int(blocking)))
    return found


def score(rounds: list[tuple[str, int]]) -> dict[str, object]:
    """Return the status and the two values."""
    if not rounds:
        return {"status": "no data", "values": dict.fromkeys(VALUES)}
    passes = [i for i, (verdict, _) in enumerate(rounds) if verdict == "PASS"]
    counted = rounds[: passes[0] + 1] if passes else rounds
    blocking = sum(n for _, n in counted)
    return {
        "status": "PASS" if passes else "no PASS",
        "values": dict(
            zip(VALUES, (len(counted), blocking / len(counted)), strict=True)
        ),
    }


def main(argv: list[str]) -> int:
    """Print the score, or the usage and exit 2."""
    if len(argv) != 2:  # noqa: PLR2004 - the script and the comments file.
        sys.stderr.write(f"{__doc__}\n")
        return 2
    comments = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    sys.stdout.write(json.dumps(score(verdicts(comments)), ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
