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


def digest(tmp_path: Path, lines: list[dict[str, Any]], *span: str) -> str:
    """Write a gzipped transcript, run `digest.py` on it, and return its output."""
    path = tmp_path / "agent.jsonl.gz"
    body = "".join(json.dumps(line) + "\n" for line in lines)
    path.write_bytes(gzip.compress(body.encode("utf-8")))
    options = list(span[:2]) if span[:1] == ("--result-cap",) else []
    rest = span[len(options) :]
    done = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), *options, str(path), *rest],
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
    """A file read is cut, as a string or as text blocks: head and tail."""
    body = "h" * 150 + "y" * 700 + "t" * 150
    out = digest(tmp_path, [user([result(body)]), user([result([text(body)])])])
    shown = [line for line in out.splitlines() if line.startswith("result: ")]
    assert shown == [f"result: {'h' * 150} […] {'t' * 150}"] * 2


def test_a_cut_result_keeps_the_summary_line_of_a_test_run(tmp_path: Path) -> None:
    """CRAFT-91 criterion 5: `1 failed` at the end of the output stays in."""
    body = "collected 40 items\n" + "." * 2000 + "\n1 failed, 39 passed in 2.1s"
    out = digest(tmp_path, [user([result(body)])])
    assert out.startswith("result: collected 40 items")
    assert out.rstrip().endswith("1 failed, 39 passed in 2.1s")
    assert " […] " in out


def test_the_result_cap_is_an_option(tmp_path: Path) -> None:
    """CRAFT-91 criterion 5: `--result-cap 2000` for subagent transcripts."""
    body = "a" * 1500 + "b" * 1500
    out = digest(tmp_path, [user([result(body)])], "--result-cap", "2000")
    assert out == f"result: {'a' * 1000} […] {'b' * 1000}\n"
    assert digest(tmp_path, [user([result("c" * 2000)])], "--result-cap", "2000") == (
        f"result: {'c' * 2000}\n"
    )


def test_the_result_cap_works_with_a_span(tmp_path: Path) -> None:
    """The option goes before the transcript, the span after it."""
    line = {**user([result("d" * 50)]), "timestamp": "2026-11-20T10:05:00.000Z"}
    span = ("2026-11-20T10:04:00.000Z", "2026-11-20T10:06:00.000Z")
    out = digest(tmp_path, [line], "--result-cap", "20", *span)
    assert out == f"result: {'d' * 10} […] {'d' * 10}\n"


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


def test_a_span_keeps_only_the_lines_of_one_segment(tmp_path: Path) -> None:
    """A review segment's part of a whole session transcript."""

    def at(minute: int, line: dict[str, Any]) -> dict[str, Any]:
        return {**line, "timestamp": f"2026-11-20T10:{minute:02d}:00.000Z"}

    lines = [
        at(1, assistant(text("Build."))),
        at(5, assistant(text("Review."))),
        at(9, assistant(text("Merge."))),
    ]
    span = ("2026-11-20T10:04:00.000Z", "2026-11-20T10:06:00.000Z")
    assert digest(tmp_path, lines, *span) == "assistant: Review.\n"
