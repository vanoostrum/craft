# Copyright (C) 2026 Theo van Oostrum
"""`escapes.py` finds the fix PR candidates and the gate spans with feedback.

The script runs as a command, as the audit runs it. Every fixture is synthetic:
the PRs, paths, tickets, and comments are made up (`docs/adr/0009`).
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "craft" / "skills" / "audit" / "scripts" / "escapes.py"
START = "2026-03-10T00:00:00Z"
END = "2026-03-17T00:00:00Z"

type Json = dict[str, object]


def pr(number: int, merged_at: str, *files: str, title: str = "") -> Json:
    """Return one merged PR, as the audit writes it to `prs.json`."""
    return {
        "number": number,
        "title": title or f"[CRAFT-{number}] Made-up ticket",
        "merged_at": merged_at,
        "files": list(files),
    }


def run(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run `escapes.py` with arguments."""
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )


def candidates(
    tmp_path: Path,
    prs: list[Json],
    searched: list[int],
    start: str = START,
    end: str = END,
) -> list[str]:
    """Write the inputs, run `escapes.py candidates`, and return its lines."""
    (tmp_path / "prs.json").write_text(json.dumps(prs), encoding="utf-8")
    (tmp_path / "searched.txt").write_text(
        "".join(f"{n}\n" for n in searched), encoding="utf-8"
    )
    done = run(tmp_path, "candidates", "prs.json", "searched.txt", start, end)
    assert done.returncode == 0, done.stderr
    return done.stdout.splitlines()


# Criterion 3: the fix PR candidates.


def test_a_later_pr_in_the_window_that_shares_a_file_is_a_candidate(
    tmp_path: Path,
) -> None:
    """One line: the ticket PR, the candidate, and the shared paths."""
    prs = [
        pr(1, "2026-03-11T10:00:00Z", "src/a.py", "src/b.py", "README.md"),
        pr(2, "2026-03-12T10:00:00Z", "src/b.py", "src/a.py", "src/c.py"),
    ]
    assert candidates(tmp_path, prs, [1]) == ["1 2 src/a.py,src/b.py"]


def test_any_title_counts_as_a_candidate(tmp_path: Path) -> None:
    """A fix the owner made by hand has no `[CRAFT-<n>]` title (ADR 0002)."""
    prs = [
        pr(1, "2026-03-11T10:00:00Z", "src/a.py"),
        pr(2, "2026-03-12T10:00:00Z", "src/a.py", title="Fix a typo by hand"),
    ]
    assert candidates(tmp_path, prs, [1]) == ["1 2 src/a.py"]


def test_a_pr_with_no_shared_file_is_no_candidate(tmp_path: Path) -> None:
    """The fix must change a file that the ticket's PR changed."""
    prs = [
        pr(1, "2026-03-11T10:00:00Z", "src/a.py"),
        pr(2, "2026-03-12T10:00:00Z", "src/b.py"),
    ]
    assert candidates(tmp_path, prs, [1]) == []


def test_an_earlier_pr_is_no_candidate(tmp_path: Path) -> None:
    """A PR merged before the ticket's PR cannot fix it."""
    prs = [
        pr(1, "2026-03-12T10:00:00Z", "src/a.py"),
        pr(2, "2026-03-11T10:00:00Z", "src/a.py"),
    ]
    assert candidates(tmp_path, prs, [1]) == []


def test_the_ticket_pr_is_not_its_own_candidate(tmp_path: Path) -> None:
    """It shares every file with itself."""
    prs = [pr(1, "2026-03-11T10:00:00Z", "src/a.py")]
    assert candidates(tmp_path, prs, [1]) == []


def test_the_14_day_edge(tmp_path: Path) -> None:
    """At most 14 days after the ticket's PR: 14 days is in, a second more is out."""
    prs = [
        pr(1, "2026-03-01T10:00:00Z", "src/a.py"),
        pr(2, "2026-03-15T10:00:00Z", "src/a.py"),
        pr(3, "2026-03-15T10:00:01Z", "src/a.py"),
    ]
    assert candidates(tmp_path, prs, [1]) == ["1 2 src/a.py"]


def test_the_window_edges(tmp_path: Path) -> None:
    """The window holds its start and not its end; the next window holds the end."""
    prs = [
        pr(1, "2026-03-09T10:00:00Z", "src/a.py"),
        pr(2, "2026-03-09T23:59:59Z", "src/a.py"),
        pr(3, START, "src/a.py"),
        pr(4, "2026-03-16T23:59:59Z", "src/a.py"),
        pr(5, END, "src/a.py"),
    ]
    assert candidates(tmp_path, prs, [1]) == ["1 3 src/a.py", "1 4 src/a.py"]


def test_a_look_back_ticket_counts_its_fix_in_this_window_only(
    tmp_path: Path,
) -> None:
    """Review focus 2: merged 10 days before the window, fixed in it, counted once."""
    prs = [
        pr(1, "2026-02-28T10:00:00Z", "src/a.py"),
        pr(2, "2026-03-11T10:00:00Z", "src/a.py"),
    ]
    assert candidates(tmp_path, prs, [1]) == ["1 2 src/a.py"]
    next_window = candidates(tmp_path, prs, [1], start=END, end="2026-03-24T00:00:00Z")
    assert next_window == []


def test_a_planned_change_is_still_a_candidate(tmp_path: Path) -> None:
    """Review focus 1: a bump PR shares `plugin.json`; the judge decides."""
    prs = [
        pr(1, "2026-03-11T10:00:00Z", "plugin.json", "skills/a/SKILL.md"),
        pr(2, "2026-03-12T10:00:00Z", "plugin.json", title="[CRAFT-2] Bump"),
    ]
    assert candidates(tmp_path, prs, [1]) == ["1 2 plugin.json"]


def test_only_searched_prs_get_candidates(tmp_path: Path) -> None:
    """A ticket skipped over the cap is not in `searched.txt` and gets none."""
    prs = [
        pr(1, "2026-03-11T10:00:00Z", "src/a.py"),
        pr(2, "2026-03-12T10:00:00Z", "src/a.py"),
        pr(3, "2026-03-13T10:00:00Z", "src/a.py"),
    ]
    assert candidates(tmp_path, prs, [2]) == ["2 3 src/a.py"]


def test_a_searched_pr_missing_from_the_listing_gets_none(tmp_path: Path) -> None:
    """A fill-up ticket that merged before the look-back span: no error."""
    prs = [pr(2, "2026-03-12T10:00:00Z", "src/a.py")]
    assert candidates(tmp_path, prs, [1, 2]) == []


def test_one_fix_can_be_a_candidate_of_two_tickets(tmp_path: Path) -> None:
    """Each ticket gets its own line, in the order of `searched.txt`."""
    prs = [
        pr(1, "2026-03-11T10:00:00Z", "src/a.py"),
        pr(2, "2026-03-11T12:00:00Z", "src/b.py"),
        pr(3, "2026-03-13T10:00:00Z", "src/a.py", "src/b.py"),
    ]
    assert candidates(tmp_path, prs, [2, 1]) == ["2 3 src/b.py", "1 3 src/a.py"]


# Criterion 4: the gate spans with feedback.


def linear(at: str, body: str) -> Json:
    """Return one Linear comment, as the audit saves it."""
    return {"createdAt": at, "body": body}


def github(at: str, body: str, login: str = "owner") -> Json:
    """Return one PR issue comment, as the GitHub API returns it."""
    return {"created_at": at, "body": body, "user": {"login": login}}


def gates(
    tmp_path: Path,
    comments: list[Json],
    pr_comments: list[Json] | None = None,
    merged_at: str = "2026-03-20T00:00:00Z",
) -> str:
    """Write the inputs, run `escapes.py gates`, and return its output."""
    (tmp_path / "linear.json").write_text(json.dumps(comments), encoding="utf-8")
    (tmp_path / "pr.json").write_text(json.dumps(pr_comments or []), encoding="utf-8")
    done = run(tmp_path, "gates", "linear.json", "pr.json", merged_at)
    assert done.returncode == 0, done.stderr
    return done.stdout


def test_a_span_with_owner_feedback_is_printed(tmp_path: Path) -> None:
    """The span's gate, its times, and the feedback in it."""
    out = gates(
        tmp_path,
        [
            linear("2026-03-11T10:00:00Z", "🤖 Gate: spec\n\nThe criteria."),
            linear("2026-03-11T11:00:00Z", "Please make the limit 10."),
            linear("2026-03-11T12:00:00Z", "🤖 Approved: spec (in chat)"),
        ],
    )
    assert out.startswith(
        "== spec gate: 2026-03-11T10:00:00Z to 2026-03-11T12:00:00Z ==\n"
    )
    assert "Please make the limit 10." in out
    assert "The criteria." not in out


def test_a_span_with_only_the_gate_and_its_approval_is_not_printed(
    tmp_path: Path,
) -> None:
    """No feedback, no span; a bare "approve" is no feedback either."""
    out = gates(
        tmp_path,
        [
            linear("2026-03-11T10:00:00Z", "🤖 Gate: spec"),
            linear("2026-03-11T11:00:00Z", "Approve."),
            linear("2026-03-11T12:00:00Z", "🤖 Approved: spec"),
            linear("2026-03-12T10:00:00Z", "🤖 Gate: merge"),
            linear("2026-03-12T11:00:00Z", "🤖 Approved: merge (👍 in chat)"),
        ],
    )
    assert out == ""


def test_a_fix_summary_shows_chat_feedback_at_a_re_posted_gate(
    tmp_path: Path,
) -> None:
    """Review focus 3: feedback in chat only; the fix comment holds it."""
    out = gates(
        tmp_path,
        [
            linear("2026-03-11T10:00:00Z", "🤖 Gate: merge"),
            linear("2026-03-11T11:00:00Z", "🤖 fix: owner feedback applied: rename"),
            linear("2026-03-11T12:00:00Z", "🤖 review: PASS"),
            linear("2026-03-11T13:00:00Z", "🤖 Gate: merge\n\nRe-posted."),
            linear("2026-03-11T14:00:00Z", "🤖 Approved: merge (in chat)"),
        ],
    )
    assert out.count("== merge gate:") == 1
    assert "== merge gate: 2026-03-11T10:00:00Z to 2026-03-11T13:00:00Z ==" in out
    assert "🤖 fix: owner feedback applied: rename" in out
    assert "🤖 review: PASS" not in out


def test_pr_comments_in_the_span_are_feedback(tmp_path: Path) -> None:
    """A fix summary posted as a PR comment, in the span; not one outside it."""
    out = gates(
        tmp_path,
        [
            linear("2026-03-11T10:00:00Z", "🤖 Gate: merge"),
            linear("2026-03-11T12:00:00Z", "🤖 Approved: merge"),
        ],
        [
            github("2026-03-11T09:00:00Z", "Review 1: PASS", "bot"),
            github("2026-03-11T11:00:00Z", "Fix summary: renamed the flag", "bot"),
        ],
    )
    assert "Fix summary: renamed the flag" in out
    assert "Review 1: PASS" not in out


def test_an_old_pass_comment_is_a_gate(tmp_path: Path) -> None:
    """`🤖 Pass: <gate>` is the gate comment from before craft 2.0."""
    out = gates(
        tmp_path,
        [
            linear("2026-03-11T10:00:00Z", "🤖 Pass: plan"),
            linear("2026-03-11T11:00:00Z", "Split ticket 2 in two."),
            linear("2026-03-11T12:00:00Z", "🤖 Approved: plan"),
        ],
    )
    assert "== plan gate: 2026-03-11T10:00:00Z to 2026-03-11T12:00:00Z ==" in out
    assert "Split ticket 2 in two." in out


def test_a_span_with_no_approval_ends_at_the_merge(tmp_path: Path) -> None:
    """No comment after `<merged_at>` is in a span."""
    out = gates(
        tmp_path,
        [
            linear("2026-03-11T10:00:00Z", "🤖 Gate: merge"),
            linear("2026-03-11T11:00:00Z", "Use the other name."),
            linear("2026-03-13T10:00:00Z", "A note after the merge."),
        ],
        merged_at="2026-03-12T00:00:00Z",
    )
    assert "== merge gate: 2026-03-11T10:00:00Z to 2026-03-12T00:00:00Z ==" in out
    assert "Use the other name." in out
    assert "A note after the merge." not in out


def test_other_craft_comments_are_not_feedback(tmp_path: Path) -> None:
    """Only owner comments, `🤖 fix:`, and PR comments count."""
    out = gates(
        tmp_path,
        [
            linear("2026-03-11T10:00:00Z", "🤖 Gate: spec"),
            linear("2026-03-11T11:00:00Z", "🤖 spec review: FAIL — 1 blocking"),
            linear("2026-03-11T12:00:00Z", "🤖 Approved: spec"),
        ],
    )
    assert out == ""


def test_each_gate_has_its_own_spans(tmp_path: Path) -> None:
    """Feedback before the first gate is in no span."""
    out = gates(
        tmp_path,
        [
            linear("2026-03-10T10:00:00Z", "Start on this soon."),
            linear("2026-03-11T10:00:00Z", "🤖 Gate: spec"),
            linear("2026-03-11T11:00:00Z", "Drop criterion 3."),
            linear("2026-03-11T12:00:00Z", "🤖 Approved: spec"),
            linear("2026-03-12T10:00:00Z", "🤖 Gate: merge"),
            linear("2026-03-12T11:00:00Z", "The button is too small."),
            linear("2026-03-12T12:00:00Z", "🤖 Approved: merge"),
        ],
    )
    assert out.index("== spec gate:") < out.index("== merge gate:")
    spec, merge = out.split("== merge gate:")
    assert "Drop criterion 3." in spec
    assert "The button is too small." in merge
    assert "Start on this soon." not in out


def test_a_wrong_command_prints_the_usage(tmp_path: Path) -> None:
    """Exit 2 with the usage text."""
    done = run(tmp_path, "nothing")
    assert done.returncode == 2  # noqa: PLR2004 - the usage error code.
    assert "Usage" in done.stderr
