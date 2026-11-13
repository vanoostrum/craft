# Copyright (C) 2026 Theo van Oostrum
"""Tag `main` as `v<version>` from the craft `plugin.json`, once per version.

Usage: `python3 .github/scripts/release_tag.py`, in a checkout of `main`.

It reads `version` from `plugins/craft/.claude-plugin/plugin.json`. When
`origin` has no tag `v<version>`, it tags `HEAD` and pushes the tag. When the
tag exists, it leaves it as it is: the tag stays on the commit that released
that version, also after a later merge without a bump. A version that is not
`X.Y.Z` fails without a tag.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

PLUGIN_JSON = Path("plugins/craft/.claude-plugin/plugin.json")
SEMVER = re.compile(r"\d+\.\d+\.\d+")


def git(*args: str) -> str:
    """Run git and return its output."""
    return subprocess.run(  # noqa: S603 - fixed git commands on the checkout.
        ["git", *args],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> int:
    """Tag `HEAD` with the plugin version, unless that tag exists."""
    version = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))["version"]
    if not SEMVER.fullmatch(version):
        print(f"{PLUGIN_JSON} has version {version!r}, not X.Y.Z. No tag.")  # noqa: T201
        return 1
    tag = f"v{version}"
    if git("ls-remote", "--tags", "origin", f"refs/tags/{tag}"):
        print(f"{tag} already exists. No new tag.")  # noqa: T201
        return 0
    git("tag", tag, "HEAD")
    git("push", "origin", f"refs/tags/{tag}")
    print(f"Tagged {git('rev-parse', 'HEAD')} as {tag}.")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
