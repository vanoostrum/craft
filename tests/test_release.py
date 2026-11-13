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
ADR_0005 = ROOT / "docs" / "adr" / "0005-release-from-the-owners-message.md"
RELEASE_SKILL = ROOT / ".claude" / "skills" / "release" / "SKILL.md"
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
    """Bump on `dev`, merge into `main`, the workflow tags, check, note."""
    release = readme_section("Release")
    marks = [
        "plugin.json",
        "from `dev` to `main`",
        "`release` workflow",
        "`v<version>`",
        "git ls-remote --tags",
        "release note",
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
    hotfix = release.split("Hotfix", 1)[1]
    assert "tag it" not in hotfix
    assert "`release` workflow" in hotfix


def test_readme_release_starts_from_the_owners_message() -> None:
    """A "release" message starts the release skill and approves its merges."""
    release = readme_section("Release")
    assert '"release" message' in release
    assert "`.claude/skills/release/`" in release
    assert "docs/adr/0005" in release
    assert "Nobody tags by hand" in release


def release_skill() -> str:
    """Return the text of the repo's release skill."""
    return RELEASE_SKILL.read_text(encoding="utf-8")


def test_release_skill_is_named_and_says_when_to_use_it() -> None:
    """The skill loads by name, and its description names the message."""
    head = release_skill().split("---", 2)[1]
    assert "name: release" in head
    assert '"release"' in head


def test_release_skill_message_is_approval_for_both_merges() -> None:
    """The message approves the bump merge and the `dev` to `main` merge only."""
    text = release_skill()
    assert "approval" in text
    assert "bump PR" in text
    assert "`dev` to `main` PR" in text
    assert "merge commit" in text
    assert "required checks" in text


def test_release_skill_stops_and_asks_when_it_cannot_go_on() -> None:
    """Red checks, a conflict, an unmerged hotfix, or no tag stop the release."""
    stops = section(release_skill(), "Stop and ask")
    for case in ("check fails", "conflict", "hotfix", "tag"):
        assert case in stops, case


def test_release_skill_steps_are_in_order() -> None:
    """Pick the version, bump, merge into `main`, wait for the tag, note, check."""
    text = release_skill()
    marks = [
        "## Pick the version",
        "**Bump.**",
        "**Merge into `main`.**",
        "**Tag.**",
        "/mnt/project-files/releases/craft-v<version>.md",
        "**Check the account.**",
    ]
    places = [text.find(mark) for mark in marks]
    assert -1 not in places, dict(zip(marks, places, strict=True))
    assert places == sorted(places)


def test_adr_0005_records_the_message_as_approval() -> None:
    """ADR 0005 says why a release needs no merge or tag by the owner."""
    adr = ADR_0005.read_text(encoding="utf-8")
    assert "GITHUB_TOKEN" in adr
    assert '"release"' in adr
    assert "approval" in adr


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
