#!/usr/bin/env python3
# Copyright (C) 2026 Theo van Oostrum
r"""Print a digest of a transcript, for the audit judge.

Usage: digest.py <transcript.jsonl.gz> [<start> <end>]

With a start and an end, such as a segment's `started_at` and `ended_at`, only the
transcript lines with a `timestamp` from start to end count.

One line per event, in order:

    assistant: <the assistant's text, in full>
    tool: <tool name> <the input as JSON, at most 500 characters>
    result: <the tool result, at most 300 characters>

A cut value ends with ` […]`. Newlines show as `\n`. Thinking, the user's own
messages, and other line types are left out.
"""

import gzip
import json
import sys
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

INPUT_CAP = 500
RESULT_CAP = 300
CUT = " […]"


def cap(value: str, limit: int) -> str:
    """Return the value, cut to `limit` characters and marked when cut."""
    return value if len(value) <= limit else value[:limit] + CUT


def one_line(value: str) -> str:
    """Return the value on one line."""
    return value.replace("\n", "\\n")


def result_text(content: str | list[dict[str, Any]]) -> str:
    """Return the text of a tool result, a string or a list of blocks."""
    if isinstance(content, str):
        return content
    return "\n".join(str(block.get("text", "")) for block in content)


def events(line: dict[str, Any]) -> Iterator[str]:
    """Return the digest lines of one transcript line."""
    content = line.get("message", {}).get("content")
    if not isinstance(content, list):
        return
    for block in content:
        kind = block.get("type")
        if line.get("type") == "assistant" and kind == "text":
            yield f"assistant: {one_line(block['text'].strip())}"
        elif line.get("type") == "assistant" and kind == "tool_use":
            tool_input = cap(json.dumps(block.get("input", {})), INPUT_CAP)
            yield f"tool: {block['name']} {one_line(tool_input)}"
        elif line.get("type") == "user" and kind == "tool_result":
            text = cap(result_text(block.get("content", "")), RESULT_CAP)
            yield f"result: {one_line(text)}"


def in_span(line: dict[str, Any], span: list[str]) -> bool:
    """Return whether a line falls in the span, or there is no span."""
    if not span:
        return True
    start, end = (datetime.fromisoformat(stamp) for stamp in span)
    stamp = line.get("timestamp")
    return stamp is not None and start <= datetime.fromisoformat(stamp) <= end


def main(argv: list[str]) -> int:
    """Print the digest, or the usage and exit 2."""
    if len(argv) not in (2, 4):
        sys.stderr.write(f"{__doc__}\n")
        return 2
    with gzip.open(Path(argv[1]), "rt", encoding="utf-8") as transcript:
        for raw in transcript:
            line = json.loads(raw) if raw.strip() else {}
            if line and in_span(line, argv[2:]):
                for event in events(line):
                    sys.stdout.write(f"{event}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
