# Copyright (C) 2026 Theo van Oostrum
"""The upload hook copies a session's transcripts to Google Cloud Storage.

A fake `gcloud` on `PATH` stands in for Google Cloud. Its `storage rsync`
copies the folder into a local "bucket" folder, so the tests can read what
would land in the bucket.
"""

import base64
import gzip
import json
import subprocess
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.transcripts import (
    HOOK,
    HOOKS,
    KEY,
    OPUS,
    PLAN,
    ROOT,
    SECRET,
    SESSION,
    SONNET,
    A,
    B,
    call_result,
    configured_env,
    fake_env,
    git_repo,
    in_dir,
    metadata,
    move,
    prompt,
    reply,
    run_hook,
    session_folder,
    skill,
    stamp,
    tool_call,
    wait_for_uploads,
    write_jsonl,
)

BRANCH_TICKET = "LIBRAG-12"
STATE_ID = "12c9a27c-cde3-413e-a70a-ebdeb48c7f23"


def at(seconds: float) -> str:
    """Return a transcript timestamp `seconds` after 10:00, to the millisecond."""
    moment = datetime(2026, 11, 2, 10, tzinfo=UTC) + timedelta(seconds=seconds)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def slash_command(minute: int, name: str, args: str = "") -> dict[str, Any]:
    """Return the user line that Claude Code writes for a typed slash command."""
    text = (
        f"<command-message>{name}</command-message>\n"
        f"<command-name>/{name}</command-name>\n"
        f"<command-args>{args}</command-args>"
    )
    return {"type": "user", "timestamp": stamp(minute), "message": {"content": text}}


def assert_no_upload(tmp_path: Path) -> None:
    """Assert that the hook called no Google tool and logged no upload."""
    upload_log = tmp_path / "tmp" / "craft-transcripts" / "upload.log"
    assert not (tmp_path / "gcloud.log").exists()
    assert " uploaded " not in (
        upload_log.read_text("utf-8") if upload_log.exists() else ""
    )


def assert_skipped(tmp_path: Path) -> None:
    """Wait until the background process skips the session, then assert no upload."""
    upload_log = tmp_path / "tmp" / "craft-transcripts" / "upload.log"
    deadline = time.monotonic() + 20
    while " skipped " not in (
        upload_log.read_text("utf-8") if upload_log.exists() else ""
    ):
        if time.monotonic() > deadline:
            pytest.fail("the hook did not skip the session")
        time.sleep(0.1)
    assert "no craft step" in upload_log.read_text("utf-8")
    assert_no_upload(tmp_path)


def tokens(model: str, input_tokens: int, replies: int) -> dict[str, dict[str, int]]:
    """Return the expected token totals of one model."""
    return {
        model: {
            "input_tokens": input_tokens,
            "output_tokens": replies,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }
    }


def test_uploads_the_session_transcripts(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """The bucket gets the gzipped transcripts, with secrets redacted."""
    run_hook(configured_env(tmp_path), transcript, project)
    wait_for_uploads(tmp_path, 1)

    folder = session_folder(tmp_path)
    main = gzip.decompress((folder / "session.jsonl.gz").read_bytes()).decode()
    subagent = gzip.decompress(
        (folder / "subagents" / "agent-a1.jsonl.gz").read_bytes()
    )

    # The lines before the first step are there too.
    assert "key [redacted:OPENAI_API_KEY]" in main
    assert SECRET not in main
    assert "token proxy-injected" in main
    meta = folder / "subagents" / "agent-a1.meta.json.gz"
    assert gzip.decompress(meta.read_bytes()) == b'{"agentType": "general"}'
    assert (
        subagent
        == (transcript.parent / SESSION / "subagents" / "agent-a1.jsonl").read_bytes()
    )
    data = metadata(tmp_path)
    assert data["repo"] == "vanoostrum/librag"
    assert data["branch"] == "librag-12/version-endpoint"
    assert data["session_id"] == SESSION
    assert data["tickets"] == ["LIBRAG-12"]
    assert data["event"] == "Stop"


def test_splits_the_session_into_craft_steps(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """A craft step's Skill call starts a segment with its ticket, times, tokens."""
    run_hook(configured_env(tmp_path), transcript, project)
    wait_for_uploads(tmp_path, 1)

    build, review, merge = metadata(tmp_path)["segments"]

    assert (build["step"], build["ticket"]) == ("build", "LIBRAG-12")
    assert (build["started_at"], build["ended_at"]) == (stamp(1), stamp(5))
    assert build["tokens"] == tokens(SONNET, 120, 2)
    assert (review["step"], review["ticket"]) == ("review", "LIBRAG-12")
    assert review["tokens"] == tokens(OPUS, 300, 1)
    assert (merge["step"], merge["ticket"]) == ("merge", "LIBRAG-12")
    assert (merge["started_at"], merge["ended_at"]) == (stamp(20), stamp(21))
    assert merge["tokens"] == tokens(OPUS, 12, 2)


def test_assigns_subagents_to_their_step(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """A subagent goes to the step of its `Agent` call, or else of its start time."""
    run_hook(configured_env(tmp_path), transcript, project)
    wait_for_uploads(tmp_path, 1)

    build, review, merge = metadata(tmp_path)["segments"]

    assert build["subagents"] == [
        {
            "agent_id": "a1",
            "role": "app driver",
            "started_at": stamp(3),
            "ended_at": stamp(3),
            "tokens": tokens(SONNET, 40, 1),
        }
    ]
    assert [s["agent_id"] for s in review["subagents"]] == ["b2"]
    assert review["subagents"][0]["role"] is None
    assert review["subagents"][0]["tokens"] == tokens(OPUS, 50, 1)
    assert merge["subagents"] == []


def test_failed_skill_call_starts_no_segment(tmp_path: Path, project: Path) -> None:
    """A Skill call that returns an error, such as an unknown skill, is no step."""
    session = tmp_path / "failed.jsonl"
    call = skill("craft:next")
    error = {
        "type": "user",
        "timestamp": stamp(2),
        "message": {
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": call["id"],
                    "is_error": True,
                    "content": "Unknown skill: craft:next",
                }
            ]
        },
    }
    write_jsonl(session, [in_dir(project, reply(1, "m1", OPUS, 9, call)), error])
    run_hook(configured_env(tmp_path), session, project, "SessionEnd")

    assert_skipped(tmp_path)


def test_step_without_a_ticket(tmp_path: Path, project: Path) -> None:
    """A step without a ticket argument, on a branch without one, has no ticket."""
    subprocess.run(  # noqa: S603
        ["git", "-C", str(project), "checkout", "-q", "-b", "claude/thread"],  # noqa: S607
        check=True,
    )
    plain = tmp_path / "plain.jsonl"
    write_jsonl(plain, [in_dir(project, reply(1, "m1", OPUS, 9, skill("craft:next")))])
    run_hook(configured_env(tmp_path), plain, project)
    wait_for_uploads(tmp_path, 1)

    data = metadata(tmp_path)
    assert data["tickets"] == []
    assert data["branch"] == "claude/thread"
    assert [(s["step"], s["ticket"]) for s in data["segments"]] == [("next", None)]


@pytest.mark.parametrize("event", ["Stop", "SubagentStop", "SessionEnd"])
@pytest.mark.parametrize("name", ["craft:rules", "craft:bstack", "pstack:tdd"])
def test_session_without_a_step_uploads_nothing(
    tmp_path: Path, project: Path, event: str, name: str
) -> None:
    """A session that loads craft skills but runs no step is not uploaded."""
    chat = tmp_path / "chat.jsonl"
    write_jsonl(
        chat,
        [
            in_dir(project, reply(1, "m1", OPUS, 9, skill(name))),
            reply(2, "m2", OPUS, 9, {"type": "text", "text": "Hi."}),
        ],
    )
    run_hook(configured_env(tmp_path), chat, project, event)

    assert_skipped(tmp_path)


@pytest.mark.parametrize(
    "step",
    [
        "brainstorm",
        "setup",
        "plan",
        "spec",
        "design",
        "build",
        "review",
        "merge",
        "next",
    ],
)
def test_each_step_skill_starts_a_segment(
    tmp_path: Path, project: Path, step: str
) -> None:
    """Each of the nine craft steps starts a segment with its step name."""
    session = tmp_path / "step.jsonl"
    write_jsonl(
        session, [in_dir(project, reply(1, "m1", OPUS, 9, skill(f"craft:{step}")))]
    )
    run_hook(configured_env(tmp_path), session, project)
    wait_for_uploads(tmp_path, 1)

    assert [s["step"] for s in metadata(tmp_path)["segments"]] == [step]


@pytest.mark.parametrize("name", ["sous:build", "factory-build", "factory:build"])
def test_old_step_names_are_no_step(tmp_path: Path, project: Path, name: str) -> None:
    """The names from before craft 2.0 and before the plugin no longer count."""
    session = tmp_path / "old.jsonl"
    write_jsonl(session, [in_dir(project, reply(1, "m1", OPUS, 9, skill(name)))])
    run_hook(configured_env(tmp_path), session, project, "SessionEnd")

    assert_skipped(tmp_path)


def test_slash_command_starts_a_segment(
    tmp_path: Path, project: Path, outside: Path
) -> None:
    """A step that the owner types as a slash command counts, with its ticket."""
    session = tmp_path / "local.jsonl"
    write_jsonl(
        session,
        [
            in_dir(project, reply(1, "m1", OPUS, 9, {"type": "text", "text": "Hi."})),
            in_dir(project, slash_command(2, "craft:build", "CRAFT-12")),
            reply(3, "m2", SONNET, 20, {"type": "text", "text": "Building."}),
        ],
    )
    run_hook(configured_env(tmp_path), session, outside)
    wait_for_uploads(tmp_path, 1)

    segments = metadata(tmp_path)["segments"]
    assert [(s["step"], s["ticket"]) for s in segments] == [
        (None, "LIBRAG-12"),
        ("build", "CRAFT-12"),
    ]
    assert segments[1]["tokens"] == tokens(SONNET, 20, 1)


def test_other_slash_commands_are_no_step(tmp_path: Path, project: Path) -> None:
    """A slash command that is not a craft step, such as `/craft:rules`, is no step."""
    session = tmp_path / "local.jsonl"
    write_jsonl(
        session,
        [
            in_dir(project, slash_command(1, "craft:rules")),
            in_dir(project, slash_command(2, "clear")),
        ],
    )
    run_hook(configured_env(tmp_path), session, project, "SessionEnd")

    assert_skipped(tmp_path)


@pytest.mark.parametrize(
    "origin",
    [
        "https://github.com/vanoostrum/craft.git",
        "https://github.com/vanoostrum/craft",
        "git@github.com:vanoostrum/craft.git",
        "ssh://git@github.com/vanoostrum/craft.git",
        "http://local_proxy@127.0.0.1:41463/git/vanoostrum/craft",
        "https://user:ghp_token123@github.com:8443/vanoostrum/craft.git",
    ],
)
def test_folder_is_named_after_the_origin_remote(
    tmp_path: Path, outside: Path, origin: str
) -> None:
    """The folder is `<owner>/<repo>` from the `origin` URL, for HTTPS and SSH."""
    repo = git_repo(tmp_path / "work" / "craft-clone", "craft-7/x", origin)
    session = tmp_path / "s.jsonl"
    write_jsonl(session, [in_dir(repo, reply(1, "m1", OPUS, 9, skill("craft:spec")))])
    run_hook(configured_env(tmp_path), session, outside)
    wait_for_uploads(tmp_path, 1)

    data = metadata(tmp_path, "vanoostrum/craft")
    assert data["repo"] == "vanoostrum/craft"
    assert data["branch"] == "craft-7/x"
    assert data["segments"][0]["ticket"] == "CRAFT-7"


def test_first_repo_with_an_origin_wins(
    tmp_path: Path, project: Path, outside: Path
) -> None:
    """Directories outside a repo, or in a repo without `origin`, are skipped."""
    local = git_repo(tmp_path / "local", "main", None)
    other = git_repo(tmp_path / "other", "main", "git@github.com:someone/other.git")
    session = tmp_path / "s.jsonl"
    write_jsonl(
        session,
        [
            in_dir(outside, reply(1, "m1", OPUS, 9, skill("craft:build"))),
            in_dir(local, reply(2, "m2", OPUS, 9)),
            in_dir(project, reply(3, "m3", OPUS, 9)),
            in_dir(other, reply(4, "m4", OPUS, 9)),
        ],
    )
    run_hook(configured_env(tmp_path), session, other)
    wait_for_uploads(tmp_path, 1)

    assert metadata(tmp_path)["repo"] == "vanoostrum/librag"


@pytest.mark.parametrize(
    "origin",
    [
        None,
        "https://example.com/craft.git",
        "https://host:8443/craft.git",
        "https://user:ghp_token123@github.com/craft.git",
        "git@github.com:craft.git",
    ],
)
def test_session_without_a_repo_goes_to_no_repo(
    tmp_path: Path, outside: Path, origin: str | None
) -> None:
    """Without a repo whose `origin` has an owner and a name, the folder is no-repo."""
    repo = git_repo(tmp_path / "solo", "craft-3/y", origin)
    session = tmp_path / "s.jsonl"
    write_jsonl(
        session,
        [
            in_dir(outside, reply(1, "m1", OPUS, 9, skill("craft:plan", "CRAFT-3"))),
            in_dir(repo, reply(2, "m2", OPUS, 9)),
        ],
    )
    run_hook(configured_env(tmp_path), session, repo)
    wait_for_uploads(tmp_path, 1)

    data = metadata(tmp_path, "no-repo")
    assert data["repo"] == "no-repo"
    assert data["branch"] == ""
    assert data["tickets"] == ["CRAFT-3"]


def test_skips_a_stop_soon_after_an_upload(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """A Stop within the interval does not upload; a SubagentStop does."""
    env = configured_env(tmp_path)
    run_hook(env, transcript, project)
    wait_for_uploads(tmp_path, 1)

    run_hook(env, transcript, project, "Stop")
    run_hook(env, transcript, project, "SubagentStop")
    wait_for_uploads(tmp_path, 2)
    time.sleep(1)

    upload_log = tmp_path / "tmp" / "craft-transcripts" / "upload.log"
    uploads = upload_log.read_text("utf-8").count(" uploaded ")
    assert uploads == len(["first Stop", "SubagentStop"])
    assert metadata(tmp_path)["event"] == "SubagentStop"


def test_stop_uploads_again_after_the_interval(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """With an interval of 0, every Stop uploads."""
    env = configured_env(tmp_path)
    env["CRAFT_GCS_STOP_INTERVAL"] = "0"
    run_hook(env, transcript, project)
    wait_for_uploads(tmp_path, 1)
    run_hook(env, transcript, project)
    wait_for_uploads(tmp_path, 2)


def test_unchanged_files_keep_the_same_bytes(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """Two uploads of an unchanged transcript write identical gzip files."""
    env = configured_env(tmp_path)
    run_hook(env, transcript, project, "SubagentStop")
    wait_for_uploads(tmp_path, 1)
    first = (session_folder(tmp_path) / "session.jsonl.gz").read_bytes()
    time.sleep(1.1)
    run_hook(env, transcript, project, "SubagentStop")
    wait_for_uploads(tmp_path, 2)

    assert (session_folder(tmp_path) / "session.jsonl.gz").read_bytes() == first


def test_accepts_a_base64_key(tmp_path: Path, project: Path, transcript: Path) -> None:
    """The key can be base64, which fits in a one-line environment variable."""
    key = base64.b64encode(json.dumps(KEY).encode()).decode()
    run_hook(configured_env(tmp_path, key), transcript, project)
    wait_for_uploads(tmp_path, 1)

    log = (tmp_path / "gcloud.log").read_text(encoding="utf-8")
    assert "auth activate-service-account" in log


def test_ignores_the_sandbox_access_token(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """The upload runs as the service account, not with the sandbox token."""
    run_hook(configured_env(tmp_path), transcript, project)
    wait_for_uploads(tmp_path, 1)

    log = (tmp_path / "gcloud.log").read_text(encoding="utf-8").splitlines()
    assert log
    assert all(line.endswith("token=none") for line in log)


def test_uses_the_proxy_token_without_a_key(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """In a cloud session without a key, gcloud uses the token the proxy adds."""
    env = fake_env(tmp_path, CRAFT_GCS_BUCKET="factory-logs")
    run_hook(env, transcript, project)
    wait_for_uploads(tmp_path, 1)

    log = (tmp_path / "gcloud.log").read_text(encoding="utf-8").splitlines()
    assert len(log) == 1
    assert log[0].startswith("storage rsync ")
    assert log[0].endswith("token=proxy-injected")
    assert (session_folder(tmp_path) / "metadata.json").is_file()


def test_does_nothing_without_a_way_to_sign_in(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """With a bucket but no key and no proxy token, the hook calls no Google tool."""
    env = fake_env(tmp_path, CRAFT_GCS_BUCKET="factory-logs")
    del env["CLOUDSDK_AUTH_ACCESS_TOKEN"]
    run_hook(env, transcript, project)
    time.sleep(1)

    assert not (tmp_path / "gcloud.log").exists()


def test_does_nothing_without_a_bucket(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """Without the environment variables, the hook calls no Google tool."""
    run_hook(fake_env(tmp_path), transcript, project)
    time.sleep(1)

    assert not (tmp_path / "gcloud.log").exists()


def test_ignores_the_old_variable_names(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """The names from before craft 2.0 no longer configure the upload.

    A second run with the new names uploads, so a background upload from the
    first run would have finished and shown up in the log by then.
    """
    old = fake_env(
        tmp_path,
        SOUS_GCS_BUCKET="factory-logs",
        SOUS_GCS_KEY=json.dumps(KEY),
        SOUS_GCS_STOP_INTERVAL="0",
    )
    run_hook(old, transcript, project, "SessionEnd")
    time.sleep(1)
    run_hook(configured_env(tmp_path), transcript, project, "SessionEnd")
    wait_for_uploads(tmp_path, 1)
    time.sleep(1)

    upload_log = tmp_path / "tmp" / "craft-transcripts" / "upload.log"
    assert upload_log.read_text("utf-8").count(" uploaded ") == 1
    gcloud_log = (tmp_path / "gcloud.log").read_text("utf-8")
    assert gcloud_log.count("storage rsync") == 1


@pytest.mark.parametrize("event", ["Stop", "SubagentStop", "SessionEnd"])
def test_plugin_runs_the_hook(event: str) -> None:
    """Claude Code runs the hook after each turn, each subagent, and at the end."""
    hooks = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    commands = [hook["command"] for group in hooks[event] for hook in group["hooks"]]
    assert '"${CLAUDE_PLUGIN_ROOT}/hooks/upload_transcripts.py"' in " ".join(commands)


@pytest.mark.parametrize(
    "path",
    [
        HOOK,
        ROOT / ".github" / "workflows" / "ci.yml",
        ROOT / ".claude" / "skills" / "verify" / "SKILL.md",
    ],
)
def test_old_names_are_gone(path: Path) -> None:
    """The hook, CI, and the verify skill no longer name the old variables or steps."""
    text = path.read_text(encoding="utf-8")
    assert "SOUS_GCS" not in text
    assert "sous:" not in text


def step_session(tmp_path: Path, project: Path, lines: list[dict[str, Any]]) -> Path:
    """Write a build session in the project: its step call, then `lines`."""
    session = tmp_path / "step.jsonl"
    first = in_dir(project, reply(1, "m0", OPUS, 9, skill("craft:build")))
    write_jsonl(session, [first, *lines])
    return session


def uploaded_segments(
    tmp_path: Path, session: Path, project: Path
) -> list[dict[str, Any]]:
    """Run the hook on a session, and return the uploaded segments."""
    run_hook(configured_env(tmp_path), session, project)
    wait_for_uploads(tmp_path, 1)
    return metadata(tmp_path)["segments"]


def test_each_segment_has_the_new_fields(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """Each segment adds craft version, model, and times to the earlier fields."""
    run_hook(configured_env(tmp_path), transcript, project)
    wait_for_uploads(tmp_path, 1)

    data = metadata(tmp_path)
    assert set(data) == {
        "repo",
        "branch",
        "session_id",
        "tickets",
        "segments",
        "event",
        "uploaded_at",
    }
    for segment in data["segments"]:
        assert set(segment) == {
            "step",
            "ticket",
            "started_at",
            "ended_at",
            "tokens",
            "subagents",
            "craft_version",
            "model",
            "work_seconds",
            "wait_seconds",
            "brief",
        }


def test_model_is_the_model_of_most_replies(tmp_path: Path, project: Path) -> None:
    """A reply written as several lines counts once."""
    session = step_session(
        tmp_path,
        project,
        [
            reply(2, "m1", OPUS, 9, {"type": "text", "text": "One"}),
            reply(2, "m1", OPUS, 9, {"type": "text", "text": "reply"}),
            reply(2, "m1", OPUS, 9, {"type": "text", "text": "in three lines."}),
            reply(3, "m2", SONNET, 9),
            reply(4, "m3", SONNET, 9),
            reply(5, "m4", SONNET, 9),
        ],
    )

    assert uploaded_segments(tmp_path, session, project)[0]["model"] == SONNET


@pytest.mark.parametrize(("earlier", "later"), [(OPUS, SONNET), (SONNET, OPUS)])
def test_a_tie_goes_to_the_latest_reply(
    tmp_path: Path, project: Path, earlier: str, later: str
) -> None:
    """With as many replies per model, the model of the latest reply wins."""
    session = tmp_path / "tie.jsonl"
    write_jsonl(
        session,
        [
            in_dir(project, reply(1, "m1", earlier, 9, skill("craft:build"))),
            reply(2, "m2", earlier, 9),
            reply(3, "m3", later, 9),
            reply(4, "m4", later, 9),
        ],
    )

    assert uploaded_segments(tmp_path, session, project)[0]["model"] == later


def test_synthetic_replies_do_not_count(tmp_path: Path, project: Path) -> None:
    """Claude Code's `<synthetic>` replies, such as an error, are not a model."""
    session = step_session(
        tmp_path,
        project,
        [reply(2, "m1", "<synthetic>", 0), reply(3, "m2", "<synthetic>", 0)],
    )

    assert uploaded_segments(tmp_path, session, project)[0]["model"] == OPUS


def test_segment_without_own_replies_has_no_model(
    tmp_path: Path, project: Path
) -> None:
    """A typed step whose only work is a subagent's has no model, and uploads."""
    session = tmp_path / "typed.jsonl"
    subagents = tmp_path / "typed" / "subagents"
    subagents.mkdir(parents=True)
    write_jsonl(session, [in_dir(project, slash_command(1, "craft:build"))])
    write_jsonl(subagents / "agent-c3.jsonl", [reply(2, "s1", SONNET, 40)])

    (segment,) = uploaded_segments(tmp_path, session, project)

    assert segment["model"] is None
    assert segment["subagents"][0]["tokens"] == tokens(SONNET, 40, 1)


def test_subagent_replies_do_not_change_the_model(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """The build's subagent runs Sonnet, the review's Opus; neither counts."""
    subagents = transcript.parent / SESSION / "subagents"
    write_jsonl(
        subagents / "agent-a1.jsonl",
        [reply(3, f"s{n}", OPUS, 40) for n in range(5)],
    )
    write_jsonl(
        subagents / "agent-b2.jsonl",
        [reply(12, f"t{n}", SONNET, 50) for n in range(5)],
    )

    build, review, merge = uploaded_segments(tmp_path, transcript, project)

    assert (build["model"], review["model"], merge["model"]) == (SONNET, OPUS, OPUS)


def timed(seconds: float, line: dict[str, Any]) -> dict[str, Any]:
    """Return a transcript line at `seconds` after 10:00."""
    return {**line, "timestamp": at(seconds)}


def typed(seconds: float, text: str = "Go on.") -> dict[str, Any]:
    """Return a prompt that the owner types, or a wake as Claude Code writes it."""
    return {"type": "user", "timestamp": at(seconds), "message": {"content": text}}


def queue(seconds: float, operation: str) -> dict[str, Any]:
    """Return a `queue-operation` line, as a cloud session writes it."""
    line = {"type": "queue-operation", "operation": operation, "timestamp": at(seconds)}
    return {**line, "content": "Go on."} if operation == "enqueue" else line


def tool_result(seconds: float) -> dict[str, Any]:
    """Return the user line with a tool result."""
    block = {"type": "tool_result", "tool_use_id": "call-x", "content": "ok"}
    return {"type": "user", "timestamp": at(seconds), "message": {"content": [block]}}


def skill_text(seconds: float) -> dict[str, Any]:
    """Return the `isMeta` user line that holds a loaded skill's text."""
    return {**typed(seconds, "Base directory for this skill: ..."), "isMeta": True}


def times(segment: dict[str, Any]) -> tuple[float, float]:
    """Return the work and wait seconds of a segment."""
    return float(segment["work_seconds"]), float(segment["wait_seconds"])


def test_gaps_split_into_craft_time_and_waiting(tmp_path: Path, project: Path) -> None:
    """A gap that ends with an incoming message is waiting; other gaps are work.

    The wait before the review's step call belongs to the build, which stopped
    at its gate. The gap into the step call belongs to the review.
    """
    session = tmp_path / "timed.jsonl"
    write_jsonl(
        session,
        [
            in_dir(project, typed(0, "Build CRAFT-12.")),
            timed(10, reply(0, "m1", SONNET, 9, skill("craft:build"))),
            tool_result(25),
            timed(30, reply(0, "m2", SONNET, 9)),
            queue(100, "enqueue"),
            queue(100.5, "dequeue"),
            typed(101),
            skill_text(101.2),
            timed(105, reply(0, "m3", SONNET, 9)),
            queue(150, "enqueue"),
            typed(151, "approve"),
            timed(160, reply(0, "m4", OPUS, 9, skill("craft:review"))),
            timed(170, reply(0, "m5", OPUS, 9)),
        ],
    )

    build, review = uploaded_segments(tmp_path, session, project)

    # Work: 10 into the step call, 15, 5, 0.5 to the dequeue, 0.2, 3.8.
    # Wait: 70 to the enqueue, 0.5 to the typed prompt, 45, and 1.
    assert times(build) == (34.5, 116.5)
    assert times(review) == (19.0, 0.0)


def test_lines_out_of_order_give_no_negative_gap(tmp_path: Path, project: Path) -> None:
    """Lines are sorted by time; lines without a time and subagents do not count."""
    session = tmp_path / "unordered.jsonl"
    subagents = tmp_path / "unordered" / "subagents"
    subagents.mkdir(parents=True)
    attachment = {"type": "attachment", "attachment": {"type": "hook_success"}}
    write_jsonl(
        session,
        [
            in_dir(project, timed(10, reply(0, "m1", SONNET, 9, skill("craft:build")))),
            timed(20, reply(0, "m2", SONNET, 9)),
            # Claude Code writes this line after the one above, but it is older.
            # Unsorted, the gap into it would be -0.5 s, and the gap out 10.5 s.
            timed(19.5, attachment),
            {"type": "last-prompt", "leafUuid": "x"},
            {"type": "tools-used", "tools": ["Skill"]},
            queue(30.001, "enqueue"),
            timed(31.234, reply(0, "m3", SONNET, 9)),
        ],
    )
    write_jsonl(subagents / "agent-d4.jsonl", [timed(25, reply(0, "s1", OPUS, 9))])

    (build,) = uploaded_segments(tmp_path, session, project)

    # Work: 9.5, 0.5, and 1.233 to the reply. Wait: 10.001 to the enqueue.
    assert times(build) == (11.2, 10.0)


def plugin_copy(tmp_path: Path, manifest: str | None) -> Path:
    """Copy the hook into a plugin folder whose `plugin.json` holds `manifest`.

    With None, the plugin has no `plugin.json`. Return the copied hook.
    """
    root = tmp_path / "plugin"
    (root / "hooks").mkdir(parents=True, exist_ok=True)
    hook = root / "hooks" / HOOK.name
    hook.write_bytes(HOOK.read_bytes())
    set_manifest(hook, manifest)
    return hook


def set_manifest(hook: Path, manifest: str | None) -> None:
    """Write, or with None remove, the `plugin.json` of a copied hook's plugin."""
    path = hook.parents[1] / ".claude-plugin" / "plugin.json"
    path.parent.mkdir(exist_ok=True)
    if manifest is None:
        path.unlink(missing_ok=True)
    else:
        path.write_text(manifest, "utf-8")


def release(version: str) -> str:
    """Return a `plugin.json` with a version."""
    return json.dumps({"name": "craft", "version": version})


def versions(tmp_path: Path) -> list[str | None]:
    """Return the craft version of each uploaded segment."""
    return [s["craft_version"] for s in metadata(tmp_path)["segments"]]


def versioned_env(tmp_path: Path) -> dict[str, str]:
    """Return a configured environment where every Stop uploads."""
    return {**configured_env(tmp_path), "CRAFT_GCS_STOP_INTERVAL": "0"}


def test_craft_version_comes_from_plugin_json(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """Each segment gets the version in the hook's own plugin."""
    hook = plugin_copy(tmp_path, release("3.1.4"))
    run_hook(versioned_env(tmp_path), transcript, project, hook=hook)
    wait_for_uploads(tmp_path, 1)

    assert versions(tmp_path) == ["3.1.4", "3.1.4", "3.1.4"]


@pytest.mark.parametrize(
    "manifest",
    [
        None,
        "{not json",
        json.dumps({"name": "craft"}),
        json.dumps({"name": "craft", "version": 3}),
        json.dumps(["2.9.0"]),
    ],
)
def test_unknown_craft_version_is_null_until_known(
    tmp_path: Path, project: Path, transcript: Path, manifest: str | None
) -> None:
    """A missing or broken `plugin.json` gives null and stores nothing."""
    env = versioned_env(tmp_path)
    hook = plugin_copy(tmp_path, manifest)
    run_hook(env, transcript, project, hook=hook)
    wait_for_uploads(tmp_path, 1)
    assert versions(tmp_path) == [None, None, None]

    set_manifest(hook, release("3.1.4"))
    run_hook(env, transcript, project, hook=hook)
    wait_for_uploads(tmp_path, 2)
    assert versions(tmp_path) == ["3.1.4", "3.1.4", "3.1.4"]


def test_a_release_during_a_session_keeps_earlier_versions(
    tmp_path: Path, project: Path
) -> None:
    """Segments keep the version of their first upload; new ones get the new one."""
    env = versioned_env(tmp_path)
    session = tmp_path / "long.jsonl"
    build = [in_dir(project, reply(1, "m1", SONNET, 9, skill("craft:build")))]
    write_jsonl(session, build)
    hook = plugin_copy(tmp_path, release("3.1.4"))
    run_hook(env, session, project, hook=hook)
    wait_for_uploads(tmp_path, 1)

    write_jsonl(session, [*build, reply(5, "m2", OPUS, 9, skill("craft:review"))])
    set_manifest(hook, release("3.2.0"))
    run_hook(env, session, project, hook=hook)
    wait_for_uploads(tmp_path, 2)
    assert versions(tmp_path) == ["3.1.4", "3.2.0"]

    for manifest in ("{not json", release("4.0.0")):
        set_manifest(hook, manifest)
        run_hook(env, session, project, hook=hook)
    wait_for_uploads(tmp_path, 4)
    assert versions(tmp_path) == ["3.1.4", "3.2.0"]


def test_a_lost_store_takes_the_current_version(
    tmp_path: Path, project: Path, transcript: Path
) -> None:
    """In a new container, with no stored version, segments get the current one."""
    env = versioned_env(tmp_path)
    hook = plugin_copy(tmp_path, release("3.1.4"))
    run_hook(env, transcript, project, hook=hook)
    wait_for_uploads(tmp_path, 1)

    state = tmp_path / "tmp" / "craft-transcripts"
    for stored in state.glob(f"{SESSION}.*"):
        if stored.suffix != ".log":
            stored.unlink()
    set_manifest(hook, release("3.2.0"))
    run_hook(env, transcript, project, hook=hook)
    wait_for_uploads(tmp_path, 2)

    assert versions(tmp_path) == ["3.2.0", "3.2.0", "3.2.0"]


# A spec session splits per ticket on moves to Specifying (CRAFT-73).


def session_with(
    tmp_path: Path, project: Path, lines: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Run the hook on a session in the project, and return its metadata."""
    session = tmp_path / "session.jsonl"
    write_jsonl(session, [in_dir(project, lines[0]), *lines[1:]])
    run_hook(configured_env(tmp_path), session, project)
    wait_for_uploads(tmp_path, 1)
    return metadata(tmp_path)["segments"]


def spec_session(
    tmp_path: Path, project: Path, lines: list[dict[str, Any]]
) -> list[tuple[str, str]]:
    """Run a spec session on PLAN with `lines` from minute 2, return (step, ticket)."""
    first = reply(1, "m1", OPUS, 1, skill("craft:spec", PLAN))
    segments = session_with(tmp_path, project, [first, *lines])
    return [(s["step"], s["ticket"]) for s in segments]


def test_one_shot_spec_session_charges_each_ticket(
    tmp_path: Path, project: Path
) -> None:
    """Each ticket's span is its own segment; the work in between goes to the plan."""
    scout = {
        "type": "tool_use",
        "id": "call-scout",
        "name": "Agent",
        "input": {"description": "spec scout"},
    }
    lines = [
        prompt(0, f"Run craft:spec on the one-shot plan {PLAN}."),
        reply(1, "m1", OPUS, 1, skill("craft:spec")),
        *move(2, A, "Specifying"),
        reply(4, "m4", OPUS, 30, scout),
        {
            "type": "user",
            "timestamp": stamp(6),
            "toolUseResult": {"agentId": "s1"},
            "message": {
                "content": [{"type": "tool_result", "tool_use_id": "call-scout"}]
            },
        },
        *move(7, A, "Ready to build"),
        reply(9, "m9", OPUS, 5, skill("craft:next")),
        *move(10, B, "Specifying"),
        reply(12, "m12", OPUS, 7, {"type": "text", "text": "Grill B."}),
    ]
    session = tmp_path / "one-shot.jsonl"
    write_jsonl(session, [in_dir(project, lines[0]), *lines[1:]])
    subagents = tmp_path / "one-shot" / "subagents"
    subagents.mkdir(parents=True)
    write_jsonl(subagents / "agent-s1.jsonl", [reply(5, "x1", OPUS, 50)])
    run_hook(configured_env(tmp_path), session, project)
    wait_for_uploads(tmp_path, 1)

    data = metadata(tmp_path)
    segments = data["segments"]
    assert [(s["step"], s["ticket"]) for s in segments] == [
        ("spec", PLAN),
        ("spec", A),
        ("spec", PLAN),
        ("next", PLAN),
        ("spec", B),
    ]
    assert data["tickets"] == sorted([A, B, PLAN])
    assert [s["started_at"] for s in segments] == [
        stamp(1),
        stamp(3),
        stamp(8),
        stamp(9),
        stamp(11),
    ]
    spec_a = segments[1]
    # The reply that moves A out still counts toward A: its result starts the next.
    assert spec_a["tokens"] == tokens(OPUS, 31, 2)
    assert [s["agent_id"] for s in spec_a["subagents"]] == ["s1"]
    assert spec_a["subagents"][0]["role"] == "spec scout"
    assert segments[4]["tokens"] == tokens(OPUS, 7, 1)


@pytest.mark.parametrize(
    "case",
    [
        (A, f"Run craft:spec on the one-shot plan {PLAN}.", "", A),
        ("", f"Run craft:spec on the one-shot plan {PLAN}.", "", PLAN),
        ("", "<session-context>…</session-context> one-shot plan CRAFT-40", "", PLAN),
        ("", "Spec the next ticket.", f"one-shot plan {B}", BRANCH_TICKET),
        ("", "", "", BRANCH_TICKET),
    ],
    ids=[
        "arguments",
        "one-shot prompt",
        "cloud thread prompt",
        "prompt after the call",
        "branch",
    ],
)
def test_session_ticket(
    tmp_path: Path, project: Path, case: tuple[str, str, str, str]
) -> None:
    """The first spec call's key, else the one-shot prompt's, else the branch's."""
    args, before, after, expected = case
    first = prompt(0, before)
    if before.startswith("<session-context>"):
        # A cloud project thread writes its first prompt as an `isMeta` line.
        first["isMeta"] = True
    lines = [first] if before else []
    lines += [reply(1, "m1", OPUS, 1, skill("craft:spec", args))]
    lines += [prompt(2, after)] if after else []
    lines += [reply(3, "m3", OPUS, 1, skill("craft:design"))]
    segments = session_with(tmp_path, project, lines)

    assert [(s["step"], s["ticket"]) for s in segments] == [
        ("spec", expected),
        ("design", expected),
    ]


SESSION_SPEC = ("spec", PLAN)

PATHS = {
    "session ticket, move of another ticket in": (
        move(2, A, "Specifying"),
        [SESSION_SPEC, ("spec", A)],
    ),
    "session ticket, move of itself in": (
        move(2, PLAN, "Specifying"),
        [SESSION_SPEC],
    ),
    "session ticket, move of itself out": (
        move(2, PLAN, "Ready to build"),
        [SESSION_SPEC],
    ),
    "session ticket, move of another ticket out": (
        move(2, A, "Todo"),
        [SESSION_SPEC],
    ),
    "current ticket to Ready to build": (
        [*move(2, A, "Specifying"), *move(4, A, "Ready to build")],
        [SESSION_SPEC, ("spec", A), SESSION_SPEC],
    ),
    "current ticket to Needs human": (
        [*move(2, A, "Specifying"), *move(4, A, "Needs human")],
        [SESSION_SPEC, ("spec", A), SESSION_SPEC],
    ),
    "current ticket back to Todo": (
        [*move(2, A, "Specifying"), *move(4, A, "Todo")],
        [SESSION_SPEC, ("spec", A), SESSION_SPEC],
    ),
    "current ticket, move of another ticket in": (
        [*move(2, A, "Specifying"), *move(4, B, "Specifying")],
        [SESSION_SPEC, ("spec", A), ("spec", B)],
    ),
    "move in after a design call": (
        [
            *move(2, A, "Specifying"),
            reply(4, "m4", OPUS, 1, skill("craft:design")),
            *move(5, B, "Specifying"),
        ],
        [SESSION_SPEC, ("spec", A), ("design", A), ("spec", B)],
    ),
    "current ticket, move of itself in again": (
        [*move(2, A, "Specifying"), *move(4, A, "specifying")],
        [SESSION_SPEC, ("spec", A)],
    ),
    "current ticket, move of another ticket out": (
        [*move(2, A, "Specifying"), *move(4, B, "Todo")],
        [SESSION_SPEC, ("spec", A)],
    ),
    "same ticket twice": (
        [
            *move(2, A, "Specifying"),
            *move(4, A, "Ready to build"),
            *move(6, A, "Specifying"),
        ],
        [SESSION_SPEC, ("spec", A), SESSION_SPEC, ("spec", A)],
    ),
    "failed move": (
        move(2, A, "Specifying", error=True),
        [SESSION_SPEC],
    ),
    "failed move out": (
        [*move(2, A, "Specifying"), *move(4, A, "Todo", error=True)],
        [SESSION_SPEC, ("spec", A)],
    ),
    "move with a state id": (
        move(2, A, STATE_ID),
        [SESSION_SPEC],
    ),
    "move of an id that is no key": (
        move(2, "04923b2d-0105", "Specifying", result_id="04923b2d-0105"),
        [SESSION_SPEC],
    ),
    "move of an id with the key in the result": (
        move(2, "04923b2d-0105", "Specifying", result_id=A),
        [SESSION_SPEC, ("spec", A)],
    ),
    "move with update_issue": (
        move(2, A, "Specifying", name="mcp__linear__update_issue"),
        [SESSION_SPEC, ("spec", A)],
    ),
    "a call of another tool": (
        move(2, A, "Specifying", name="mcp__Linear__get_issue"),
        [SESSION_SPEC],
    ),
    "step call without a key": (
        [
            *move(2, A, "Specifying"),
            reply(4, "m4", OPUS, 1, skill("craft:spec")),
            reply(5, "m5", OPUS, 1, skill("craft:next")),
        ],
        [SESSION_SPEC, ("spec", A), ("spec", A), ("next", A)],
    ),
    "step call with a key": (
        [
            *move(2, A, "Specifying"),
            reply(4, "m4", OPUS, 1, skill("craft:design", B)),
            reply(5, "m5", OPUS, 1, skill("craft:next")),
        ],
        [SESSION_SPEC, ("spec", A), ("design", B), ("next", A)],
    ),
}


@pytest.mark.parametrize(("lines", "expected"), PATHS.values(), ids=PATHS.keys())
def test_spec_session_paths(
    tmp_path: Path,
    project: Path,
    lines: list[dict[str, Any]],
    expected: list[tuple[str, str]],
) -> None:
    """Each path of the current ticket in a spec session gives its segments."""
    assert spec_session(tmp_path, project, lines) == expected


@pytest.mark.parametrize(("step", "args"), [("plan", ""), ("plan", PLAN), ("build", A)])
def test_other_sessions_do_not_split(
    tmp_path: Path, project: Path, step: str, args: str
) -> None:
    """A session that does not start with a spec ignores moves to Specifying."""
    lines = [
        reply(1, "m1", OPUS, 1, skill(f"craft:{step}", args)),
        *move(2, PLAN, "Specifying"),
        *move(4, A, "Specifying"),
        reply(6, "m6", OPUS, 1, skill("craft:next")),
    ]
    segments = session_with(tmp_path, project, lines)

    assert [(s["step"], s["ticket"]) for s in segments] == [
        (step, args or BRANCH_TICKET),
        ("next", BRANCH_TICKET),
    ]


# A brainstorm or setup segment records its brief (CRAFT-73).

BRIEF_URL = (
    "https://linear.app/clearblocks/document/brief-craft-console-v1-959b353787a7"
)
DEV_URL = "https://linear.app/clearblocks/document/brief-dev-environment-0a1b2c3d"


def save(
    minute: int,
    result: dict[str, Any] | str,
    *,
    doc_id: str | None = None,
    error: bool = False,
    name: str = "mcp__Linear__save_document",
) -> list[dict[str, Any]]:
    """Return a document save, with an `id` when it changes a document."""
    call_id = f"save-{minute}"
    tool_input: dict[str, Any] = {"title": "Brief", "content": "..."}
    if doc_id is not None:
        tool_input["id"] = doc_id
    return [
        tool_call(minute, call_id, name, tool_input),
        call_result(minute + 1, call_id, result, error=error),
    ]


def brief(title: str, url: str) -> dict[str, Any]:
    """Return the result of a document save."""
    return {"id": "doc", "title": title, "url": url}


BRIEFS = {
    "created brief": (
        "brainstorm",
        save(2, brief("Brief: Craft Console v1", BRIEF_URL)),
        BRIEF_URL,
    ),
    "setup brief with create_document": (
        "setup",
        save(2, brief("Brief: Dev environment", DEV_URL), name="create_document"),
        DEV_URL,
    ),
    "a created brief wins over a changed one": (
        "setup",
        [
            *save(2, brief("Brief: Dev environment", DEV_URL)),
            *save(4, brief("Brief: Craft Console v1", BRIEF_URL), doc_id="d1"),
        ],
        DEV_URL,
    ),
    "the last of two changed briefs": (
        "brainstorm",
        [
            *save(2, brief("Brief: Dev environment", DEV_URL), doc_id="d1"),
            *save(4, brief("Brief: Craft Console v1", BRIEF_URL), doc_id="d2"),
        ],
        BRIEF_URL,
    ),
    "the last of two created briefs": (
        "brainstorm",
        [
            *save(2, brief("Brief: Dev environment", DEV_URL)),
            *save(4, brief("Brief: Craft Console v1", BRIEF_URL)),
        ],
        BRIEF_URL,
    ),
    "a failed save, then a good one": (
        "brainstorm",
        [
            *save(2, brief("Brief: Dev environment", DEV_URL), doc_id="d", error=True),
            *save(4, brief("Brief: Craft Console v1", BRIEF_URL), doc_id="d"),
        ],
        BRIEF_URL,
    ),
    "only a failed save": (
        "setup",
        save(2, brief("Brief: Dev environment", DEV_URL), error=True),
        None,
    ),
    "a document that is no brief": (
        "brainstorm",
        save(2, brief("Plan: Craft Console v1", BRIEF_URL)),
        None,
    ),
    "a result that is not JSON": (
        "brainstorm",
        save(2, "Saved the document."),
        None,
    ),
    "a result without a url": (
        "brainstorm",
        save(2, {"title": "Brief: Craft Console v1", "url": 3}),
        None,
    ),
    "a read of a brief": (
        "brainstorm",
        save(2, brief("Brief: Craft Console v1", BRIEF_URL), name="get_document"),
        None,
    ),
    "a brief saved in another step": (
        "plan",
        save(2, brief("Brief: Craft Console v1", BRIEF_URL)),
        None,
    ),
}


@pytest.mark.parametrize(
    ("step", "lines", "expected"), BRIEFS.values(), ids=BRIEFS.keys()
)
def test_brief_of_a_segment(
    tmp_path: Path,
    project: Path,
    step: str,
    lines: list[dict[str, Any]],
    expected: str | None,
) -> None:
    """A brainstorm or setup segment holds the URL of the brief that it saved."""
    first = reply(1, "m1", OPUS, 1, skill(f"craft:{step}"))
    segments = session_with(tmp_path, project, [first, *lines])

    assert [s["brief"] for s in segments] == [expected]


def test_brief_belongs_to_the_segment_that_saved_it(
    tmp_path: Path, project: Path
) -> None:
    """A brief saved in setup does not go to the brainstorm before it."""
    lines = [
        reply(1, "m1", OPUS, 1, skill("craft:brainstorm")),
        *save(2, brief("Brief: Craft Console v1", BRIEF_URL)),
        reply(4, "m4", OPUS, 1, skill("craft:setup")),
        *save(5, brief("Brief: Dev environment", DEV_URL)),
        reply(7, "m7", OPUS, 1, skill("craft:plan")),
    ]
    segments = session_with(tmp_path, project, lines)

    assert [(s["step"], s["brief"]) for s in segments] == [
        ("brainstorm", BRIEF_URL),
        ("setup", DEV_URL),
        ("plan", None),
    ]
