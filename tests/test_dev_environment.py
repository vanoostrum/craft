# Copyright (C) 2026 Theo van Oostrum
"""The walking skeleton: craft's own verify skill, app driver, and config."""

import json
import re
from pathlib import Path
from typing import Any

import yaml

from tests.test_brainstorm import section
from tests.test_ci import check_steps

ROOT = Path(__file__).resolve().parents[1]
REPO_SKILLS = ROOT / ".claude" / "skills"
EVALS = ROOT / "plugins" / "craft" / "evals"
HOOKS = ROOT / "plugins" / "craft" / "hooks" / "hooks.json"
CASES = sorted(p.parent.name for p in EVALS.glob("*/prompt.md"))
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def repo_skill(name: str) -> str:
    """Return the text of a project skill in `.claude/skills/`."""
    return (REPO_SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def frontmatter(path: Path) -> dict[str, Any]:
    """Return the YAML frontmatter of a markdown file."""
    match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
    assert match, f"{path} has no frontmatter"
    return yaml.safe_load(match.group(1))


def test_project_verify_runs_the_checks_in_ci_order() -> None:
    """`project-verify` installs, then runs each `checks` command in the same order."""
    text = repo_skill("project-verify")
    commands = check_steps()
    assert commands[0] == "uv sync --frozen"
    positions = [text.find(f"\n{command}\n") for command in commands]
    assert -1 not in positions, "a checks command is missing from project-verify"
    assert positions == sorted(positions)


def test_project_verify_names_the_step_that_failed() -> None:
    """A failed check is reported by name, not as a pass."""
    assert "name the step that failed" in repo_skill("project-verify")


def test_verify_runs_the_suite_without_uploads() -> None:
    """`verify` runs the agreed command with the upload hook off, and passes --case."""
    text = repo_skill("verify")
    assert "env -u CRAFT_GCS_BUCKET \\\n  claude plugin eval" in text
    assert (
        "claude plugin eval plugins/craft --trust-plugin --no-publish "
        "--ablation none --runs 1"
    ) in text
    assert "--case <glob>" in text
    assert "plugins/craft/evals/results/" in text


def test_verify_maps_every_case_and_every_uncovered_hook() -> None:
    """The feature map names each smoke case, and lists the hooks no case covers."""
    feature_map = section(repo_skill("verify"), "Feature map")
    assert CASES
    for case in CASES:
        assert f"`{case}`" in feature_map
    hooks = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]
    scripts = {
        Path(hook["command"].split('"')[-2]).name
        for entries in hooks.values()
        for entry in entries
        for hook in entry["hooks"]
    }
    uncovered = feature_map.split("Not covered", 1)[1]
    for script in scripts:
        assert f"`{script}`" in uncovered


def test_verify_says_how_to_try_a_step_by_hand() -> None:
    """A step can be tried by hand on the branch's plugin."""
    assert "claude --plugin-dir plugins/craft" in repo_skill("verify")


def test_verify_names_the_cli_version_of_ci() -> None:
    """The skill names the Claude Code version that CI pins."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    version = re.search(r"@anthropic-ai/claude-code@([\d.]+)", ci)
    assert version
    assert f"`{version.group(1)}`" in repo_skill("verify")


def test_each_smoke_case_has_a_prompt_and_a_grader_and_no_bash() -> None:
    """Each case has a prompt and a grader, and cannot reach Bash, Linear, or GitHub."""
    for case in CASES:
        prompt = EVALS / case / "prompt.md"
        meta = frontmatter(prompt)
        assert FRONTMATTER.sub("", prompt.read_text(encoding="utf-8")).strip()
        assert set(meta["allowed_tools"]) <= {"Read", "Glob", "Grep", "Skill"}
        graders = list((EVALS / case / "graders").glob("*.md"))
        assert graders, f"{case} has no grader"
        assert sum(frontmatter(g)["type"] == "llm" for g in graders) <= 1


def test_the_results_folder_is_ignored() -> None:
    """Eval results never show in `git status`."""
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "plugins/craft/evals/results/" in ignored


def test_the_plugin_is_version_2_5_0() -> None:
    """The release that stops setup from starting plan is 2.5.0."""
    manifest = ROOT / "plugins" / "craft" / ".claude-plugin" / "plugin.json"
    assert json.loads(manifest.read_text(encoding="utf-8"))["version"] == "2.5.0"


def test_craft_config_has_the_final_values() -> None:
    """Craft's own config names its checks and skills."""
    config = (ROOT / ".claude" / "craft.md").read_text(encoding="utf-8")
    assert "| Required CI checks | `checks`, `evals` |" in config
    assert "| Verify skill | `project-verify` |" in config
    assert "| App driver skill | `verify` |" in config


def test_claude_md_and_readme_point_to_the_skills() -> None:
    """`CLAUDE.md` and the README Development section name the two skills."""
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    development = section(
        (ROOT / "README.md").read_text(encoding="utf-8"), "Development"
    )
    for name in ("project-verify", "verify"):
        assert f"`{name}`" in claude
        assert f"`{name}`" in development
    assert "uv run ruff" not in development
