#!/usr/bin/env python3
# Copyright (C) 2026 Theo van Oostrum
"""Score the Attempts and Feedback speed measures of the Build rubric.

Usage: build.py attempts|speed <input.json>

`input.json` holds what the audit read for one ticket:

    {"required_checks": ["checks", "evals"],
     "comments": [{"body": "🤖 build: retry 1 of 4 — CI failed on lint"}],
     "check_runs": [{"name": "checks", "status": "completed",
                     "conclusion": "failure", "started_at": "...",
                     "completed_at": "..."}],
     "segments": [{"step": "build", "work_seconds": 840.0,
                   "subagents": [{"role": "Run project-verify",
                                  "started_at": "...", "ended_at": "..."}]}]}

`required_checks` comes from `Required CI checks` in the project's
`.claude/craft.md`, `comments` are the ticket's Linear comments, `check_runs`
are the check runs on every commit of the PR, and `segments` are the ticket's
segments from `metadata.json`. Only segments with `step` `build` count.

Prints JSON: `{"values": {...}}`, with `null` for no data.

- `attempts`: Failed attempts, the comments that start with `🤖 build: retry`;
  CI reds, the runs of a required check whose conclusion is `failure` or
  `timed_out`; and Work minutes, the sum of the build segments' `work_seconds`
  in minutes, or `null` with no build segment.
- `speed`: Verify minutes, the median duration of the build segments' verify
  subagents, and CI minutes, the median duration of the completed runs of the
  required checks. A subagent is a verify run when its role holds "verify",
  case-insensitive, and none of "app driver", "smoke", "drive", or "eval".
"""

import json
import statistics
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

type Json = dict[str, Any]  # Parsed JSON of the input file.

RETRY = "🤖 build: retry"
RED = ("failure", "timed_out")
NOT_VERIFY = ("app driver", "smoke", "drive", "eval")


def minutes(start: str | None, end: str | None) -> float | None:
    """Return the minutes from start to end, or None when one is missing."""
    if start is None or end is None:
        return None
    span = datetime.fromisoformat(end) - datetime.fromisoformat(start)
    return span.total_seconds() / 60


def median(values: list[float | None]) -> float | None:
    """Return the median of the known values, or None with none."""
    known = [value for value in values if value is not None]
    return statistics.median(known) if known else None


def build_segments(data: Json) -> list[Json]:
    """Return the ticket's build segments."""
    return [segment for segment in data["segments"] if segment.get("step") == "build"]


def required_runs(data: Json) -> list[Json]:
    """Return the check runs of the required checks."""
    required = set(data["required_checks"])
    return [run for run in data["check_runs"] if run.get("name") in required]


def is_verify_run(role: str) -> bool:
    """Return whether a subagent's role names a verify run."""
    role = role.lower()
    return "verify" in role and not any(word in role for word in NOT_VERIFY)


def attempts(data: Json) -> dict[str, float | None]:
    """Return Failed attempts, CI reds, and Work minutes."""
    segments = build_segments(data)
    work = sum(float(s.get("work_seconds") or 0) for s in segments) / 60
    return {
        "Failed attempts": sum(
            (c.get("body") or "").startswith(RETRY) for c in data["comments"]
        ),
        "CI reds": sum(run.get("conclusion") in RED for run in required_runs(data)),
        "Work minutes": round(work, 2) if segments else None,
    }


def speed(data: Json) -> dict[str, float | None]:
    """Return Verify minutes and CI minutes."""
    verify = [
        minutes(agent.get("started_at"), agent.get("ended_at"))
        for segment in build_segments(data)
        for agent in segment.get("subagents", [])
        if is_verify_run(str(agent.get("role") or ""))
    ]
    ci = [
        minutes(run.get("started_at"), run.get("completed_at"))
        for run in required_runs(data)
        if run.get("status") == "completed"
    ]
    return {"Verify minutes": median(verify), "CI minutes": median(ci)}


COMMANDS = {"attempts": attempts, "speed": speed}


def main(argv: list[str]) -> int:
    """Print the values, or the usage and exit 2."""
    if len(argv) != 3 or argv[1] not in COMMANDS:  # noqa: PLR2004 - command and file.
        sys.stderr.write(f"{__doc__}\n")
        return 2
    data = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    values = COMMANDS[argv[1]](data)
    sys.stdout.write(json.dumps({"values": values}, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
