# Copyright (C) 2026 Theo van Oostrum
"""The marketplace pins craft to a release tag, and the README says how to release."""

import json
import re
from pathlib import Path
from typing import Any

import pytest

from tests.test_brainstorm import section

ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
PLUGIN = ROOT / "plugins" / "craft" / ".claude-plugin" / "plugin.json"
README = ROOT / "README.md"
ADR_0003 = ROOT / "docs" / "adr" / "0003-pin-craft-to-a-release-tag.md"
TAG = re.compile(r"^v\d+\.\d+\.\d+$")

type Entry = dict[str, Any]


def load(path: Path) -> Entry:
    """Return the JSON object in `path`."""
    return json.loads(path.read_text(encoding="utf-8"))


def entry(marketplace: Entry, name: str) -> Entry:
    """Return the plugin entry called `name` in the marketplace."""
    return next(plugin for plugin in marketplace["plugins"] if plugin["name"] == name)


def pin_problems(marketplace: Entry) -> list[str]:
    """Return what is wrong with the craft pin, or nothing when it is a release tag.

    It does not compare `ref` with the `version` in `plugin.json`: between a
    version bump and the ref-bump PR, `main` is ahead of the release on purpose.
    """
    source = entry(marketplace, "craft")["source"]
    if not isinstance(source, dict):
        return [f"craft source is a local path: {source!r}"]
    expected = {
        "source": "git-subdir",
        "url": "vanoostrum/craft",
        "path": "plugins/craft",
    }
    problems = [
        f"{key} is {source.get(key)!r}, not {value!r}"
        for key, value in expected.items()
        if source.get(key) != value
    ]
    if not TAG.match(str(source.get("ref", ""))):
        problems.append(f"ref {source.get('ref')!r} is not a vX.Y.Z tag")
    return problems


def test_craft_is_pinned_to_a_release_tag() -> None:
    """The craft entry is a git-subdir source on this repo, at a vX.Y.Z tag."""
    assert pin_problems(load(MARKETPLACE)) == []


def test_craft_keeps_its_name_and_description() -> None:
    """Only the source of the craft entry changes."""
    craft = entry(load(MARKETPLACE), "craft")
    assert craft["description"] == "The craft steps, rules, and hooks."


GOOD_SOURCE = {
    "source": "git-subdir",
    "url": "vanoostrum/craft",
    "path": "plugins/craft",
    "ref": "v2.4.0",
}


def with_source(**changes: str) -> Entry:
    """Return a marketplace whose craft source is a good pin with `changes`."""
    return {"plugins": [{"name": "craft", "source": GOOD_SOURCE | changes}]}


@pytest.mark.parametrize(
    "marketplace",
    [
        pytest.param(
            {"plugins": [{"name": "craft", "source": "./plugins/craft"}]},
            id="local path",
        ),
        pytest.param(with_source(url="someone/craft"), id="other url"),
        pytest.param(with_source(path="plugins/other"), id="other path"),
        pytest.param(with_source(ref="main"), id="branch ref"),
        pytest.param(with_source(ref="2.4.0"), id="ref without v"),
        pytest.param(with_source(source="github"), id="other source type"),
    ],
)
def test_pin_check_fails_on_a_bad_pin(marketplace: Entry) -> None:
    """The check catches each way the pin can go wrong."""
    assert pin_problems(marketplace) != []


def test_pin_check_passes_when_main_is_ahead_of_ref() -> None:
    """A newer `version` in `plugin.json` than `ref` keeps CI green."""
    version = load(PLUGIN)["version"]
    marketplace = with_source(ref="v0.1.0")
    assert version != "0.1.0"
    assert pin_problems(marketplace) == []


def test_pstack_stays_pinned_to_its_tag() -> None:
    """The pstack entry keeps its source, at a vX.Y.Z tag that VENDORED.md bumps."""
    source = entry(load(MARKETPLACE), "pstack")["source"]
    assert source["source"] == "git-subdir"
    assert source["url"] == "michael-denyer/pstack-claude"
    assert source["path"] == "plugins/pstack"
    assert TAG.match(source["ref"])


def readme_section(heading: str) -> str:
    """Return a `##` section of the README."""
    return section(README.read_text(encoding="utf-8"), heading)


def test_readme_release_steps_are_in_order() -> None:
    """Bump the version, tag main, check the tag, then bump `ref`."""
    release = readme_section("Release")
    marks = ["plugin.json", "`v<version>`", "git ls-remote --tags", "marketplace.json"]
    places = [release.find(mark) for mark in marks]
    assert -1 not in places, dict(zip(marks, places, strict=True))
    assert places == sorted(places)
    assert "`ref`" in release[places[-1] :]
    assert "pyproject.toml" in release


def test_readme_release_has_a_rollback_line() -> None:
    """A bad release goes back to the last good tag, or by hand per ADR 0002."""
    release = readme_section("Release")
    assert "last good tag" in release
    assert "docs/adr/0002" in release
    assert "./plugins/craft" in release


def test_readme_development_does_not_say_how_to_release() -> None:
    """The release steps live only in the Release section."""
    assert "release" not in readme_section("Development").lower()


def test_readme_install_names_only_the_account_plugin() -> None:
    """Install points to the account plugin, at the tag that `ref` names."""
    install = readme_section("Install")
    assert "account" in install
    assert "`ref`" in install
    assert "extraKnownMarketplaces" not in install
    assert ".claude/settings.json" not in install


def test_adr_0003_says_craft_is_only_an_account_plugin() -> None:
    """The ADR drops terminal pins for the owner's 2026-11-11 decision."""
    adr = ADR_0003.read_text(encoding="utf-8")
    assert "Terminal sessions keep pinning a tag" not in adr
    assert "Craft is installed only as an account plugin" in adr
