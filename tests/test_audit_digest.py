# Copyright (C) 2026 Theo van Oostrum
"""`digest.py` prints a small digest of a transcript for the audit judge.

The script runs as a command, as the audit runs it. The transcript is made up.
"""

import gzip
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "craft" / "skills" / "audit" / "scripts" / "digest.py"


def assistant(*content: dict[str, Any]) -> dict[str, Any]:
    """Return an assistant line."""
    return {"type": "assistant", "message": {"role": "assistant", "content": content}}


def user(content: str | list[dict[str, Any]]) -> dict[str, Any]:
    """Return a user line."""
    return {"type": "user", "message": {"role": "user", "content": content}}


def text(value: str) -> dict[str, Any]:
    """Return a text block."""
    return {"type": "text", "text": value}


def call(name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    """Return a tool call block."""
    return {"type": "tool_use", "id": "call-1", "name": name, "input": tool_input}


def result(content: str | list[dict[str, Any]]) -> dict[str, Any]:
    """Return a tool result block."""
    return {"type": "tool_result", "tool_use_id": "call-1", "content": content}


def digest(tmp_path: Path, lines: list[dict[str, Any]]) -> str:
    """Write a gzipped transcript, run `digest.py` on it, and return its output."""
    path = tmp_path / "agent.jsonl.gz"
    body = "".join(json.dumps(line) + "\n" for line in lines)
    path.write_bytes(gzip.compress(body.encode("utf-8")))
    done = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


# Criterion 7: the digest.


def test_the_digest_keeps_the_assistant_text_in_full(tmp_path: Path) -> None:
    """The reviewer's own words are what the checks judge."""
    words = "I read the whole file. " * 100
    out = digest(tmp_path, [assistant(text(words))])
    assert f"assistant: {words.strip()}" in out


def test_the_digest_names_each_tool_call_with_its_input(tmp_path: Path) -> None:
    """The name and the input as JSON."""
    out = digest(tmp_path, [assistant(call("Read", {"file_path": "src/app.py"}))])
    assert 'tool: Read {"file_path": "src/app.py"}' in out


def test_a_tool_input_is_capped_at_500_characters(tmp_path: Path) -> None:
    """A long Bash command is cut."""
    command = "x" * 2000
    out = digest(tmp_path, [assistant(call("Bash", {"command": command}))])
    line = next(line for line in out.splitlines() if line.startswith("tool: Bash"))
    shown = line.removeprefix("tool: Bash ")
    assert shown == json.dumps({"command": command})[:500] + " […]"


def test_a_tool_result_is_capped_at_300_characters(tmp_path: Path) -> None:
    """A file read is cut, as a string or as text blocks."""
    body = "y" * 1000
    out = digest(tmp_path, [user([result(body)]), user([result([text(body)])])])
    shown = [line for line in out.splitlines() if line.startswith("result: ")]
    assert shown == [f"result: {body[:300]} […]"] * 2


def test_short_values_are_not_marked_as_cut(tmp_path: Path) -> None:
    """No `[…]` without a cut."""
    out = digest(tmp_path, [user([result("ok")])])
    assert out == "result: ok\n"


def test_the_digest_leaves_out_what_the_judge_does_not_need(tmp_path: Path) -> None:
    """Thinking, the user's own prompt, and other line types."""
    lines = [
        user("Review the PR."),
        assistant({"type": "thinking", "thinking": "secret plan"}),
        {"type": "summary", "summary": "a summary"},
        assistant(text("Done.")),
    ]
    assert digest(tmp_path, lines) == "assistant: Done.\n"


def test_newlines_stay_inside_one_digest_line(tmp_path: Path) -> None:
    """Each event is one line, so the order stays readable."""
    out = digest(tmp_path, [user([result("line 1\nline 2")])])
    assert out == "result: line 1\\nline 2\n"
