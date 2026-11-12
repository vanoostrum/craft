# Copyright (C) 2026 Theo van Oostrum
"""Stop, SubagentStop, and SessionEnd hook: copy transcripts to Google Cloud Storage.

The transcripts are for evaluating and improving the craft steps, so the hook
uploads only a session that runs a step: a call of `craft:brainstorm`,
`craft:setup`, `craft:plan`, `craft:spec`, `craft:design`, `craft:build`,
`craft:review`, `craft:merge`, or `craft:next`, as a Skill call or as a slash
command that the owner types. Such a session uploads in full, from its first
line. Other craft skills, such as `craft:rules`, are no step.

`CRAFT_GCS_BUCKET` names the bucket. The hook signs in to Google Cloud in one
of two ways, and does nothing when neither is there:

- In a cloud session, a "GCP access token" network secret for
  `storage.googleapis.com` lets the proxy add the access token. The sandbox
  marks this with `CLOUDSDK_AUTH_ACCESS_TOKEN=proxy-injected`. The key never
  enters the container.
- Elsewhere, `CRAFT_GCS_KEY` holds a service account key, as JSON or base64
  JSON.

The hook returns at once and uploads in a background process, so a turn does
not wait for Google Cloud. Each upload writes the whole session to the same
folder, so the bucket always holds the latest state:

    gs://<bucket>/<owner>/<repo>/sessions/<session id>/
        session.jsonl.gz
        subagents/<agent>.jsonl.gz
        metadata.json

`<owner>/<repo>` is the last two path segments of the `origin` remote URL of
the session's repo: the first working directory in the transcript that is
inside a git repo with such a remote. It comes from the transcript, not from
the hook's own directory, so every upload of a session goes to one folder. A
session without such a repo goes to `no-repo/`. `metadata.json` has the same
value in `repo`, and the branch of that repo in `branch`.

`metadata.json` splits the session into segments. Each step call starts a
segment. A segment has its step, its ticket, its start and end time, its
tokens per model, and its subagents with their own tokens.

- The ticket of a segment comes from the step's arguments, such as `ABC-12`,
  or else from the branch name, such as `abc-12/version-endpoint`.
- A subagent belongs to the segment whose `Agent` call started it. When the
  transcript does not link the two, it belongs to the segment that was running
  when the subagent wrote its first line.
- A Stop upload is skipped when the last upload of the session is less than
  `CRAFT_GCS_STOP_INTERVAL` seconds old (default 300). SubagentStop and
  SessionEnd always upload.
- One upload per session runs at a time. The next one waits for it.
- The gzip files have a fixed timestamp, so an unchanged file has the same
  bytes, and `gcloud storage rsync` skips it.

Secret environment values are replaced before upload. The background process
logs each upload, or its error, to `craft-transcripts/upload.log` in the
temp folder.

The service account needs only the Storage Object User role on the bucket.
"""

import base64
import binascii
import contextlib
import fcntl
import gzip
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BUCKET_ENV = "CRAFT_GCS_BUCKET"
KEY_ENV = "CRAFT_GCS_KEY"
TOKEN_ENV = "CLOUDSDK_AUTH_ACCESS_TOKEN"  # noqa: S105 - a variable name.
PROXY_TOKEN = "proxy-injected"  # noqa: S105 - a marker, not a secret.
INTERVAL_ENV = "CRAFT_GCS_STOP_INTERVAL"
DEFAULT_STOP_INTERVAL = 300.0
UPLOAD_FLAG = "--upload"
TICKET_BRANCH = re.compile(r"^([a-z]+)-(\d+)/")
TICKET_KEY = re.compile(r"\b[A-Z][A-Z0-9]*-\d+\b")
STEP_SKILL = re.compile(
    r"^craft:(brainstorm|setup|plan|spec|design|build|review|merge|next)$"
)
SLASH_COMMAND = re.compile(
    r"<command-name>/?(?P<name>[^<]*)</command-name>"
    r"(?:\s*<command-args>(?P<args>[^<]*)</command-args>)?"
)
NO_REPO = "no-repo"
SECRET_NAME = re.compile(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", re.IGNORECASE)
MIN_SECRET_LENGTH = 8
AGENT_TOOLS = {"Agent", "Task"}
USAGE_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)

Tokens = dict[str, dict[str, int]]


def state_dir() -> Path:
    """Return the folder for the log, the locks, and the last upload times."""
    folder = Path(tempfile.gettempdir()) / "craft-transcripts"
    folder.mkdir(exist_ok=True)
    return folder


def setting(name: str) -> str:
    """Return a `CRAFT_GCS_*` variable, or "" when it is not set."""
    return os.environ.get(name, "")


def git(cwd: str, *args: str) -> str:
    """Return the output of a git command, or "" when it fails."""
    result = subprocess.run(  # noqa: S603
        ["git", "-C", cwd, *args],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else ""


def owner_repo(url: str) -> str | None:
    """Return `<owner>/<repo>` from the last two path segments of a remote URL.

    Works for HTTPS, SSH (`git@host:owner/repo.git`), and proxy URLs with more
    segments in front. Returns None when the path has fewer than two segments.
    """
    rest = re.sub(r"^[A-Za-z][A-Za-z0-9+.-]*://", "", url.strip())
    path = [part for part in re.split(r"[/:]", rest)[1:] if part]
    if len(path) < 2:  # noqa: PLR2004 - an owner and a repo.
        return None
    return f"{path[-2]}/{path[-1].removesuffix('.git')}"


@dataclass
class Repo:
    """The repo a session works in: its `<owner>/<repo>` and its checkout."""

    name: str
    toplevel: str | None


def session_repo(path: Path) -> Repo:
    """Return the first repo with an `origin` remote in the transcript's cwds."""
    seen: set[str] = set()
    for entry in entries(path):
        cwd = entry.get("cwd")
        if not isinstance(cwd, str) or cwd in seen:
            continue
        seen.add(cwd)
        toplevel = git(cwd, "rev-parse", "--show-toplevel")
        name = owner_repo(git(cwd, "remote", "get-url", "origin")) if toplevel else None
        if name is not None:
            return Repo(name, toplevel)
    return Repo(NO_REPO, None)


def ticket_of(branch: str) -> str | None:
    """Return the ticket key of a ticket branch, or None."""
    match = TICKET_BRANCH.match(branch)
    if match is None:
        return None
    return f"{match.group(1).upper()}-{match.group(2)}"


def secrets() -> dict[str, str]:
    """Return the environment values that look like secrets, by name."""
    return {
        name: value
        for name, value in os.environ.items()
        if SECRET_NAME.search(name)
        and len(value) >= MIN_SECRET_LENGTH
        and value != PROXY_TOKEN
    }


def redact(text: str, values: dict[str, str]) -> str:
    """Replace each secret value in `text` with its variable name."""
    for name, value in sorted(values.items(), key=lambda item: -len(item[1])):
        text = text.replace(value, f"[redacted:{name}]")
    return text


def key_json(raw: str) -> str:
    """Return the service account key as JSON, decoding base64 if needed."""
    if raw.lstrip().startswith("{"):
        return raw
    try:
        return base64.b64decode(raw, validate=True).decode()
    except (binascii.Error, UnicodeDecodeError):
        return raw


def transcripts(transcript: Path) -> dict[str, Path]:
    """Return the session transcript and its subagent transcripts, by upload name."""
    found = {"session.jsonl": transcript} if transcript.is_file() else {}
    folder = transcript.with_suffix("")
    if folder.is_dir():
        for pattern in ("*.jsonl", "*.meta.json"):
            for path in sorted(folder.rglob(pattern)):
                found[str(path.relative_to(folder))] = path
    return found


def entries(path: Path) -> Iterator[dict[str, Any]]:
    """Yield the JSON objects of a transcript, skipping broken lines."""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            yield entry


def blocks(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the content blocks of a transcript entry."""
    content = (entry.get("message") or {}).get("content")
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def add_usage(tokens: Tokens, model: str, usage: dict[str, Any]) -> None:
    """Add one reply's token usage to the totals of its model."""
    totals = tokens.setdefault(model, dict.fromkeys(USAGE_FIELDS, 0))
    for name in USAGE_FIELDS:
        value = usage.get(name)
        if isinstance(value, int):
            totals[name] += value


def usage_by_reply(path: Path) -> dict[str, tuple[str, str, dict[str, Any]]]:
    """Return each reply's timestamp, model, and usage, by message id.

    Claude Code writes one reply as several lines, one per content block, and
    repeats the usage on each. Keying by message id counts each reply once.
    """
    replies: dict[str, tuple[str, str, dict[str, Any]]] = {}
    for number, entry in enumerate(entries(path)):
        message = entry.get("message") or {}
        usage = message.get("usage")
        if entry.get("type") != "assistant" or not isinstance(usage, dict):
            continue
        key = message.get("id") or f"line-{number}"
        replies[key] = (entry.get("timestamp") or "", message.get("model") or "", usage)
    return replies


@dataclass
class Subagent:
    """A subagent transcript and its totals."""

    agent_id: str
    role: str | None
    started_at: str | None
    ended_at: str | None
    tokens: Tokens = field(default_factory=dict)


@dataclass
class Segment:
    """The part of a session that one craft step ran."""

    step: str | None
    ticket: str | None
    started_at: str | None
    ended_at: str | None = None
    tokens: Tokens = field(default_factory=dict)
    subagents: list[Subagent] = field(default_factory=list)
    agent_calls: dict[str, str | None] = field(default_factory=dict)


def failed_calls(path: Path) -> set[str]:
    """Return the ids of the tool calls whose result is an error."""
    return {
        str(block.get("tool_use_id"))
        for entry in entries(path)
        for block in blocks(entry)
        if block.get("type") == "tool_result" and block.get("is_error") is True
    }


def texts(entry: dict[str, Any]) -> list[str]:
    """Return the text of a user line, as a string or as text blocks."""
    if entry.get("type") != "user":
        return []
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return [content]
    return [str(block.get("text") or "") for block in blocks(entry)]


def step_calls(entry: dict[str, Any], failed: set[str]) -> Iterator[tuple[str, str]]:
    """Yield the name and arguments of each step call in a transcript line.

    A step call is a Skill call or a slash command of a craft step. A Skill
    call that failed, such as an unknown skill, is no step call.
    """
    calls: list[tuple[str, str]] = [
        (str(command.group("name")).strip(), str(command.group("args") or ""))
        for text in texts(entry)
        for command in SLASH_COMMAND.finditer(text)
    ]
    calls += [
        (str(tool_input.get("skill") or ""), str(tool_input.get("args") or ""))
        for block in blocks(entry)
        if block.get("type") == "tool_use"
        and block.get("name") == "Skill"
        and str(block.get("id")) not in failed
        for tool_input in [block.get("input") or {}]
    ]
    for name, args in calls:
        match = STEP_SKILL.match(name)
        if match is not None:
            yield str(match.group(1)), args


def segment_starts(path: Path, branch_ticket: str | None) -> list[Segment]:
    """Return the segments of the main transcript, with their `Agent` calls."""
    failed = failed_calls(path)
    segments = [Segment(step=None, ticket=branch_ticket, started_at=None)]
    for entry in entries(path):
        stamp = entry.get("timestamp")
        for step, args in step_calls(entry, failed):
            found = TICKET_KEY.search(args)
            ticket = found.group(0) if found else branch_ticket
            segments.append(Segment(step, ticket, stamp, stamp))
        for block in blocks(entry):
            if block.get("type") == "tool_use" and block.get("name") in AGENT_TOOLS:
                tool_input = block.get("input") or {}
                role = tool_input.get("description") or tool_input.get("subagent_type")
                segments[-1].agent_calls[str(block.get("id"))] = role
        if stamp:
            segments[-1].started_at = segments[-1].started_at or stamp
            segments[-1].ended_at = stamp
    return segments


def agent_links(path: Path) -> dict[str, str]:
    """Return the `Agent` call id that started each subagent, by agent id."""
    links: dict[str, str] = {}
    for entry in entries(path):
        result = entry.get("toolUseResult")
        agent_id = result.get("agentId") if isinstance(result, dict) else None
        if not agent_id:
            continue
        for block in blocks(entry):
            if block.get("type") == "tool_result" and block.get("tool_use_id"):
                links[str(agent_id)] = str(block["tool_use_id"])
    return links


def segment_at(segments: list[Segment], stamp: str | None) -> Segment:
    """Return the segment that was running at `stamp`."""
    current = segments[0]
    for segment in segments:
        start = segment.started_at
        if stamp is not None and start is not None and start <= stamp:
            current = segment
    return current


def segment_session(transcript: Path, branch_ticket: str | None) -> list[Segment]:
    """Split a session into segments and add the tokens of each."""
    segments = segment_starts(transcript, branch_ticket)
    for stamp, model, usage in usage_by_reply(transcript).values():
        add_usage(segment_at(segments, stamp).tokens, model, usage)
    links = agent_links(transcript)
    folder = transcript.with_suffix("")
    for path in sorted(folder.rglob("agent-*.jsonl")) if folder.is_dir() else []:
        agent_id = path.stem.removeprefix("agent-")
        replies = list(usage_by_reply(path).values())
        stamps = sorted(s for s in (e.get("timestamp") for e in entries(path)) if s)
        call = links.get(agent_id)
        owner = next((s for s in segments if call in s.agent_calls), None)
        if owner is None:
            owner = segment_at(segments, stamps[0] if stamps else None)
        subagent = Subagent(
            agent_id=agent_id,
            role=owner.agent_calls.get(call) if call is not None else None,
            started_at=stamps[0] if stamps else None,
            ended_at=stamps[-1] if stamps else None,
        )
        for _, model, usage in replies:
            add_usage(subagent.tokens, model, usage)
        owner.subagents.append(subagent)
    return [s for s in segments if s.step is not None or s.tokens or s.subagents]


def segment_json(segment: Segment) -> dict[str, Any]:
    """Return a segment as it goes into `metadata.json`."""
    return {
        "step": segment.step,
        "ticket": segment.ticket,
        "started_at": segment.started_at,
        "ended_at": segment.ended_at,
        "tokens": segment.tokens,
        "subagents": [
            {
                "agent_id": subagent.agent_id,
                "role": subagent.role,
                "started_at": subagent.started_at,
                "ended_at": subagent.ended_at,
                "tokens": subagent.tokens,
            }
            for subagent in segment.subagents
        ],
    }


def stage(event: dict[str, Any], out: Path) -> str | None:
    """Write the gzipped transcripts and metadata to `out`. Return the prefix.

    Return None, and write nothing, when the session ran no craft step.
    """
    session = event.get("session_id") or "unknown-session"
    transcript = Path(event.get("transcript_path") or "")
    if not transcript.is_file():
        return None
    repo = session_repo(transcript)
    branch = (
        "" if repo.toplevel is None else git(repo.toplevel, "branch", "--show-current")
    )
    segments = segment_session(transcript, ticket_of(branch))
    if all(segment.step is None for segment in segments):
        return None
    values = secrets()
    for name, path in transcripts(transcript).items():
        target = out / f"{name}.gz"
        target.parent.mkdir(parents=True, exist_ok=True)
        text = path.read_text(encoding="utf-8", errors="replace")
        target.write_bytes(gzip.compress(redact(text, values).encode(), mtime=0))
    metadata = {
        "repo": repo.name,
        "branch": branch,
        "session_id": session,
        "tickets": sorted({s.ticket for s in segments if s.ticket is not None}),
        "segments": [segment_json(segment) for segment in segments],
        "event": event.get("hook_event_name"),
        "uploaded_at": datetime.now(UTC).isoformat(),
    }
    (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return f"{repo.name}/sessions/{session}"


def proxy_auth() -> bool:
    """Return whether the cloud sandbox's proxy adds the Google access token."""
    return os.environ.get(TOKEN_ENV, "") == PROXY_TOKEN


def gcloud(config: Path, *args: str, keep_token: bool) -> None:
    """Run gcloud with its own config folder, so the user's login stays as it is.

    With a service account key, the sandbox's `CLOUDSDK_AUTH_ACCESS_TOKEN` is
    dropped, because it would override the key.
    """
    env = {
        name: value
        for name, value in os.environ.items()
        if keep_token or name != TOKEN_ENV
    }
    env["CLOUDSDK_CONFIG"] = str(config)
    subprocess.run(  # noqa: S603
        ["gcloud", *args, "--quiet"],  # noqa: S607
        env=env,
        check=True,
        capture_output=True,
    )


def upload(event: dict[str, Any]) -> bool:
    """Stage the session and copy it to the bucket. Return whether it uploaded."""
    bucket = setting(BUCKET_ENV)
    with tempfile.TemporaryDirectory(prefix="craft-transcripts-") as tmp:
        work = Path(tmp)
        out = work / "out"
        out.mkdir()
        prefix = stage(event, out)
        if prefix is None:
            return False
        config = work / "gcloud"
        raw_key = setting(KEY_ENV)
        if raw_key:
            key = work / "key.json"
            key.write_text(key_json(raw_key), encoding="utf-8")
            key.chmod(0o600)
            gcloud(
                config,
                "auth",
                "activate-service-account",
                f"--key-file={key}",
                keep_token=False,
            )
        gcloud(
            config,
            "storage",
            "rsync",
            str(out),
            f"gs://{bucket}/{prefix}",
            "--recursive",
            keep_token=not raw_key,
        )
    return True


def log(message: str) -> None:
    """Append a line to the upload log."""
    with (
        contextlib.suppress(OSError),
        (state_dir() / "upload.log").open("a", encoding="utf-8") as file,
    ):
        file.write(f"{datetime.now(UTC).isoformat()} {message}\n")


def session_file(session: str, suffix: str) -> Path:
    """Return a state file of one session."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session)
    return state_dir() / f"{safe}.{suffix}"


def recently_uploaded(session: str) -> bool:
    """Return whether the session's last upload is newer than the Stop interval."""
    try:
        interval = float(setting(INTERVAL_ENV) or DEFAULT_STOP_INTERVAL)
        last = float(session_file(session, "last").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return time.time() - last < interval


def upload_locked(event: dict[str, Any]) -> None:
    """Upload under the session's lock, and log the result."""
    session = str(event.get("session_id") or "unknown-session")
    with session_file(session, "lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            uploaded = upload(event)
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(error, "stderr", b"") or b""
            log(f"failed {session}: {error} {detail.decode()[-500:]}")
            return
        if not uploaded:
            log(f"skipped {session}: no craft step")
            return
        session_file(session, "last").write_text(str(time.time()), encoding="utf-8")
        log(f"uploaded {session} ({event.get('hook_event_name')})")


def main() -> None:
    """Start a background upload, or run it when called with the upload flag."""
    if not setting(BUCKET_ENV):
        return
    if not (setting(KEY_ENV) or proxy_auth()):
        return
    if sys.argv[1:2] == [UPLOAD_FLAG]:
        upload_locked(json.loads(sys.argv[2]))
        return
    event = json.load(sys.stdin)
    session = str(event.get("session_id") or "unknown-session")
    if event.get("hook_event_name") == "Stop" and recently_uploaded(session):
        return
    subprocess.Popen(  # noqa: S603
        [sys.executable, __file__, UPLOAD_FLAG, json.dumps(event)],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


if __name__ == "__main__":
    main()
