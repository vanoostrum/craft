# Copyright (C) 2026 Theo van Oostrum
"""`main` holds releases, `dev` takes the work, and the README says how to release."""

import json
import re
from pathlib import Path
from typing import Any

import yaml

from tests.test_brainstorm import section

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
README = ROOT / "README.md"
CRAFT_CONFIG = ROOT / ".claude" / "craft.md"
CI = ROOT / ".github" / "workflows" / "ci.yml"
ADR_0003 = ROOT / "docs" / "adr" / "0003-pin-craft-to-a-release-tag.md"
ADR_0004 = ROOT / "docs" / "adr" / "0004-main-is-the-release-branch.md"
TAG = re.compile(r"^v\d+\.\d+\.\d+$")

type Entry = dict[str, Any]


def entry(name: str) -> Entry:
    """Return the plugin entry called `name` in the marketplace."""
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    return next(plugin for plugin in marketplace["plugins"] if plugin["name"] == name)


def test_craft_source_is_the_local_path() -> None:
    """claude.ai syncs craft only from a local path on `main` (ADR 0004)."""
    craft = entry("craft")
    assert craft["source"] == "./plugins/craft"
    assert craft["description"] == "The craft steps, rules, and hooks."


def test_pstack_stays_pinned_to_its_tag() -> None:
    """The pstack entry keeps its source, at a vX.Y.Z tag that VENDORED.md bumps."""
    source = entry("pstack")["source"]
    assert source["source"] == "git-subdir"
    assert source["url"] == "michael-denyer/pstack-claude"
    assert source["path"] == "plugins/pstack"
    assert TAG.match(source["ref"])


def test_craft_prs_target_dev() -> None:
    """Craft steps open their PRs on `dev`, so a merge does not reach the projects."""
    assert "| Base branch | `dev` |" in CRAFT_CONFIG.read_text(encoding="utf-8")


def test_ci_runs_on_pushes_to_main_and_dev() -> None:
    """Both long-lived branches get the `checks` job on every push."""
    workflow = yaml.safe_load(CI.read_text(encoding="utf-8"))
    assert set(workflow["on"]["push"]["branches"]) == {"main", "dev"}


def readme_section(heading: str) -> str:
    """Return a `##` section of the README."""
    return section(README.read_text(encoding="utf-8"), heading)


def test_readme_release_steps_are_in_order() -> None:
    """Bump the version on `dev`, merge `dev` into `main`, tag, check the tag."""
    release = readme_section("Release")
    marks = [
        "plugin.json",
        "from `dev` to `main`",
        "`v<version>`",
        "git ls-remote --tags",
    ]
    places = [release.find(mark) for mark in marks]
    assert -1 not in places, dict(zip(marks, places, strict=True))
    assert places == sorted(places)
    assert "pyproject.toml" in release
    assert "merge commit" in release
    assert "ref" not in release


def test_readme_release_has_rollback_and_hotfix_lines() -> None:
    """A bad release goes back to the last good tag; a hotfix goes back into `dev`."""
    release = readme_section("Release")
    assert "last good tag" in release
    assert "docs/adr/0002" in release
    assert "Hotfix" in release
    assert "back into `dev`" in release


def test_readme_development_does_not_say_how_to_release() -> None:
    """The release steps live only in the Release section."""
    assert "release" not in readme_section("Development").lower()


def test_readme_install_names_only_the_account_plugin() -> None:
    """Install points to the account plugin, which runs the craft on `main`."""
    install = readme_section("Install")
    assert "account" in install
    assert "`main`" in install
    assert "`ref`" not in install
    assert "extraKnownMarketplaces" not in install
    assert ".claude/settings.json" not in install


def test_adr_0004_replaces_the_tag_pin() -> None:
    """ADR 0004 records why the pin went, and ADR 0003 points to it."""
    adr = ADR_0004.read_text(encoding="utf-8")
    assert "`dev`" in adr
    assert "git-subdir" in adr
    assert "Craft is installed only as an account plugin" in adr
    assert "Superseded by `docs/adr/0004`" in ADR_0003.read_text(encoding="utf-8")
