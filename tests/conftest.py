# Copyright (C) 2026 Theo van Oostrum
"""Fixtures for the tests of the upload hook and the re-process command."""

from pathlib import Path

import pytest

from tests.transcripts import (
    OPUS,
    SECRET,
    SESSION,
    SONNET,
    git_repo,
    in_dir,
    reply,
    skill,
    stamp,
    write_jsonl,
)


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Return a git checkout on a ticket branch, with a GitHub `origin`."""
    return git_repo(
        tmp_path / "checkout",
        "librag-12/version-endpoint",
        "https://github.com/vanoostrum/librag.git",
    )


@pytest.fixture
def outside(tmp_path: Path) -> Path:
    """Return a folder that is not inside a git repo, such as `/home/user`."""
    folder = tmp_path / "home"
    folder.mkdir()
    return folder


@pytest.fixture
def transcript(tmp_path: Path, project: Path, outside: Path) -> Path:
    """Return a build session: build, review, and merge, with two subagents.

    The session starts outside any repo and then works in the project. Subagent
    a1 is linked to its `Agent` call. Subagent b2 is not, and wrote its first
    line during the review.
    """
    sessions = tmp_path / "sessions"
    main = sessions / f"{SESSION}.jsonl"
    subagents = sessions / SESSION / "subagents"
    subagents.mkdir(parents=True)
    agent_call = {
        "type": "tool_use",
        "id": "call-agent",
        "name": "Agent",
        "input": {"description": "app driver", "subagent_type": "general-purpose"},
    }
    first = {
        "type": "user",
        "timestamp": stamp(0),
        "message": {"content": f"key {SECRET}, token proxy-injected"},
    }
    write_jsonl(
        main,
        [
            in_dir(outside, first),
            # One reply written as two lines, each with the same usage.
            reply(1, "m1", SONNET, 100, {"type": "text", "text": "Building."}),
            reply(1, "m1", SONNET, 100, skill("craft:build", "LIBRAG-12")),
            # Loading the rules, or any other craft skill, starts no segment.
            reply(1, "m1", SONNET, 100, skill("craft:rules")),
            reply(2, "m2", SONNET, 20, agent_call),
            {
                "type": "user",
                "timestamp": stamp(5),
                "toolUseResult": {"agentId": "a1"},
                "message": {
                    "content": [{"type": "tool_result", "tool_use_id": "call-agent"}]
                },
            },
            in_dir(
                project, reply(10, "m3", OPUS, 300, skill("craft:review", "LIBRAG-12"))
            ),
            reply(20, "m4", OPUS, 7, skill("craft:merge")),
            reply(21, "m5", OPUS, 5, {"type": "text", "text": "Merged."}),
        ],
    )
    write_jsonl(subagents / "agent-a1.jsonl", [reply(3, "s1", SONNET, 40)])
    (subagents / "agent-a1.meta.json").write_text('{"agentType": "general"}', "utf-8")
    write_jsonl(subagents / "agent-b2.jsonl", [reply(12, "s2", OPUS, 50)])
    return main
