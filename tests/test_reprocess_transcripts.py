# Copyright (C) 2026 Theo van Oostrum
"""The re-process command rebuilds `metadata.json` of stored sessions.

The command runs as a process, with the fake `gcloud` of the upload hook tests:
its bucket is a local folder. Its current directory is a git repo with release
tags at set commit times.
"""

import gzip
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.transcripts import (
    HOOKS,
    OPUS,
    PLAN,
    SESSION,
    A,
    B,
    configured_env,
    fake_env,
    in_dir,
    metadata,
    move,
    prompt,
    reply,
    run_hook,
    session_folder,
    skill,
    stamp,
    wait_for_uploads,
    write_jsonl,
)

COMMAND = HOOKS / "reprocess_transcripts.py"
BUCKET = "factory-logs"
NEW_FIELDS = ("craft_version", "model", "work_seconds", "wait_seconds", "brief")
KEPT = ("repo", "branch", "session_id", "event", "uploaded_at")
OLD_UPLOAD = "2026-11-02T10:30:00+00:00"


def git(cwd: Path, *args: str, date: str | None = None) -> None:
    """Run git in `cwd`, with a set commit time when `date` is given."""
    env = dict(os.environ)
    if date is not None:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(  # noqa: S603
        ["git", "-C", str(cwd), *args],  # noqa: S607
        check=True,
        capture_output=True,
        env=env,
    )


def craft_checkout(tmp_path: Path, tags: dict[str, str]) -> Path:
    """Return a git repo with one commit per tag, at the tag's commit time.

    The tags are lightweight, except `v2.8.0`, which is annotated, as a release
    tag may be either.
    """
    checkout = tmp_path / "craft"
    checkout.mkdir()
    git(checkout, "init", "-q", "-b", "main")
    git(checkout, "config", "user.email", "craft@example.com")
    git(checkout, "config", "user.name", "craft")
    for tag, date in tags.items():
        git(checkout, "commit", "-q", "--allow-empty", "-m", tag, date=date)
        if tag == "v2.8.0":
            git(checkout, "tag", "-a", tag, "-m", tag, date="2030-01-01T00:00:00Z")
        else:
            git(checkout, "tag", tag)
    return checkout


BEFORE = {"v2.8.0": "2026-11-02T09:00:00Z"}


def run_command(
    env: dict[str, str], cwd: Path, *args: str
) -> subprocess.CompletedProcess[str]:
    """Run the re-process command as the owner does, from a craft checkout."""
    return subprocess.run(  # noqa: S603
        [sys.executable, str(COMMAND), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )


def bucket(tmp_path: Path) -> Path:
    """Return the local folder of the fake bucket."""
    return tmp_path / "gcs" / BUCKET


def files(tmp_path: Path) -> dict[str, bytes]:
    """Return every file in the fake bucket, by path."""
    root = bucket(tmp_path)
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def gcloud_calls(tmp_path: Path) -> list[str]:
    """Return the fake `gcloud` calls so far, one line each."""
    log = tmp_path / "gcloud.log"
    return log.read_text("utf-8").splitlines() if log.exists() else []


def make_old(data: dict[str, Any], **changes: Any) -> dict[str, Any]:  # noqa: ANN401
    """Return metadata as a hook before CRAFT-72 wrote it: without the new fields."""
    segments = [
        {key: value for key, value in segment.items() if key not in NEW_FIELDS}
        for segment in data["segments"]
    ]
    return {**data, "segments": segments, **changes}


def put_session(  # noqa: PLR0913 - a stored session and its parts.
    tmp_path: Path,
    path: str,
    lines: list[dict[str, Any]] | None,
    data: dict[str, Any] | None,
    *,
    subagents: dict[str, list[dict[str, Any]]] | None = None,
    raw: bytes | None = None,
) -> Path:
    """Store a session in the fake bucket as the hook uploads it."""
    folder = bucket(tmp_path) / path
    folder.mkdir(parents=True)
    if raw is not None:
        (folder / "session.jsonl.gz").write_bytes(raw)
    elif lines is not None:
        text = "".join(json.dumps(line) + "\n" for line in lines)
        (folder / "session.jsonl.gz").write_bytes(gzip.compress(text.encode()))
    for name, agent_lines in (subagents or {}).items():
        target = folder / "subagents" / f"{name}.jsonl.gz"
        target.parent.mkdir(exist_ok=True)
        text = "".join(json.dumps(line) + "\n" for line in agent_lines)
        target.write_bytes(gzip.compress(text.encode()))
    if data is not None:
        (folder / "metadata.json").write_text(json.dumps(data), "utf-8")
    return folder


def stored(tmp_path: Path, path: str) -> dict[str, Any]:
    """Return the `metadata.json` of a stored session."""
    return json.loads((bucket(tmp_path) / path / "metadata.json").read_text("utf-8"))


OLD_SEGMENT = {"step": "build", "ticket": "LIBRAG-12", "started_at": stamp(1)}


def old_metadata(
    branch: str,
    segments: list[dict[str, Any]] | None = None,
    repo: str = "vanoostrum/librag",
) -> dict[str, Any]:
    """Return an old `metadata.json`, by default with one segment of an old hook."""
    return {
        "repo": repo,
        "branch": branch,
        "session_id": "old",
        "tickets": [],
        "segments": [OLD_SEGMENT] if segments is None else segments,
        "event": "SessionEnd",
        "uploaded_at": OLD_UPLOAD,
    }


BUILD_LINES = [
    prompt(0, "Build it."),
    reply(1, "m1", OPUS, 10, skill("craft:build", "LIBRAG-12")),
    reply(5, "m2", OPUS, 10, {"type": "text", "text": "Built."}),
    reply(10, "m3", OPUS, 10, skill("craft:review")),
    reply(12, "m4", OPUS, 10, {"type": "text", "text": "Reviewed."}),
]
BUILD_PATH = "vanoostrum/librag/sessions/build"


def put_build(tmp_path: Path, segments: list[dict[str, Any]] | None = None) -> None:
    """Store an old build session: build 10:01-10:05, review 10:10-10:12."""
    put_session(
        tmp_path,
        BUILD_PATH,
        BUILD_LINES,
        old_metadata("librag-12/version-endpoint", segments),
    )


def reprocessed(
    tmp_path: Path, tags: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run the command on the fake bucket, from a checkout with `tags`."""
    env = fake_env(tmp_path, CRAFT_GCS_BUCKET=BUCKET)
    return run_command(env, craft_checkout(tmp_path, tags))


# Criterion 9: sign-in and bucket.


@pytest.mark.parametrize(
    ("settings", "proxy", "message"),
    [
        ({}, True, "CRAFT_GCS_BUCKET"),
        ({"CRAFT_GCS_BUCKET": BUCKET}, False, "CRAFT_GCS_KEY"),
    ],
    ids=["no bucket", "no way to sign in"],
)
def test_stops_without_a_bucket_or_a_sign_in(
    tmp_path: Path, settings: dict[str, str], *, proxy: bool, message: str
) -> None:
    """Without a bucket, or without a key and the proxy token, no gcloud runs."""
    env = fake_env(tmp_path, **settings)
    if not proxy:
        env.pop("CLOUDSDK_AUTH_ACCESS_TOKEN")
    result = run_command(env, craft_checkout(tmp_path, BEFORE))

    assert result.returncode == 1
    assert message in result.stderr
    assert gcloud_calls(tmp_path) == []


def test_signs_in_with_the_key(tmp_path: Path) -> None:
    """With `CRAFT_GCS_KEY`, gcloud signs in with it, and drops the proxy token."""
    put_build(tmp_path)
    env = configured_env(tmp_path)
    result = run_command(env, craft_checkout(tmp_path, BEFORE))

    assert result.returncode == 0, result.stderr
    calls = gcloud_calls(tmp_path)
    assert calls[0].startswith("auth activate-service-account")
    assert all(call.endswith("token=none") for call in calls)


# Criteria 1 and 2: the rebuild.


def without_versions(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the segments of `metadata.json` without `craft_version`."""
    return [
        {key: value for key, value in s.items() if key != "craft_version"}
        for s in data["segments"]
    ]


def test_rebuilds_an_old_session_as_the_hook_uploads_it(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """The rebuild has the hook's tickets and segments, with the old kept fields."""
    run_hook(configured_env(tmp_path), transcript, project, event="SessionEnd")
    wait_for_uploads(tmp_path, 1)
    expected = metadata(tmp_path)
    folder = session_folder(tmp_path)
    old = make_old(
        expected, branch="librag-12/version-endpoint", uploaded_at=OLD_UPLOAD
    )
    old["tickets"] = []
    (folder / "metadata.json").write_text(json.dumps(old), "utf-8")
    # The project is gone: the branch comes from the old metadata only.
    git(project, "checkout", "-q", "-b", "other")
    before = files(tmp_path)

    result = reprocessed(tmp_path, BEFORE)

    assert result.returncode == 0, result.stderr
    data = metadata(tmp_path)
    assert data["tickets"] == expected["tickets"]
    assert without_versions(data) == without_versions(expected)
    assert {key: data[key] for key in KEPT} == {key: old[key] for key in KEPT}
    assert list(data) == list(expected)
    after = files(tmp_path)
    changed = {name for name in after if after[name] != before.get(name)}
    assert changed == {f"vanoostrum/librag/sessions/{SESSION}/metadata.json"}
    assert set(after) == set(before)


def test_rebuild_splits_a_one_shot_spec_session(tmp_path: Path, project: Path) -> None:
    """A craft 2.8 one-shot spec session splits per ticket, as the hook does now."""
    lines = [
        prompt(0, f"Run craft:spec on the one-shot plan {PLAN}."),
        reply(1, "m1", OPUS, 1, skill("craft:spec")),
        *move(2, A, "Specifying"),
        *move(7, A, "Ready to build"),
        reply(9, "m9", OPUS, 5, skill("craft:next")),
        *move(10, B, "Specifying"),
        reply(12, "m12", OPUS, 7, {"type": "text", "text": "Grill B."}),
    ]
    session = tmp_path / f"{SESSION}.jsonl"
    write_jsonl(session, [in_dir(project, lines[0]), *lines[1:]])
    run_hook(configured_env(tmp_path), session, project)
    wait_for_uploads(tmp_path, 1)
    expected = metadata(tmp_path)
    one_segment = [{"step": "spec", "ticket": "LIBRAG-12", "started_at": stamp(1)}]
    old = {**expected, "tickets": ["LIBRAG-12"], "segments": one_segment}
    (session_folder(tmp_path) / "metadata.json").write_text(json.dumps(old), "utf-8")

    result = reprocessed(tmp_path, BEFORE)

    assert result.returncode == 0, result.stderr
    data = metadata(tmp_path)
    assert [(s["step"], s["ticket"]) for s in data["segments"]] == [
        ("spec", PLAN),
        ("spec", A),
        ("spec", PLAN),
        ("next", PLAN),
        ("spec", B),
    ]
    assert without_versions(data) == without_versions(expected)


def test_rebuilds_a_session_without_a_repo(tmp_path: Path) -> None:
    """A session under `no-repo/` is found too, one folder less deep."""
    path = "no-repo/sessions/loose"
    put_session(tmp_path, path, BUILD_LINES, old_metadata("", repo="no-repo"))

    result = reprocessed(tmp_path, BEFORE)

    assert result.returncode == 0, result.stderr
    assert f"{path}: rebuilt" in result.stdout.splitlines()
    data = stored(tmp_path, path)
    assert [(s["step"], s["ticket"]) for s in data["segments"]] == [
        ("build", "LIBRAG-12"),
        ("review", None),
    ]
    assert data["repo"] == "no-repo"


def test_rebuild_gives_subagents_to_their_step(tmp_path: Path) -> None:
    """Subagent transcripts in the bucket count toward their segment."""
    put_session(
        tmp_path,
        BUILD_PATH,
        BUILD_LINES,
        old_metadata("librag-12/version-endpoint"),
        subagents={"agent-x1": [reply(11, "s1", OPUS, 40)]},
    )

    result = reprocessed(tmp_path, BEFORE)

    assert result.returncode == 0, result.stderr
    build, review = stored(tmp_path, BUILD_PATH)["segments"]
    assert build["subagents"] == []
    assert [s["agent_id"] for s in review["subagents"]] == ["x1"]
    assert review["ticket"] == "LIBRAG-12"


# Criterion 3: up to date.


def full_segment(step: str, started_at: str) -> dict[str, Any]:
    """Return a segment with every ADR 0005 field, as the released hook writes."""
    return {
        "step": step,
        "ticket": "LIBRAG-12",
        "started_at": started_at,
        "ended_at": started_at,
        "tokens": {},
        "subagents": [],
        "craft_version": None,
        "model": None,
        "work_seconds": 0.0,
        "wait_seconds": 0.0,
        "brief": None,
    }


def test_up_to_date_session_is_not_downloaded_or_written(tmp_path: Path) -> None:
    """A session with all five fields, even with null values, is left alone."""
    put_build(tmp_path, [full_segment("build", stamp(1))])
    before = files(tmp_path)

    result = reprocessed(tmp_path, BEFORE)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        f"{BUILD_PATH}: up to date",
        "0 rebuilt, 1 up to date, 0 failed",
    ]
    assert files(tmp_path) == before
    assert not [
        c
        for c in gcloud_calls(tmp_path)
        if c.startswith(("storage rsync", "storage cp"))
    ]


def test_second_run_writes_nothing(tmp_path: Path) -> None:
    """A run right after a run finds every session up to date."""
    put_build(tmp_path)
    env = fake_env(tmp_path, CRAFT_GCS_BUCKET=BUCKET)
    checkout = craft_checkout(tmp_path, BEFORE)
    first = run_command(env, checkout)
    assert f"{BUILD_PATH}: rebuilt" in first.stdout
    after_first = files(tmp_path)
    calls = len(gcloud_calls(tmp_path))

    second = run_command(env, checkout)

    assert second.returncode == 0, second.stderr
    assert f"{BUILD_PATH}: up to date" in second.stdout
    assert files(tmp_path) == after_first
    assert not [
        c
        for c in gcloud_calls(tmp_path)[calls:]
        if c.startswith(("storage rsync", "storage cp"))
    ]


# Criteria 4, 5, and 6: the craft version.

VERSIONS = {
    "release before the session": (
        {"v2.7.0": "2026-11-01T09:00:00Z", **BEFORE, "v2.9.0": "2026-11-02T11:00:00Z"},
        ["2.8.0", "2.8.0"],
    ),
    "release in the middle": (
        {**BEFORE, "v2.9.0": "2026-11-02T10:07:00Z"},
        ["2.8.0", None],
    ),
    "release at the session start": (
        {"v2.9.0": "2026-11-02T10:00:00Z"},
        ["2.9.0", "2.9.0"],
    ),
    "no release before the session": (
        {"v2.9.0": "2026-11-02T11:00:00Z"},
        [None, None],
    ),
    "other tags do not count": (
        {
            **BEFORE,
            "v2.9.0-rc1": "2026-11-02T10:07:00Z",
            "probe": "2026-11-02T10:08:00Z",
        },
        ["2.8.0", "2.8.0"],
    ),
}


@pytest.mark.parametrize(("tags", "expected"), VERSIONS.values(), ids=VERSIONS.keys())
def test_craft_version_from_release_times(
    tmp_path: Path, tags: dict[str, str], expected: list[str | None]
) -> None:
    """The latest release before the start, unless a release falls before the end."""
    put_build(tmp_path)

    result = reprocessed(tmp_path, tags)

    assert result.returncode == 0, result.stderr
    segments = stored(tmp_path, BUILD_PATH)["segments"]
    assert [s["craft_version"] for s in segments] == expected


def test_a_recorded_version_is_kept(tmp_path: Path) -> None:
    """A string `craft_version` of the same step and start wins over the tags."""
    put_build(
        tmp_path,
        [
            {"step": "build", "started_at": stamp(1), "craft_version": "2.9.0"},
            {"step": "review", "started_at": stamp(9), "craft_version": "2.9.0"},
        ],
    )

    result = reprocessed(tmp_path, {**BEFORE, "v2.9.0": "2026-11-02T10:07:00Z"})

    assert result.returncode == 0, result.stderr
    segments = stored(tmp_path, BUILD_PATH)["segments"]
    # The review started at 10:10, so the old 10:09 version is another segment.
    assert [s["craft_version"] for s in segments] == ["2.9.0", None]


def test_stops_without_release_tags(tmp_path: Path) -> None:
    """A checkout without release tags gives an error before any gcloud call."""
    put_build(tmp_path)
    before = files(tmp_path)

    result = reprocessed(tmp_path, {"probe": "2026-11-02T09:00:00Z"})

    assert result.returncode == 1
    assert "release tag" in result.stderr
    assert gcloud_calls(tmp_path) == []
    assert files(tmp_path) == before


# Criteria 7 and 8: the report, failures, and the dry run.


def put_mixed_bucket(tmp_path: Path) -> None:
    """Store one good session and one session for each way to fail."""
    put_build(tmp_path)
    branch = "librag-12/version-endpoint"
    put_session(tmp_path, "a/b/sessions/no-metadata", BUILD_LINES, None)
    put_session(tmp_path, "a/b/sessions/no-transcript", None, old_metadata(branch))
    put_session(
        tmp_path,
        "a/b/sessions/broken-transcript",
        None,
        old_metadata(branch),
        raw=b"not gzip",
    )
    folder = put_session(tmp_path, "a/b/sessions/broken-metadata", BUILD_LINES, None)
    (folder / "metadata.json").write_text("{", "utf-8")
    put_session(
        tmp_path,
        "a/b/sessions/no-step",
        [prompt(0, "Hello."), reply(1, "m1", OPUS, 1, skill("craft:rules"))],
        old_metadata(branch),
    )


MIXED_REPORT = [
    "a/b/sessions/broken-metadata: failed: cannot read metadata.json",
    "a/b/sessions/broken-transcript: failed: cannot read session.jsonl.gz",
    "a/b/sessions/no-metadata: failed: no metadata.json",
    "a/b/sessions/no-step: failed: no craft step",
    "a/b/sessions/no-transcript: failed: no session.jsonl.gz",
    f"{BUILD_PATH}: rebuilt",
    "1 rebuilt, 0 up to date, 5 failed",
]


def test_failed_sessions_do_not_stop_the_others(tmp_path: Path) -> None:
    """Each failed session is reported and not written; the exit status is 1."""
    put_mixed_bucket(tmp_path)
    before = files(tmp_path)

    result = reprocessed(tmp_path, BEFORE)

    assert result.returncode == 1
    assert result.stdout.splitlines() == MIXED_REPORT
    after = files(tmp_path)
    changed = {name for name in after if after[name] != before.get(name)}
    assert changed == {f"{BUILD_PATH}/metadata.json"}


def test_dry_run_reports_and_writes_nothing(tmp_path: Path) -> None:
    """`--dry-run` prints the report of a real run, and the bucket stays as it is."""
    put_mixed_bucket(tmp_path)
    before = files(tmp_path)
    env = fake_env(tmp_path, CRAFT_GCS_BUCKET=BUCKET)

    result = run_command(env, craft_checkout(tmp_path, BEFORE), "--dry-run")

    assert result.returncode == 1
    assert result.stdout.splitlines() == MIXED_REPORT
    assert files(tmp_path) == before
    assert not [c for c in gcloud_calls(tmp_path) if c.startswith("storage cp")]
