# Copyright (C) 2026 Theo van Oostrum
"""The smoke case `one-shot-grills-one-ticket` grades the last message with regex.

The CLI runs each `regex` grader's pattern on the last message. These tests do
the same with Python `re`, so a grader cannot fail a correct round, or pass a
round that asks about several tickets.
"""

import re
from pathlib import Path

from tests.test_dev_environment import FRONTMATTER, frontmatter

GRADERS = (
    Path(__file__).resolve().parents[1]
    / "plugins"
    / "craft"
    / "evals"
    / "one-shot-grills-one-ticket"
    / "graders"
)

ONE_TICKET = """**CRAFT-901 Share the family: two questions**

1. What does Settings show while the invite is not opened yet?
   I recommend "Invite sent. Waiting for your partner to open the link."
2. What happens to children the partner added before joining?
   I recommend they stay on the partner's phone only.

After your answers I grill CRAFT-902 Sleep timer on the Lock Screen,
and then CRAFT-903 Nudges."""

SEVERAL_TICKETS = (
    ONE_TICKET
    + """

**CRAFT-902 Sleep timer on the Lock Screen**

1. Does the Live Activity close at once after "Awake"?"""
)


def passes(grader: str, message: str) -> bool:
    """Return whether the regex grader `grader` passes on `message`."""
    path = GRADERS / f"{grader}.md"
    meta = frontmatter(path)
    assert meta["type"] == "regex"
    assert meta["target"] == "last_message"
    pattern = FRONTMATTER.sub("", path.read_text(encoding="utf-8")).strip()
    flags = re.IGNORECASE if "i" in meta.get("flags", "") else 0
    flags |= re.DOTALL if "s" in meta.get("flags", "") else 0
    found = re.search(pattern, message, flags) is not None
    return not found if meta.get("match") == "not_contains" else found


def test_a_round_for_the_first_ticket_passes() -> None:
    """Naming the later tickets' titles is fine; only their questions are not."""
    assert passes("grills-the-first-ticket", ONE_TICKET)
    assert passes("no-other-tickets-questions", ONE_TICKET)


def test_a_round_for_several_tickets_fails() -> None:
    """A round that also asks the second ticket's questions fails."""
    assert not passes("no-other-tickets-questions", SEVERAL_TICKETS)


def test_a_round_without_the_first_tickets_questions_fails() -> None:
    """A message that asks nothing about the first ticket fails."""
    assert not passes("grills-the-first-ticket", "I can't reach Linear. Stopping.")
