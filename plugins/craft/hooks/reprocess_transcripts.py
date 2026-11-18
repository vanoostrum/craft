# Copyright (C) 2026 Theo van Oostrum
"""Re-process: rebuild `metadata.json` of the stored sessions in the bucket.

Run it from a checkout of the craft repo that has the release tags:

    git fetch --tags
    uv run python plugins/craft/hooks/reprocess_transcripts.py [--dry-run]

It signs in to Google Cloud as the upload hook does: `CRAFT_GCS_BUCKET` names
the bucket, and `CRAFT_GCS_KEY` or the cloud proxy's token signs in.

A session is a folder `<path>/sessions/<id>/` in the bucket. The command
rebuilds the `metadata.json` of each session that has a segment without one of
the ADR 0005 fields: `craft_version`, `model`, `work_seconds`, `wait_seconds`,
and `brief`. It leaves the other sessions alone, so a second run writes
nothing. The rebuild uses the upload hook's own code on the session's
transcripts in the bucket, so the hook and the command compute the same
segments. It keeps `repo`, `branch`, `session_id`, `event`, and `uploaded_at`
of the old `metadata.json`, and takes the branch's ticket from that branch. It
writes only `metadata.json`.

A new segment keeps the `craft_version` of the old segment with the same step
and start, when that is a string. Otherwise it gets the version of the latest
release at or before the session's start, when no release falls after the
start and at or before the segment's end; else null. A release is a tag
`v<x>.<y>.<z>` in the current git repo, at the committer time of its commit.
The session's start is the time of its earliest timestamped line.

The command prints one line per session: its path and `rebuilt`, `up to date`,
or `failed: <reason>`, and then the counts. A failed session is not written.
The exit status is 1 when a session failed, else 0. `--dry-run` prints the same
report and writes nothing.
"""

import gzip
import json
import re
import subprocess
import sys
import tempfile
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import upload_transcripts as hook

DRY_RUN = "--dry-run"
NEW_FIELDS = ("craft_version", "model", "work_seconds", "wait_seconds", "brief")
RELEASE_TAG = re.compile(r"^v(\d+\.\d+\.\d+)$")
SESSION_OBJECT = re.compile(r"^gs://[^/]+/(?P<session>.+/sessions/[^/]+)/(?P<name>.+)$")
METADATA = "metadata.json"
MAIN = "session.jsonl.gz"


@dataclass(frozen=True)
class Release:
    """A craft release: its version and its release time."""

    version: str
    time: datetime


class SessionFailedError(Exception):
    """A session that cannot be rebuilt; the message is the reason."""


def releases(cwd: str) -> list[Release]:
    """Return the release tags of the git repo at `cwd`, with their times."""
    found = []
    for tag in hook.git(cwd, "tag", "--list", "v*").splitlines():
        match = RELEASE_TAG.match(tag)
        if match is None:
            continue
        seconds = hook.git(cwd, "log", "-1", "--format=%ct", f"{tag}^{{commit}}")
        if seconds.isdigit():
            found.append(
                Release(match.group(1), datetime.fromtimestamp(int(seconds), UTC))
            )
    return found


def moment(stamp: object) -> datetime | None:
    """Return a transcript timestamp as a time, or None when it is none."""
    if not isinstance(stamp, str):
        return None
    try:
        return datetime.fromisoformat(stamp)
    except ValueError:
        return None


def release_version(
    known: list[Release], start: datetime | None, end: datetime | None
) -> str | None:
    """Return the version of the release that ran from `start` to `end`, if one did.

    That is the latest release at or before `start`, when no release falls after
    `start` and at or before `end`.
    """
    if start is None:
        return None
    end = end or start
    before = [release for release in known if release.time <= start]
    if not before or any(start < release.time <= end for release in known):
        return None
    return max(before, key=lambda release: release.time).version


def up_to_date(old: dict[str, Any]) -> bool:
    """Return whether each segment has all ADR 0005 fields."""
    return all(
        isinstance(segment, dict) and all(name in segment for name in NEW_FIELDS)
        for segment in old["segments"]
    )


def recorded_versions(old: dict[str, Any]) -> dict[tuple[object, object], str]:
    """Return the string `craft_version` of each old segment, by step and start."""
    return {
        (segment.get("step"), segment.get("started_at")): segment["craft_version"]
        for segment in old["segments"]
        if isinstance(segment, dict) and isinstance(segment.get("craft_version"), str)
    }


def unpack(download: Path, names: set[str], transcript: Path) -> None:
    """Unzip the session's transcripts where the hook's code looks for them."""
    folder = transcript.with_suffix("")
    for name in sorted(names):
        if name != MAIN and not (
            name.startswith("subagents/") and name.endswith(".jsonl.gz")
        ):
            continue
        target = transcript if name == MAIN else folder / name.removesuffix(".gz")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_bytes(gzip.decompress((download / name).read_bytes()))
        except (OSError, EOFError, zlib.error) as error:
            message = f"cannot read {name}"
            raise SessionFailedError(message) from error


@dataclass
class Run:
    """One run of the command: where it reads, how it signs in, what it knows."""

    bucket: str
    config: Path
    keep_token: bool
    known: list[Release]
    dry_run: bool

    def gcloud(self, *args: str) -> bytes:
        """Run gcloud as the hook does, and return its output."""
        return hook.gcloud(self.config, *args, keep_token=self.keep_token)

    def old_metadata(self, session: str) -> dict[str, Any]:
        """Return the session's `metadata.json` from the bucket."""
        try:
            text = self.gcloud(
                "storage", "cat", f"gs://{self.bucket}/{session}/{METADATA}"
            )
            old = json.loads(text)
        except (subprocess.CalledProcessError, ValueError) as error:
            message = f"cannot read {METADATA}"
            raise SessionFailedError(message) from error
        if not isinstance(old, dict) or not isinstance(old.get("segments"), list):
            message = f"cannot read {METADATA}"
            raise SessionFailedError(message)
        return old

    def rebuild(self, session: str, names: set[str], work: Path) -> str:
        """Rebuild one session's `metadata.json`; return `rebuilt` or `up to date`."""
        if METADATA not in names:
            message = f"no {METADATA}"
            raise SessionFailedError(message)
        old = self.old_metadata(session)
        if up_to_date(old):
            return "up to date"
        if MAIN not in names:
            message = f"no {MAIN}"
            raise SessionFailedError(message)
        download = work / "download"
        try:
            self.gcloud(
                "storage",
                "rsync",
                f"gs://{self.bucket}/{session}",
                str(download),
                "--recursive",
            )
        except subprocess.CalledProcessError as error:
            message = "cannot download the session"
            raise SessionFailedError(message) from error
        transcript = work / "session.jsonl"
        unpack(download, names, transcript)
        branch = old.get("branch")
        branch = branch if isinstance(branch, str) else ""
        segments = hook.craft_segments(transcript, branch)
        if segments is None:
            message = "no craft step"
            raise SessionFailedError(message)
        lines = hook.timed_lines(transcript)
        start = lines[0][0] if lines else None
        recorded = recorded_versions(old)
        for segment in segments:
            kept = recorded.get((segment.step, segment.started_at))
            segment.craft_version = kept or release_version(
                self.known, start, moment(segment.ended_at)
            )
        text = hook.metadata_json(
            repo=old.get("repo"),
            branch=old.get("branch"),
            session=old.get("session_id"),
            segments=segments,
            event=old.get("event"),
            uploaded_at=old.get("uploaded_at"),
        )
        if not self.dry_run:
            target = work / METADATA
            target.write_text(text, encoding="utf-8")
            self.gcloud(
                "storage", "cp", str(target), f"gs://{self.bucket}/{session}/{METADATA}"
            )
        return "rebuilt"


def sessions(listing: str) -> dict[str, set[str]]:
    """Return the object names of each session folder in a bucket listing."""
    found: dict[str, set[str]] = {}
    for line in listing.splitlines():
        match = SESSION_OBJECT.match(line.strip())
        if match is not None:
            found.setdefault(match.group("session"), set()).add(match.group("name"))
    return found


def fail(message: str) -> int:
    """Print an error and return the exit status 1."""
    print(f"error: {message}", file=sys.stderr)  # noqa: T201 - a command's error.
    return 1


def main(args: list[str]) -> int:
    """Re-process the bucket's sessions. Return the exit status."""
    bucket = hook.setting(hook.BUCKET_ENV)
    if not bucket:
        return fail(f"set {hook.BUCKET_ENV} to the transcript bucket")
    if not (hook.setting(hook.KEY_ENV) or hook.proxy_auth()):
        return fail(f"set {hook.KEY_ENV}, or run where the cloud proxy adds the token")
    known = releases(str(Path.cwd()))
    if not known:
        return fail("no release tag v<x>.<y>.<z> here; run `git fetch --tags` first")
    counts = {"rebuilt": 0, "up to date": 0, "failed": 0}
    with tempfile.TemporaryDirectory(prefix="craft-reprocess-") as tmp:
        work = Path(tmp)
        config, keep_token = hook.sign_in(work)
        run = Run(bucket, config, keep_token, known, dry_run=DRY_RUN in args)
        try:
            listing = run.gcloud("storage", "ls", f"gs://{bucket}/**")
        except subprocess.CalledProcessError as error:
            return fail(f"cannot list gs://{bucket}: {error.stderr.decode()[-500:]}")
        for number, (session, names) in enumerate(
            sorted(sessions(listing.decode()).items())
        ):
            folder = work / str(number)
            folder.mkdir()
            try:
                outcome = run.rebuild(session, names, folder)
            except SessionFailedError as error:
                counts["failed"] += 1
                print(f"{session}: failed: {error}")  # noqa: T201 - the report.
                continue
            counts[outcome] += 1
            print(f"{session}: {outcome}")  # noqa: T201 - the report.
    print(", ".join(f"{count} {name}" for name, count in counts.items()))  # noqa: T201
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
