# Copyright (C) 2026 Theo van Oostrum
"""Do the fixed local steps of a craft release.

Usage: `python3 .claude/skills/release/scripts/release_prep.py <command>`, in a
checkout of the craft repo. It uses only `git`. The GitHub calls stay with the
agent that runs the release skill.

- `status`: the start checks, the last tag, the `dev` version, and the PRs.
- `bump <patch|minor|major|X.Y.Z> <branch>`: the bump commit, pushed.
- `wait-tag <version>`: wait until `origin` has the tag `v<version>`.

The last tag is the highest `vX.Y.Z` tag on `origin`.
"""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

PLUGIN_JSON = Path("plugins/craft/.claude-plugin/plugin.json")
SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")
TAG_REF = re.compile(r"refs/tags/v(\d+\.\d+\.\d+)")
PR_SUFFIX = re.compile(r"^(?P<subject>.*) \(#(?P<number>\d+)\)$")

type Version = tuple[int, int, int]


class ReleaseStopError(Exception):
    """A check that stops the release, with the reason for the owner."""


def git(*args: str) -> str:
    """Run git and return its output."""
    return subprocess.run(  # noqa: S603 - fixed git commands on the checkout.
        ["git", *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def parse(version: str) -> Version | None:
    """Return `version` as numbers, or None when it is not `X.Y.Z`."""
    match = SEMVER.fullmatch(version)
    if not match:
        return None
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def show(version: Version) -> str:
    """Return `version` as `X.Y.Z`."""
    return ".".join(str(part) for part in version)


def fetch() -> None:
    """Fetch `main`, `dev`, and the tags from `origin`."""
    git(
        "fetch",
        "-q",
        "--tags",
        "origin",
        "+refs/heads/main:refs/remotes/origin/main",
        "+refs/heads/dev:refs/remotes/origin/dev",
    )


def last_tag() -> Version:
    """Return the highest `vX.Y.Z` tag on `origin`."""
    refs = git("ls-remote", "--tags", "origin", "refs/tags/v*").splitlines()
    versions = [
        version
        for ref in refs
        if (match := TAG_REF.fullmatch(ref.split()[-1]))
        and (version := parse(match[1]))
    ]
    if not versions:
        message = "origin has no vX.Y.Z tag."
        raise ReleaseStopError(message)
    return max(versions)


def dev_version() -> str:
    """Return `version` from `plugin.json` on `origin/dev`."""
    manifest = git("show", f"origin/dev:{PLUGIN_JSON.as_posix()}")
    return json.loads(manifest)["version"]


def pr_line(sha: str, subject: str) -> str:
    """Return the line of one commit in the PR list."""
    match = PR_SUFFIX.match(subject)
    if match:
        return f"- #{match['number']} {match['subject']}"
    return f"- {sha} {subject}"


def status() -> None:
    """Print the release state, or stop when there is no release to make."""
    fetch()
    hotfixes = git("log", "--no-merges", "--format=%h %s", "origin/dev..origin/main")
    if hotfixes:
        message = (
            "main has a hotfix that is not merged back into dev:\n"
            f"{hotfixes}\nMerge main into dev first."
        )
        raise ReleaseStopError(message)
    if not git("rev-list", "origin/main..origin/dev"):
        message = "Nothing to release: dev has no commit that main lacks."
        raise ReleaseStopError(message)
    tag = last_tag()
    version = dev_version()
    print(f"Last tag: v{show(tag)}")  # noqa: T201
    print(f"Version on dev: {version}")  # noqa: T201
    if (parse(version) or (0, 0, 0)) > tag:
        print(f"The bump is done: dev is at {version}, above v{show(tag)}.")  # noqa: T201
    print("PRs since the last tag:")  # noqa: T201
    commits = git(
        "log",
        "--first-parent",
        "--reverse",
        "--format=%h%x00%s",
        f"v{show(tag)}..origin/dev",
    )
    for line in commits.splitlines():
        sha, subject = line.split("\0", 1)
        print(pr_line(sha, subject))  # noqa: T201


def next_version(tag: Version, part: str) -> Version:
    """Return the version that `part` names, above `tag`."""
    major, minor, patch = tag
    if part == "major":
        return major + 1, 0, 0
    if part == "minor":
        return major, minor + 1, 0
    if part == "patch":
        return major, minor, patch + 1
    version = parse(part)
    if version is None:
        message = f"{part!r} is not X.Y.Z, patch, minor, or major."
        raise ReleaseStopError(message)
    if version <= tag:
        message = f"{part} is not above the last tag v{show(tag)}."
        raise ReleaseStopError(message)
    return version


def bump(part: str, branch: str) -> None:
    """Commit the new version on `branch` from `origin/dev`, and push it."""
    fetch()
    version = show(next_version(last_tag(), part))
    git("switch", "-q", "-C", branch, "origin/dev")
    text = PLUGIN_JSON.read_text(encoding="utf-8")
    new_text = re.sub(
        r'("version":\s*")[^"]*(")', rf"\g<1>{version}\g<2>", text, count=1
    )
    PLUGIN_JSON.write_text(new_text, encoding="utf-8")
    git("commit", "-q", "-m", f"Bump craft to {version}", "--", str(PLUGIN_JSON))
    git("push", "-q", "-u", "origin", branch)
    print(f"Pushed {branch} with version {version}.")  # noqa: T201


def wait_tag(version: str, timeout: float, interval: float) -> None:
    """Wait until `origin` has the tag `v<version>`."""
    tag = f"v{version}"
    deadline = time.monotonic() + timeout
    while True:
        if git("ls-remote", "--tags", "origin", f"refs/tags/{tag}"):
            print(f"origin has {tag}.")  # noqa: T201
            return
        if time.monotonic() >= deadline:
            message = f"origin has no {tag} after {timeout:g} seconds."
            raise ReleaseStopError(message)
        time.sleep(interval)


def arguments() -> argparse.Namespace:
    """Parse the command line."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="check the start and list the PRs")
    bump_command = commands.add_parser("bump", help="push the bump commit")
    bump_command.add_argument("part", help="patch, minor, major, or X.Y.Z")
    bump_command.add_argument("branch", help="the branch to push")
    wait = commands.add_parser("wait-tag", help="wait for the release tag")
    wait.add_argument("version", help="the version, as X.Y.Z")
    wait.add_argument(
        "--timeout", type=float, default=300, help="limit (default: 300 seconds)"
    )
    wait.add_argument(
        "--interval", type=float, default=5, help="wait (default: 5 seconds)"
    )
    return parser.parse_args()


def main() -> int:
    """Run one command."""
    args = arguments()
    try:
        if args.command == "status":
            status()
        elif args.command == "bump":
            bump(args.part, args.branch)
        else:
            wait_tag(args.version, args.timeout, args.interval)
    except ReleaseStopError as stop:
        print(stop, file=sys.stderr)  # noqa: T201
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
