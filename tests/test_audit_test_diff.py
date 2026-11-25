# Copyright (C) 2026 Theo van Oostrum
"""`test_diff.py` prints the diff of a PR's test files, for the audit judge.

The script runs as a command, as the audit runs it. The PR files are made up.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "craft" / "skills" / "audit" / "scripts" / "test_diff.py"
LIMIT = 40_000


def changed(
    path: str, patch: str | None = "@@ -1 +1 @@\n-old\n+new"
) -> dict[str, object]:
    """Return one PR file, as the GitHub files API returns it."""
    file: dict[str, object] = {"filename": path, "status": "modified"}
    if patch is not None:
        file["patch"] = patch
    return file


def run_diff(tmp_path: Path, files: list[dict[str, object]]) -> str:
    """Write the PR files, run `test_diff.py` on them, and return its output."""
    path = tmp_path / "files.json"
    path.write_text(json.dumps(files), encoding="utf-8")
    done = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout


@pytest.mark.parametrize(
    "path",
    [
        "tests/test_app.py",
        "src/test/java/AppCheck.java",
        "e2e/projects.ts",
        "src/__tests__/app.tsx",
        "NapTimeUITests/LaunchScreen.swift",
        "Packages/Core/Tests/CoreTests/SleepTimer.swift",
        "test_app.py",
        "app_test.go",
        "src/lib/app.test.ts",
        "src/app.spec.ts",
    ],
)
def test_a_test_file_is_found_by_its_path(tmp_path: Path, path: str) -> None:
    """Each part of the Test file rule."""
    out = run_diff(tmp_path, [changed(path)])
    assert out.startswith(f"== {path} ==\n")
    assert "+new" in out


@pytest.mark.parametrize(
    "path",
    ["src/app.py", "src/latest/notes.md", "contest.py", "docs/testing.md"],
)
def test_other_files_are_left_out(tmp_path: Path, path: str) -> None:
    """A word that only holds `test` is no test file."""
    assert run_diff(tmp_path, [changed(path)]) == "no test files changed\n"


def test_each_test_file_follows_its_heading(tmp_path: Path) -> None:
    """In the order of the PR's files."""
    files = [
        changed("tests/test_a.py", "+a"),
        changed("src/a.py", "+code"),
        changed("tests/test_b.py", "+b"),
    ]
    out = run_diff(tmp_path, files)
    assert out == "== tests/test_a.py ==\n+a\n== tests/test_b.py ==\n+b\n"


def test_no_test_file_says_so(tmp_path: Path) -> None:
    """Review focus 3: the judge judges this line against the spec."""
    assert run_diff(tmp_path, []) == "no test files changed\n"


def test_a_test_file_without_a_patch_says_so(tmp_path: Path) -> None:
    """GitHub leaves out the patch of a large file."""
    out = run_diff(tmp_path, [changed("tests/test_big.py", None)])
    assert out == "== tests/test_big.py ==\n(no patch from GitHub)\n"


def test_a_long_diff_is_cut_with_a_mark(tmp_path: Path) -> None:
    """Review focus 4: at 40,000 characters, and the cut says so."""
    files = [changed(f"tests/test_{n}.py", "+" + "x" * 15_000) for n in range(4)]
    out = run_diff(tmp_path, files)
    body, mark = out.rstrip("\n").rsplit("\n", 1)
    assert mark == f"[… cut at {LIMIT} characters]"
    assert len(body) == LIMIT
    assert "== tests/test_3.py ==" not in out


def test_a_diff_of_exactly_the_limit_is_not_cut(tmp_path: Path) -> None:
    """No mark without a cut."""
    heading = "== tests/test_a.py ==\n"
    patch = "+" + "x" * (LIMIT - len(heading) - 2)
    out = run_diff(tmp_path, [changed("tests/test_a.py", patch)])
    assert len(out) == LIMIT
    assert "cut at" not in out
