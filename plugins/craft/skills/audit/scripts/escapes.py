#!/usr/bin/env python3
# Copyright (C) 2026 Theo van Oostrum
"""Find the fix PR candidates and the gate spans with feedback, for the escape judge.

Usage:
    escapes.py candidates <prs.json> <searched.txt> <window start> <window end>
    escapes.py gates <linear comments.json> <pr comments.json> <merged_at>

`candidates` reads the merged PRs of one project from `prs.json`, a list of
`{"number", "title", "merged_at", "files"}` with `files` the changed paths, and
the PR numbers of the searched tickets from `searched.txt`, one per line. A fix
PR candidate of a searched PR is another PR that merged in the window (from its
start, up to but not at its end), after the searched PR and at most 14 days
after it, and changes at least one of its files. Any title counts. It prints
one line per candidate, `<ticket PR> <candidate PR> <shared paths>`, with the
shared paths comma-separated, in the order of `searched.txt`, then by merge
time. A searched PR that is not in `prs.json` gets no candidate.

`gates` reads the ticket's Linear comments (`createdAt`, `body`) and the PR's
issue comments, as `gh api repos/<repo>/issues/<n>/comments` returns them. A
gate span runs from a `🤖 Gate: <gate>` comment, or an old `🤖 Pass: <gate>`,
to the next `🤖 Approved: <gate>`, the next gate comment for the same gate, or
`<merged_at>`, whichever comes first. Its feedback is each owner comment (no
`🤖`) that is not only "approve", each `🤖 fix:` comment, and each PR comment
in the span. It prints each span with feedback, after a line
`== <gate> gate: <start> to <end> ==`, with each comment after a line
`-- <time> <source> --`. A span with no feedback is not printed.
"""

import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

LOOK_BACK = timedelta(days=14)
GATE = re.compile(r"\A🤖 (?:Gate|Pass): (\w+)")
APPROVED = re.compile(r"\A🤖 Approved: (\w+)")
FIX = "🤖 fix:"
CRAFT = "🤖"
APPROVE = re.compile(r"\A\s*approve[.!]?\s*\Z", re.IGNORECASE)

type Json = dict[str, Any]  # Parsed JSON from GitHub, Linear, or the audit.


def when(text: str) -> datetime:
    """Return an ISO 8601 time, such as `2026-03-11T10:00:00Z`."""
    return datetime.fromisoformat(text)


def candidates(prs: list[Json], searched: list[int], start: str, end: str) -> str:
    """Return the candidate lines of the searched PRs."""
    window = (when(start), when(end))
    by_number = {int(str(pr["number"])): pr for pr in prs}
    merged = sorted(prs, key=lambda pr: (when(str(pr["merged_at"])), pr["number"]))
    lines = []
    for number in searched:
        ticket = by_number.get(number)
        if ticket is None:
            continue
        ticket_at = when(str(ticket["merged_at"]))
        ticket_files = set(map(str, ticket["files"]))
        for pr in merged:
            at = when(str(pr["merged_at"]))
            shared = sorted(ticket_files & set(map(str, pr["files"])))
            if (
                pr["number"] != number
                and window[0] <= at < window[1]
                and ticket_at < at <= ticket_at + LOOK_BACK
                and shared
            ):
                lines.append(f"{number} {pr['number']} {','.join(shared)}\n")
    return "".join(lines)


@dataclass(frozen=True)
class Comment:
    """One comment on the ticket or the PR, in time order."""

    at: datetime
    time: str
    source: str
    body: str


def comments(linear: list[Json], github: list[Json]) -> list[Comment]:
    """Return the Linear and PR comments in time order."""
    found = [
        Comment(
            when(str(c["createdAt"])), str(c["createdAt"]), "Linear", str(c["body"])
        )
        for c in linear
    ]
    for c in github:
        user = c.get("user")
        login = user.get("login", "?") if isinstance(user, dict) else "?"
        time = str(c["created_at"])
        found.append(
            Comment(when(time), time, f"PR comment by {login}", str(c["body"]))
        )
    return sorted(found, key=lambda c: c.at)


def is_feedback(comment: Comment) -> bool:
    """Return whether a comment in a span is feedback."""
    if comment.source != "Linear":
        return True
    if comment.body.startswith(CRAFT):
        return comment.body.startswith(FIX)
    return not APPROVE.match(comment.body)


def span_end(rest: list[Comment], gate: str, merged: Comment) -> Comment:
    """Return the comment that ends a span: approval, re-post, or the merge."""
    for comment in rest:
        if comment.at >= merged.at:
            break
        if comment.source != "Linear":
            continue
        for pattern in (APPROVED, GATE):
            found = pattern.match(comment.body)
            if found and found.group(1) == gate:
                return comment
    return merged


def gates(linear: list[Json], github: list[Json], merged_at: str) -> str:
    """Return each gate span with feedback, and its comments."""
    merged = Comment(when(merged_at), merged_at, "merge", "")
    ordered = comments(linear, github)
    out = []
    for index, comment in enumerate(ordered):
        gate = GATE.match(comment.body) if comment.source == "Linear" else None
        if gate is None or comment.at >= merged.at:
            continue
        rest = ordered[index + 1 :]
        end = span_end(rest, gate.group(1), merged)
        inside = [c for c in rest if c.at < end.at and c is not end]
        feedback = [c for c in inside if is_feedback(c)]
        if not feedback:
            continue
        out.append(f"== {gate.group(1)} gate: {comment.time} to {end.time} ==\n")
        out.extend(f"-- {c.time} {c.source} --\n{c.body}\n" for c in feedback)
    return "".join(out)


def read(path: str) -> list[Json]:
    """Return a JSON list from a file."""
    data: list[Json] = json.loads(Path(path).read_text(encoding="utf-8"))
    return data


def main(argv: list[str]) -> int:
    """Run one command, or print the usage and exit 2."""
    command, args = (argv[1], argv[2:]) if len(argv) > 1 else ("", [])
    if command == "candidates" and len(args) == 4:  # noqa: PLR2004 - its inputs.
        searched = [
            int(line)
            for line in Path(args[1]).read_text(encoding="utf-8").split()
            if line.strip()
        ]
        sys.stdout.write(candidates(read(args[0]), searched, args[2], args[3]))
        return 0
    if command == "gates" and len(args) == 3:  # noqa: PLR2004 - its inputs.
        sys.stdout.write(gates(read(args[0]), read(args[1]), args[2]))
        return 0
    sys.stderr.write(f"{__doc__}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
