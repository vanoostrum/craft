# Copyright (C) 2026 Theo van Oostrum
"""`release_prep.py` does the fixed local steps of a release.

Each test runs the script as the release skill does, in a clone of a temporary
bare repo that stands in for GitHub. The bare repo holds the release tags; the
clone has none of them, as in a fresh cloud checkout.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests.test_evals_gate import git

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude" / "skills" / "release" / "scripts" / "release_prep.py"
PLUGIN_JSON = Path("plugins") / "craft" / ".claude-plugin" / "plugin.json"
IDENTITY = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.invalid",
}


def write_version(repo: Path, version: str) -> None:
    """Write `plugin.json` at `version`, in the layout of the real file."""
    path = repo / PLUGIN_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {"name": "craft", "version": version, "license": "UNLICENSED"}
    path.write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")


def commit(repo: Path, subject: str, version: str | None = None) -> str:
    """Commit a change with `subject`, and return its short SHA."""
    if version:
        write_version(repo, version)
    else:
        notes = repo / "notes.txt"
        notes.write_text(notes.read_text("utf-8") + subject + "\n", "utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", subject)
    return git(repo, "rev-parse", "--short", "HEAD")


def released(tmp_path: Path) -> tuple[Path, Path]:
    """Return an `origin` just after release 2.8.2, and a clone on `dev`.

    `main` is `dev` plus the release merge commit, tagged `v2.8.2` on
    `origin` only. `dev` holds the bump to 2.8.2.
    """
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    repo = tmp_path / "repo"
    git(tmp_path, "clone", "-q", str(origin), str(repo))
    git(repo, "checkout", "-q", "-b", "main")
    (repo / "notes.txt").write_text("", "utf-8")
    commit(repo, "Start", version="2.8.1")
    git(repo, "tag", "v2.8.1")
    git(repo, "checkout", "-q", "-b", "dev")
    commit(repo, "Bump craft to 2.8.2 (#35)", version="2.8.2")
    git(repo, "checkout", "-q", "main")
    git(repo, "merge", "-q", "--no-ff", "dev", "-m", "Release craft 2.8.2 (#36)")
    git(repo, "tag", "v2.8.2")
    git(repo, "push", "-q", "origin", "main", "dev", "v2.8.1", "v2.8.2")
    git(repo, "tag", "-d", "v2.8.1", "v2.8.2")
    git(repo, "checkout", "-q", "dev")
    return origin, repo


def on_dev(repo: Path, subject: str, version: str | None = None) -> str:
    """Commit `subject` on `dev`, push it, and return its short SHA."""
    git(repo, "checkout", "-q", "dev")
    sha = commit(repo, subject, version)
    git(repo, "push", "-q", "origin", "dev")
    return sha


def run_prep(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the script in `repo`, as the release skill does."""
    return subprocess.run(  # noqa: S603 - runs the script under test.
        [sys.executable, str(SCRIPT), *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **IDENTITY},
    )


def output(result: subprocess.CompletedProcess[str]) -> str:
    """Return what the script printed, on both streams."""
    return result.stdout + result.stderr


def test_status_stops_on_a_hotfix_that_dev_lacks(tmp_path: Path) -> None:
    """A non-merge commit on `main` that `dev` lacks stops the release."""
    _, repo = released(tmp_path)
    on_dev(repo, "Add a step (#40)")
    git(repo, "checkout", "-q", "main")
    commit(repo, "Fix a typo on main")
    git(repo, "push", "-q", "origin", "main")
    result = run_prep(repo, "status")
    assert result.returncode != 0
    assert "hotfix" in output(result)
    assert "Fix a typo on main" in output(result)


def test_status_goes_on_past_release_merge_commits(tmp_path: Path) -> None:
    """The release merge commits on `main` are not hotfixes."""
    _, repo = released(tmp_path)
    on_dev(repo, "Add a step (#40)")
    result = run_prep(repo, "status")
    assert result.returncode == 0, output(result)
    assert "hotfix" not in output(result)


def test_status_has_nothing_to_release_after_a_release(tmp_path: Path) -> None:
    """`main` is `dev` plus the release merge commit: nothing to release."""
    _, repo = released(tmp_path)
    result = run_prep(repo, "status")
    assert result.returncode != 0
    assert "nothing to release" in output(result).lower()


def test_status_has_nothing_to_release_when_dev_is_main(tmp_path: Path) -> None:
    """`dev` at the same commit as `main`: nothing to release."""
    _, repo = released(tmp_path)
    git(repo, "push", "-q", "-f", "origin", "origin/main:refs/heads/dev")
    result = run_prep(repo, "status")
    assert result.returncode != 0
    assert "nothing to release" in output(result).lower()


def test_status_lists_the_prs_since_the_last_tag(tmp_path: Path) -> None:
    """One line per commit on `dev` since the tag, oldest first."""
    _, repo = released(tmp_path)
    on_dev(repo, "Add a step (#40)")
    sha = on_dev(repo, "Fix the grader")
    on_dev(repo, "Bump craft to 2.9.0 (#42)", version="2.9.0")
    result = run_prep(repo, "status")
    assert result.returncode == 0, output(result)
    lines = [line for line in result.stdout.splitlines() if line.startswith("- ")]
    assert lines == [
        "- #40 Add a step",
        f"- {sha} Fix the grader",
        "- #42 Bump craft to 2.9.0",
    ]
    assert "v2.8.2" in result.stdout
    assert "2.9.0" in result.stdout


def test_status_says_the_bump_is_done(tmp_path: Path) -> None:
    """A `dev` version above the last tag means the bump is done."""
    _, repo = released(tmp_path)
    on_dev(repo, "Add a step (#40)")
    assert "bump is done" not in run_prep(repo, "status").stdout
    on_dev(repo, "Bump craft to 2.9.0 (#41)", version="2.9.0")
    result = run_prep(repo, "status")
    assert result.returncode == 0, output(result)
    assert "bump is done" in result.stdout


@pytest.mark.parametrize(
    ("part", "version"),
    [("patch", "2.8.3"), ("minor", "2.9.0"), ("major", "3.0.0"), ("2.10.0", "2.10.0")],
)
def test_bump_pushes_a_branch_that_changes_only_the_version(
    tmp_path: Path, part: str, version: str
) -> None:
    """`bump` commits the new version on the named branch and pushes it."""
    origin, repo = released(tmp_path)
    on_dev(repo, "Add a step (#40)")
    result = run_prep(repo, "bump", part, "release-bump")
    assert result.returncode == 0, output(result)
    branch = "refs/heads/release-bump"
    assert git(origin, "log", "-1", "--format=%s", branch) == f"Bump craft to {version}"
    assert git(origin, "rev-parse", f"{branch}~1") == git(origin, "rev-parse", "dev")
    changed = git(origin, "diff", "--name-only", "dev", branch)
    assert changed == PLUGIN_JSON.as_posix()
    manifest = json.loads(git(origin, "show", f"{branch}:{PLUGIN_JSON.as_posix()}"))
    assert manifest == {"name": "craft", "version": version, "license": "UNLICENSED"}


@pytest.mark.parametrize("part", ["2.8.2", "2.8.1", "2.9", "banana"])
def test_bump_refuses_a_version_not_above_the_last_tag(
    tmp_path: Path, part: str
) -> None:
    """A version at or below the last tag, or not `X.Y.Z`, makes no branch."""
    origin, repo = released(tmp_path)
    on_dev(repo, "Add a step (#40)")
    result = run_prep(repo, "bump", part, "release-bump")
    assert result.returncode != 0
    assert part in output(result)
    assert not git(origin, "branch", "--list", "release-bump")


def test_bump_starts_from_the_highest_tag_on_origin(tmp_path: Path) -> None:
    """The last tag is the highest `vX.Y.Z` on `origin`, not the newest."""
    origin, repo = released(tmp_path)
    on_dev(repo, "Add a step (#40)")
    git(origin, "tag", "v2.10.0", "main")
    git(origin, "tag", "v2.9.0", "main")
    result = run_prep(repo, "bump", "patch", "release-bump")
    assert result.returncode == 0, output(result)
    subject = git(origin, "log", "-1", "--format=%s", "release-bump")
    assert subject == "Bump craft to 2.10.1"


def test_wait_tag_ends_when_the_tag_is_on_origin(tmp_path: Path) -> None:
    """The tag already exists: `wait-tag` exits zero at once."""
    _, repo = released(tmp_path)
    result = run_prep(repo, "wait-tag", "2.8.2")
    assert result.returncode == 0, output(result)
    assert "v2.8.2" in result.stdout


def test_wait_tag_gives_up_at_its_limit(tmp_path: Path) -> None:
    """No tag: `wait-tag` exits non-zero when the limit is reached."""
    _, repo = released(tmp_path)
    start = time.monotonic()
    result = run_prep(repo, "wait-tag", "2.9.0", "--timeout", "1", "--interval", "0.2")
    assert result.returncode != 0
    assert time.monotonic() - start < 5  # noqa: PLR2004 - "within a few seconds".
    assert "v2.9.0" in output(result)


def test_wait_tag_help_names_the_defaults(tmp_path: Path) -> None:
    """A check every 5 seconds, for up to 300 seconds."""
    result = run_prep(tmp_path, "wait-tag", "--help")
    assert result.returncode == 0, output(result)
    options = {
        line.split()[0]: line
        for line in result.stdout.splitlines()
        if line.strip().startswith("--")
    }
    assert "300 seconds" in options["--timeout"]
    assert "5 seconds" in options["--interval"]
