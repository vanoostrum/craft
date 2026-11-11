# Copyright (C) 2026 Theo van Oostrum
"""The `evals` job checks its secret first, then skips PRs outside the plugin.

Each test runs `evals_gate.py` as the job does, in a temporary git repo with a
base commit and a head commit.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / ".github" / "scripts" / "evals_gate.py"
KEY = "ANTHROPIC_API_KEY"


def git(repo: Path, *args: str) -> str:
    """Run git in `repo` and return its output."""
    return subprocess.run(  # noqa: S603 - runs git on a test repo.
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def repo_with_change(tmp_path: Path, changed: str) -> tuple[Path, str]:
    """Return a repo whose head commit changes `changed`, and its base SHA."""
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "base")
    base = git(repo, "rev-parse", "HEAD")
    path = repo / changed
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("head\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "head")
    return repo, base


def run_gate(
    repo: Path, base: str, key: str, tmp_path: Path
) -> tuple[subprocess.CompletedProcess[str], str]:
    """Run the gate as the job does; return the process and `$GITHUB_OUTPUT`."""
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    env = {**os.environ, KEY: key, "GITHUB_OUTPUT": str(output)}
    result = subprocess.run(  # noqa: S603 - runs the script under test.
        [sys.executable, str(GATE), base],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, output.read_text(encoding="utf-8")


@pytest.mark.parametrize("changed", ["README.md", "plugins/craft/skills/x.md"])
def test_an_empty_secret_fails_and_names_it(tmp_path: Path, changed: str) -> None:
    """Without the secret the job fails on every PR, also on a docs-only PR."""
    repo, base = repo_with_change(tmp_path, changed)
    result, output = run_gate(repo, base, "", tmp_path)
    assert result.returncode != 0
    assert KEY in result.stdout + result.stderr
    assert "run=" not in output


@pytest.mark.parametrize("changed", ["README.md", "tests/test_x.py", "docs/a.md"])
def test_a_change_outside_the_plugin_skips_the_suite(
    tmp_path: Path, changed: str
) -> None:
    """A PR that does not touch the plugin, the marketplace, or CI skips the suite."""
    repo, base = repo_with_change(tmp_path, changed)
    result, output = run_gate(repo, base, "sk-test", tmp_path)
    assert result.returncode == 0, result.stderr
    assert output.strip() == "run=false"


@pytest.mark.parametrize(
    "changed",
    [
        "plugins/craft/skills/rules/SKILL.md",
        ".claude-plugin/marketplace.json",
        ".github/workflows/ci.yml",
    ],
)
def test_a_change_to_the_plugin_runs_the_suite(tmp_path: Path, changed: str) -> None:
    """A PR that touches the plugin, the marketplace, or CI runs the suite."""
    repo, base = repo_with_change(tmp_path, changed)
    result, output = run_gate(repo, base, "sk-test", tmp_path)
    assert result.returncode == 0, result.stderr
    assert output.strip() == "run=true"


def test_moving_a_file_out_of_the_plugin_runs_the_suite(tmp_path: Path) -> None:
    """A rename out of `plugins/` changes the plugin, so the suite runs."""
    repo, _ = repo_with_change(tmp_path, "plugins/craft/skills/x/SKILL.md")
    base = git(repo, "rev-parse", "HEAD")
    (repo / "docs").mkdir()
    git(repo, "mv", "plugins/craft/skills/x/SKILL.md", "docs/SKILL.md")
    git(repo, "commit", "-q", "-m", "move")
    result, output = run_gate(repo, base, "sk-test", tmp_path)
    assert result.returncode == 0, result.stderr
    assert output.strip() == "run=true"


@pytest.mark.parametrize("changed", ["plugins/café.md", "plugins/a b/SKILL.md"])
def test_an_unusual_plugin_path_runs_the_suite(tmp_path: Path, changed: str) -> None:
    """A plugin path with a non-ASCII character or a space still runs the suite."""
    repo, base = repo_with_change(tmp_path, changed)
    result, output = run_gate(repo, base, "sk-test", tmp_path)
    assert result.returncode == 0, result.stderr
    assert output.strip() == "run=true"
