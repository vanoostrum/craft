# Copyright (C) 2026 Theo van Oostrum
"""A push to `main` tags it `v<version>` from `plugin.json`, once per version.

Each test runs `release_tag.py` as the `release` workflow does, in a clone of a
temporary bare repo that stands in for GitHub.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

from tests.test_evals_gate import git

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".github" / "scripts" / "release_tag.py"
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"
PLUGIN_JSON = Path("plugins") / "craft" / ".claude-plugin" / "plugin.json"


def commit_version(repo: Path, version: str) -> str:
    """Commit `plugin.json` at `version`, push it, and return the commit SHA."""
    path = repo / PLUGIN_JSON
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"name": "craft", "version": version}), "utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "--allow-empty", "-m", f"craft {version}")
    git(repo, "push", "-q", "origin", "main")
    return git(repo, "rev-parse", "HEAD")


def clone(tmp_path: Path) -> tuple[Path, Path]:
    """Return a bare `origin` with an empty `main`, and a clone of it."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    repo = tmp_path / "repo"
    git(tmp_path, "clone", "-q", str(origin), str(repo))
    git(repo, "checkout", "-q", "-b", "main")
    return origin, repo


def run_script(repo: Path) -> subprocess.CompletedProcess[str]:
    """Run the script in `repo`, as the workflow step does."""
    return subprocess.run(  # noqa: S603 - runs the script under test.
        [sys.executable, str(SCRIPT)],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def remote_tag(origin: Path, tag: str) -> str:
    """Return the commit that `tag` points to on `origin`, or ''."""
    return git(origin, "rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}")


def test_a_new_version_tags_main_and_pushes_the_tag(tmp_path: Path) -> None:
    """The first push of a version creates `v<version>` on that commit."""
    origin, repo = clone(tmp_path)
    head = commit_version(repo, "2.7.0")
    result = run_script(repo)
    assert result.returncode == 0, result.stderr
    assert remote_tag(origin, "v2.7.0") == head
    assert "v2.7.0" in result.stdout


def test_a_push_without_a_bump_keeps_the_tag(tmp_path: Path) -> None:
    """A later push at the same version leaves the tag on the release commit."""
    origin, repo = clone(tmp_path)
    release = commit_version(repo, "2.7.0")
    assert run_script(repo).returncode == 0
    commit_version(repo, "2.7.0")
    result = run_script(repo)
    assert result.returncode == 0, result.stderr
    assert remote_tag(origin, "v2.7.0") == release
    assert "already" in result.stdout


def test_the_next_version_gets_its_own_tag(tmp_path: Path) -> None:
    """Each version gets one tag, on the commit that first had it on `main`."""
    origin, repo = clone(tmp_path)
    first = commit_version(repo, "2.7.0")
    assert run_script(repo).returncode == 0
    second = commit_version(repo, "2.7.1")
    assert run_script(repo).returncode == 0
    assert remote_tag(origin, "v2.7.0") == first
    assert remote_tag(origin, "v2.7.1") == second


def test_a_version_that_is_not_semver_fails(tmp_path: Path) -> None:
    """A version such as `2.7` makes no tag and fails the job."""
    origin, repo = clone(tmp_path)
    commit_version(repo, "2.7")
    result = run_script(repo)
    assert result.returncode != 0
    assert "2.7" in result.stdout + result.stderr
    assert git(origin, "tag", "--list") == ""


def release_workflow() -> dict[Any, Any]:
    """Return the parsed release workflow."""
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_the_workflow_runs_on_pushes_to_main_with_write_access() -> None:
    """Only `main` gets tags, with the built-in token and no other secret."""
    flow = release_workflow()
    assert flow["on"] == {"push": {"branches": ["main"]}}
    assert flow["permissions"] == {"contents": "write"}
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "secrets." not in text
    assert "PAT" not in text


def test_the_workflow_fetches_tags_and_runs_the_script() -> None:
    """The checkout has the tags, so the script can see an existing tag."""
    steps = release_workflow()["jobs"]["tag"]["steps"]
    checkout = next(s for s in steps if str(s.get("uses", "")).startswith("actions/"))
    assert checkout["with"]["fetch-depth"] == 0
    assert any(
        "python3 .github/scripts/release_tag.py" in str(s.get("run", "")) for s in steps
    )
