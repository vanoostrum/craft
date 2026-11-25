#!/usr/bin/env python3
# Copyright (C) 2026 Theo van Oostrum
"""Print the diff of a PR's test files, for the audit judge.

Usage: test_diff.py <files.json>

`files.json` is the PR's files, as
`gh api "repos/<repo>/pulls/<n>/files?per_page=100"` returns them. A file is a
test file when a part of its path is `tests`, `test`, `e2e`, or `__tests__`, or
ends with `Tests`, such as `NapTimeUITests`, or when its file name matches
`test_*`, `*_test.*`, `*.test.*`, or `*.spec.*`.

Prints the `patch` of each test file after a line `== <path> ==`, in the order
of the files. A test file with no `patch`, such as a large file, gets
`(no patch from GitHub)`. With no test file, prints `no test files changed`.
The output stops at 40,000 characters, and then ends with
`[… cut at 40000 characters]`.
"""

import json
import sys
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

LIMIT = 40_000
TEST_FOLDERS = ("tests", "test", "e2e", "__tests__")
TEST_NAMES = ("test_*", "*_test.*", "*.test.*", "*.spec.*")
NO_TESTS = "no test files changed"
NO_PATCH = "(no patch from GitHub)"


def is_test_file(path: str) -> bool:
    """Return whether a changed file is a test file, by the Test file rule."""
    parts = PurePosixPath(path).parts
    folders, name = parts[:-1], parts[-1]
    if any(part in TEST_FOLDERS or part.endswith("Tests") for part in folders):
        return True
    return any(fnmatchcase(name, pattern) for pattern in TEST_NAMES)


def diff(files: list[dict[str, object]]) -> str:
    """Return the diff of the test files, cut at the limit."""
    parts = [
        f"== {file['filename']} ==\n{file.get('patch', NO_PATCH)}\n"
        for file in files
        if is_test_file(str(file["filename"]))
    ]
    if not parts:
        return f"{NO_TESTS}\n"
    text = "".join(parts)
    if len(text) <= LIMIT:
        return text
    return f"{text[:LIMIT]}\n[… cut at {LIMIT} characters]\n"


def main(argv: list[str]) -> int:
    """Print the diff, or the usage and exit 2."""
    if len(argv) != 2:  # noqa: PLR2004 - the script and the files file.
        sys.stderr.write(f"{__doc__}\n")
        return 2
    files = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    sys.stdout.write(diff(files))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
