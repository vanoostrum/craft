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
ADR_0006 = ROOT / "docs" / "adr" / "0006-release-prs-auto-merge.md"
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
    """Bump on `dev`, auto-merge into `main`, the workflow tags, wait, note."""
    release = readme_section("Release")
    marks = [
        "release_prep.py status",
        "plugin.json",
        "squash auto-merge",
        "from `dev` to `main`",
        "`release` workflow",
        "`v<version>`",
        "release_prep.py wait-tag",
        "new thread",
    ]
    places = [release.find(mark) for mark in marks]
    assert -1 not in places, dict(zip(marks, places, strict=True))
    assert places == sorted(places)
    assert "pyproject.toml" in release
    assert "merge commit" in release
    assert "release note" in release
    assert "docs/adr/0006" in release
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
    """Pick the version, bump, merge into `main`, note while CI runs, tag, reply."""
    text = release_skill()
    marks = [
        "## Pick the version",
        "**Bump.**",
        "**Wait for `dev`.**",
        "**Merge into `main`.**",
        "**Release note.**",
        "**Tag.**",
        "**Reply.**",
    ]
    places = [text.find(mark) for mark in marks]
    assert -1 not in places, dict(zip(marks, places, strict=True))
    assert places == sorted(places)


def step(heading: str) -> str:
    """Return one numbered step of the release skill, up to the next one."""
    steps = section(release_skill(), "Steps")
    start = steps.index(f"**{heading}.**")
    following = re.search(r"\n\d\. \*\*", steps[start:])
    return steps[start : start + following.start()] if following else steps[start:]


def test_release_skill_auto_merges_the_bump_pr_and_waits_for_its_event() -> None:
    """Squash auto-merge on the bump PR, then end the turn until it merges."""
    bump = step("Bump")
    assert "auto-merge with squash" in bump
    wait = step("Wait for `dev`")
    assert "end the turn" in wait
    assert "merge event" in wait
    assert "failed check" in wait
    assert "**Stop and ask**" in wait


def test_release_skill_waits_for_the_tag_in_the_same_turn() -> None:
    """Merge-commit auto-merge on the `dev` to `main` PR, then `wait-tag` in turn."""
    merge = step("Merge into `main`")
    assert "auto-merge with a merge commit" in merge
    assert "after the bump pr merged" in merge.lower()
    tag = step("Tag")
    assert "release_prep.py wait-tag <version>" in tag
    assert "same turn" in tag
    assert "Do not end the turn" in tag


def test_release_skill_names_the_auto_merge_fallback() -> None:
    """A refusal by GitHub or the session falls back to merge on green checks."""
    fallback = section(release_skill(), "Auto-merge")
    assert "GitHub or the session refuses" in fallback
    assert "wait for green required checks, then merge" in fallback
    assert "docs/adr/0005" in fallback
    assert "fallback" in step("Reply")


def test_release_skill_uses_the_script_instead_of_project_verify() -> None:
    """`release_prep.py` does the start checks and the bump; no local verify."""
    text = release_skill()
    assert "release_prep.py status" in section(text, "Check the start")
    assert "The bump is done" in section(text, "Check the start")
    assert "skip step 1" in section(text, "Check the start")
    bump = step("Bump")
    assert "release_prep.py bump" in bump
    assert "Do not run `project-verify`" in bump
    assert "Run the `project-verify` skill" not in text


def test_release_skill_names_one_reason_when_the_tag_wait_fails() -> None:
    """A failed check, an unmerged PR, or a merged PR without a tag."""
    tag = step("Tag")
    reasons = tag.split("When `wait-tag` fails", 1)[1]
    assert "A check failed: name that check" in reasons
    assert "did not merge and no check failed" in reasons
    assert "state of each check" in reasons
    assert "auto-merge is still on" in reasons
    assert "The PR merged: give the `release` workflow run link" in reasons


def test_release_skill_writes_the_note_while_ci_runs() -> None:
    """The note is written before the tag wait, and gets the time after it."""
    note = step("Release note")
    assert "While CI runs on the `dev` to `main` PR" in note
    assert "/mnt/project-files/releases/craft-v<version>.md" in note
    assert "add the release time to the note" in step("Tag")
    assert "owner's message" in step("Tag")


def test_release_skill_has_no_account_step() -> None:
    """The reply asks for a check in a new thread instead."""
    text = release_skill()
    head = text.split("---", 2)[1]
    assert "account" not in head
    assert "Check the account" not in text
    assert "new thread" in step("Reply")


def test_release_skill_turns_off_auto_merge_on_every_stop() -> None:
    """A stop leaves no release PR that merges on a later push."""
    stops = section(release_skill(), "Stop and ask")
    assert "On every stop, turn off auto-merge on each open release PR" in stops
    assert "say so in the reply" in stops


def test_release_skill_reuses_an_open_dev_to_main_pr() -> None:
    """An open `dev` to `main` PR is used, not doubled."""
    start = section(release_skill(), "Check the start")
    assert "already open" in start
    assert "do not open a second one" in start
    assert "or use the open one" in step("Merge into `main`")


def test_release_skill_names_both_merges_in_its_first_message() -> None:
    """The first message names the action the owner's message approves."""
    text = release_skill()
    assert "merge the two release PRs, with auto-merge where GitHub allows it" in text


def test_adr_0006_records_auto_merge_on_release_prs() -> None:
    """ADR 0006 says why release PRs auto-merge, and how a stop ends it."""
    adr = ADR_0006.read_text(encoding="utf-8")
    assert adr.startswith("# Release PRs use auto-merge")
    assert "squash" in adr
    assert "merge commit" in adr
    assert "ADR 0005" in adr
    assert "turns off auto-merge" in adr
    assert "docs/adr/0006" in release_skill()


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
