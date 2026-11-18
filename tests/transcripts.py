# Copyright (C) 2026 Theo van Oostrum
"""Helpers for the tests of the upload hook and the re-process command.

A fake `gcloud` on `PATH` stands in for Google Cloud. Its bucket is a local
folder, so the tests can read what would land in the bucket.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "plugins" / "craft" / "hooks"
HOOK = HOOKS / "upload_transcripts.py"
SESSION = "0b1c2d3e-session"
SECRET = "sk-test-0123456789abcdef"  # noqa: S105 - a fake secret to redact.
KEY = {"type": "service_account", "client_email": "factory@example.iam"}
OPUS = "claude-opus"
SONNET = "claude-sonnet"

FAKE_GCLOUD = r"""#!/bin/sh
echo "$* token=${CLOUDSDK_AUTH_ACCESS_TOKEN:-none}" >> "$FAKE_GCLOUD_LOG"
root="$FAKE_BUCKET_ROOT"
case "$1 $2" in
"storage rsync")
  case "$3" in
  gs://*) mkdir -p "$4" && cp -R "$root/${3#gs://}"/. "$4"/ ;;
  *) dest="$root/${4#gs://}" && mkdir -p "$dest" && cp -R "$3"/. "$dest"/ ;;
  esac ;;
"storage ls")
  # Only the form `gs://<bucket>/**`: every object of the bucket.
  folder="$root/${3#gs://}" && folder="${folder%/\*\*}"
  [ -d "$folder" ] || { echo "ERROR: $3 matched no objects" >&2; exit 1; }
  find "$folder" -type f | sort | sed "s|^$root/|gs://|" ;;
"storage cat")
  cat "$root/${3#gs://}" ;;
"storage cp")
  dest="$root/${4#gs://}" && mkdir -p "$(dirname "$dest")" && cp "$3" "$dest" ;;
esac
"""


def stamp(minute: int) -> str:
    """Return a transcript timestamp at a minute past 10:00."""
    return f"2026-11-02T10:{minute:02d}:00.000Z"


def reply(
    minute: int, message_id: str, model: str, tokens: int, *content: dict[str, Any]
) -> dict[str, Any]:
    """Return an assistant line with its token usage."""
    usage = {
        "input_tokens": tokens,
        "output_tokens": 1,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
    }
    return {
        "type": "assistant",
        "timestamp": stamp(minute),
        "message": {
            "id": message_id,
            "model": model,
            "usage": usage,
            "content": list(content),
        },
    }


def skill(name: str, args: str = "") -> dict[str, Any]:
    """Return a Skill tool call block."""
    return {
        "type": "tool_use",
        "id": f"call-{name}",
        "name": "Skill",
        "input": {"skill": name, "args": args},
    }


def write_jsonl(path: Path, lines: list[dict[str, Any]]) -> None:
    """Write transcript lines to a file."""
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), "utf-8")


def git_repo(path: Path, branch: str, origin: str | None) -> Path:
    """Create a git checkout at `path` on `branch`, with an `origin` remote."""
    path.mkdir(parents=True)
    subprocess.run(  # noqa: S603
        ["git", "init", "-q", "-b", branch, str(path)],  # noqa: S607
        check=True,
    )
    if origin is not None:
        subprocess.run(  # noqa: S603
            ["git", "-C", str(path), "remote", "add", "origin", origin],  # noqa: S607
            check=True,
        )
    return path


def in_dir(cwd: Path, line: dict[str, Any]) -> dict[str, Any]:
    """Return a transcript line with the working directory Claude Code records."""
    return {**line, "cwd": str(cwd)}


def fake_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    """Return an environment whose `gcloud` is the fake one."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    gcloud = bin_dir / "gcloud"
    gcloud.write_text(FAKE_GCLOUD, encoding="utf-8")
    gcloud.chmod(0o755)
    temp = tmp_path / "tmp"
    temp.mkdir(exist_ok=True)
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("CRAFT_GCS_", "SOUS_GCS_"))
    }
    env.update(
        PATH=f"{bin_dir}{os.pathsep}{env['PATH']}",
        TMPDIR=str(temp),
        FAKE_GCLOUD_LOG=str(tmp_path / "gcloud.log"),
        FAKE_BUCKET_ROOT=str(tmp_path / "gcs"),
        OPENAI_API_KEY=SECRET,
        CLOUDSDK_AUTH_ACCESS_TOKEN="proxy-injected",  # noqa: S106 - as in the sandbox.
        **extra,
    )
    return env


def configured_env(tmp_path: Path, key: str = json.dumps(KEY)) -> dict[str, str]:
    """Return an environment with a bucket and a service account key."""
    return fake_env(tmp_path, CRAFT_GCS_BUCKET="factory-logs", CRAFT_GCS_KEY=key)


def run_hook(
    env: dict[str, str],
    transcript: Path,
    cwd: Path,
    event: str = "Stop",
    hook: Path = HOOK,
) -> None:
    """Run the hook as Claude Code does."""
    payload = {
        "session_id": SESSION,
        "transcript_path": str(transcript),
        "cwd": str(cwd),
        "hook_event_name": event,
    }
    subprocess.run(  # noqa: S603
        [sys.executable, str(hook)],
        input=json.dumps(payload),
        text=True,
        env=env,
        check=True,
        timeout=10,
    )


def wait_for_uploads(tmp_path: Path, count: int) -> None:
    """Wait until the background process has logged `count` uploads."""
    upload_log = tmp_path / "tmp" / "craft-transcripts" / "upload.log"
    deadline = time.monotonic() + 20
    while True:
        text = upload_log.read_text("utf-8") if upload_log.exists() else ""
        if text.count(" uploaded ") >= count:
            return
        if " failed " in text or time.monotonic() > deadline:
            pytest.fail(f"the upload did not finish: {text!r}")
        time.sleep(0.1)


def session_folder(tmp_path: Path, repo: str = "vanoostrum/librag") -> Path:
    """Return the session's folder in the fake bucket."""
    return tmp_path / "gcs" / "factory-logs" / repo / "sessions" / SESSION


def metadata(tmp_path: Path, repo: str = "vanoostrum/librag") -> dict[str, Any]:
    """Return the uploaded metadata of the session."""
    path = session_folder(tmp_path, repo) / "metadata.json"
    return json.loads(path.read_text("utf-8"))


PLAN = "CRAFT-40"
A = "CRAFT-41"
B = "CRAFT-42"
SAVE_ISSUE = "mcp__Linear__save_issue"


def tool_call(
    minute: int, call_id: str, name: str, tool_input: dict[str, Any]
) -> dict[str, Any]:
    """Return an assistant line that calls a tool, such as a Linear tool."""
    block = {"type": "tool_use", "id": call_id, "name": name, "input": tool_input}
    return reply(minute, f"r-{call_id}", OPUS, 1, block)


def call_result(
    minute: int, call_id: str, result: dict[str, Any] | str, *, error: bool = False
) -> dict[str, Any]:
    """Return the user line with a tool's result, as a text block of JSON."""
    text = result if isinstance(result, str) else json.dumps(result)
    block: dict[str, Any] = {
        "type": "tool_result",
        "tool_use_id": call_id,
        "content": [{"type": "text", "text": text}],
    }
    if error:
        block["is_error"] = True
    return {"type": "user", "timestamp": stamp(minute), "message": {"content": [block]}}


def move(  # noqa: PLR0913 - a move and its result, with their options.
    minute: int,
    ticket: str,
    state: str,
    *,
    result_id: str | None = None,
    error: bool = False,
    name: str = SAVE_ISSUE,
) -> list[dict[str, Any]]:
    """Return a Linear call that moves a ticket, and its result a minute later."""
    call_id = f"move-{minute}"
    result = {"id": result_id or ticket, "status": state}
    return [
        tool_call(minute, call_id, name, {"id": ticket, "state": state}),
        call_result(minute + 1, call_id, result, error=error),
    ]


def prompt(minute: int, text: str) -> dict[str, Any]:
    """Return a prompt that the owner, or `craft:next`, types."""
    return {"type": "user", "timestamp": stamp(minute), "message": {"content": text}}
