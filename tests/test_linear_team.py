# Copyright (C) 2026 Theo van Oostrum
"""`linear_team.py` creates or completes the Linear team and project for craft.

A fake Linear GraphQL server stands in for Linear. It keeps teams, workflow
states, and labels in memory, so the tests can read what the script made.
"""

import json
import os
import subprocess
import sys
import threading
from collections.abc import Iterator
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, override

import pytest

from tests.test_brainstorm import SKILLS, skill, step

SCRIPT = SKILLS / "setup" / "scripts" / "linear_team.py"
ROOT = Path(__file__).resolve().parents[1]
CRAFT_STATES = {
    "Backlog": "backlog",
    "Todo": "unstarted",
    "Specifying": "started",
    "Ready to build": "started",
    "Building": "started",
    "In Review": "started",
    "Needs human": "started",
    "Done": "completed",
    "Canceled": "canceled",
    "Duplicate": "duplicate",
}
STARTED_ORDER = ["Specifying", "Ready to build", "Building", "In Review", "Needs human"]
LINEAR_DEFAULT_STATES = [
    ("Backlog", "backlog"),
    ("Todo", "unstarted"),
    ("In Progress", "started"),
    ("In Review", "started"),
    ("Done", "completed"),
    ("Canceled", "canceled"),
    ("Duplicate", "duplicate"),
]


class FakeLinear:
    """Teams, states, and labels, changed by GraphQL operations by name."""

    def __init__(self, team_limit: int = 5) -> None:
        """Start with no teams."""
        self.team_limit = team_limit
        self.teams: dict[str, dict[str, Any]] = {}
        self.mutations: list[str] = []
        self.auth: list[str] = []
        self.http_status = 200
        self.next_id = 0

    def new_id(self) -> str:
        """Return a fresh id."""
        self.next_id += 1
        return f"id-{self.next_id}"

    def add_team(self, key: str, states: list[tuple[str, str]]) -> dict[str, Any]:
        """Add a team with these states and no labels."""
        team = {
            "id": self.new_id(),
            "key": key,
            "states": [],
            "labels": [],
            "projects": [],
        }
        for position, (name, kind) in enumerate(states):
            team["states"].append(
                {"id": self.new_id(), "name": name, "type": kind, "position": position}
            )
        self.teams[team["id"]] = team
        return team

    def state(self, state_id: str) -> dict[str, Any]:
        """Return the state with this id."""
        return next(
            s for t in self.teams.values() for s in t["states"] if s["id"] == state_id
        )

    def handle(self, operation: str, variables: dict[str, Any]) -> dict[str, Any]:
        """Run one named operation and return its GraphQL response."""
        if operation.startswith(("Create", "Update")):
            self.mutations.append(operation)
        handler = getattr(self, f"op_{operation}", None)
        if handler is None:
            return {"errors": [{"message": f"unknown operation {operation}"}]}
        return handler(variables)

    def op_Teams(self, _: dict[str, Any]) -> dict[str, Any]:  # noqa: N802
        """List the teams."""
        nodes = [{"id": t["id"], "key": t["key"]} for t in self.teams.values()]
        return {"data": {"teams": {"nodes": nodes}}}

    def op_CreateTeam(self, variables: dict[str, Any]) -> dict[str, Any]:  # noqa: N802
        """Create a team with Linear's default states, within the plan limit."""
        if len(self.teams) >= self.team_limit:
            message = "You have reached the limit of teams allowed in your plan."
            error = {"extensions": {"userPresentableMessage": message}}
            return {"errors": [{"message": "Access denied", **error}]}
        team = self.add_team(variables["input"]["key"], LINEAR_DEFAULT_STATES)
        return {"data": {"teamCreate": {"team": {"id": team["id"]}}}}

    def op_TeamSetup(self, variables: dict[str, Any]) -> dict[str, Any]:  # noqa: N802
        """Return a team's states and labels."""
        team = self.teams[variables["id"]]
        labels = [{"name": n} for n in team["labels"]]
        projects = [{"name": n} for n in team["projects"]]
        data = {
            "states": {"nodes": team["states"]},
            "labels": {"nodes": labels},
            "projects": {"nodes": projects},
        }
        return {"data": {"team": data}}

    def op_UpdateState(self, variables: dict[str, Any]) -> dict[str, Any]:  # noqa: N802
        """Change a state."""
        self.state(variables["id"]).update(variables["input"])
        return {"data": {"workflowStateUpdate": {"success": True}}}

    def op_CreateState(self, variables: dict[str, Any]) -> dict[str, Any]:  # noqa: N802
        """Add a state to a team."""
        given = variables["input"]
        self.teams[given["teamId"]]["states"].append(
            {
                "id": self.new_id(),
                "name": given["name"],
                "type": given["type"],
                "position": given["position"],
            }
        )
        return {"data": {"workflowStateCreate": {"success": True}}}

    def op_CreateProject(self, variables: dict[str, Any]) -> dict[str, Any]:  # noqa: N802
        """Add a project to the given teams."""
        given = variables["input"]
        for team_id in given["teamIds"]:
            self.teams[team_id]["projects"].append(given["name"])
        return {"data": {"projectCreate": {"success": True}}}

    def op_CreateLabel(self, variables: dict[str, Any]) -> dict[str, Any]:  # noqa: N802
        """Add a label to a team."""
        given = variables["input"]
        self.teams[given["teamId"]]["labels"].append(given["name"])
        return {"data": {"issueLabelCreate": {"success": True}}}


@pytest.fixture
def linear() -> Iterator[tuple[FakeLinear, str]]:
    """Serve a fake Linear on a local port, and return it with its URL."""
    fake = FakeLinear()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            fake.auth.append(self.headers.get("Authorization", ""))
            name = body["query"].split("(", 1)[0].split("{", 1)[0].split()[-1]
            if fake.http_status == HTTPStatus.OK:
                reply = fake.handle(name, body.get("variables") or {})
            else:
                reply = {"errors": [{"message": "Query too complex"}]}
            out = json.dumps(reply).encode()
            self.send_response(fake.http_status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)

        @override
        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield fake, f"http://127.0.0.1:{server.server_port}/graphql"
    server.shutdown()


def run(
    url: str, *args: str, key: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the script against the fake Linear."""
    env = {k: v for k, v in os.environ.items() if k != "LINEAR_API_KEY"}
    env["LINEAR_API_URL"] = url
    if key is not None:
        env["LINEAR_API_KEY"] = key
    return subprocess.run(  # noqa: S603 - runs our own script.
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def craft_team(fake: FakeLinear, key: str) -> dict[str, Any]:
    """Return the team with this key."""
    return next(t for t in fake.teams.values() if t["key"] == key)


def started_order(team: dict[str, Any]) -> list[str]:
    """Return the names of the team's started states, in board order."""
    started = [s for s in team["states"] if s["type"] == "started"]
    return [s["name"] for s in sorted(started, key=lambda s: s["position"])]


def test_creates_a_team_with_the_craft_states_and_the_ui_label(
    linear: tuple[FakeLinear, str],
) -> None:
    """A new key gets a team with exactly the craft states, in order, and `ui`."""
    fake, url = linear
    result = run(url, "ABC", "Abc team", "Abc app")
    assert result.returncode == 0, result.stderr
    team = craft_team(fake, "ABC")
    assert {s["name"]: s["type"] for s in team["states"]} == CRAFT_STATES
    assert started_order(team) == STARTED_ORDER
    assert team["labels"] == ["ui"]
    assert team["projects"] == ["Abc app"]
    assert "ABC" in result.stdout


def test_completes_an_existing_team_and_keeps_its_states(
    linear: tuple[FakeLinear, str],
) -> None:
    """An existing team keeps what it has and gets what craft still misses."""
    fake, url = linear
    fake.add_team("ABC", [*LINEAR_DEFAULT_STATES, ("QA", "started")])
    result = run(url, "ABC", "Abc team", "Abc app")
    assert result.returncode == 0, result.stderr
    team = craft_team(fake, "ABC")
    names = {s["name"] for s in team["states"]}
    assert set(CRAFT_STATES) <= names
    assert "QA" in names
    assert "In Progress" not in names
    assert [s["name"] for s in team["states"]].count("Specifying") == 1
    assert started_order(team)[:2] == ["Specifying", "Ready to build"]
    assert "CreateTeam" not in fake.mutations


def test_keeps_the_team_s_own_backlog_state(linear: tuple[FakeLinear, str]) -> None:
    """A team with a backlog state under its own name gets no second one."""
    fake, url = linear
    fake.add_team("ABC", [("Triage", "backlog"), *LINEAR_DEFAULT_STATES[1:]])
    result = run(url, "ABC", "Abc team", "Abc app")
    assert result.returncode == 0, result.stderr
    names = [s["name"] for s in craft_team(fake, "ABC")["states"]]
    assert "Triage" in names
    assert "Backlog" not in names


def test_an_http_error_shows_linear_s_message(
    linear: tuple[FakeLinear, str],
) -> None:
    """Linear answers some errors with HTTP 400; the owner reads the message."""
    fake, url = linear
    fake.http_status = HTTPStatus.BAD_REQUEST
    result = run(url, "ABC", "Abc team", "Abc app")
    assert result.returncode != 0
    assert "Query too complex" in result.stderr
    assert "Traceback" not in result.stderr


def test_a_refused_key_says_where_to_set_it(linear: tuple[FakeLinear, str]) -> None:
    """Without a valid key, the message says how to give the script one."""
    fake, url = linear
    fake.http_status = HTTPStatus.UNAUTHORIZED
    result = run(url, "ABC", "Abc team", "Abc app")
    assert result.returncode != 0
    assert "LINEAR_API_KEY" in result.stderr
    assert "api.linear.app" in result.stderr


def test_adds_a_second_project_to_a_shared_team(
    linear: tuple[FakeLinear, str],
) -> None:
    """One team holds many projects: a new project joins the existing team."""
    fake, url = linear
    run(url, "ABC", "Abc team", "Abc app")
    fake.mutations.clear()
    result = run(url, "ABC", "Abc team", "Other app")
    assert result.returncode == 0, result.stderr
    assert craft_team(fake, "ABC")["projects"] == ["Abc app", "Other app"]
    assert fake.mutations == ["CreateProject"]


def test_a_second_run_changes_nothing(linear: tuple[FakeLinear, str]) -> None:
    """The script is safe to run again: a complete team gets no writes."""
    fake, url = linear
    run(url, "ABC", "Abc team", "Abc app")
    fake.mutations.clear()
    result = run(url, "ABC", "Abc team", "Abc app")
    assert result.returncode == 0, result.stderr
    assert fake.mutations == []


def test_a_plan_limit_fails_with_linear_s_message(
    linear: tuple[FakeLinear, str],
) -> None:
    """When Linear refuses a new team, the owner reads why."""
    fake, url = linear
    fake.team_limit = 0
    result = run(url, "ABC", "Abc team", "Abc app")
    assert result.returncode != 0
    assert "limit of teams" in result.stderr


def test_sends_linear_api_key_when_set(linear: tuple[FakeLinear, str]) -> None:
    """In a terminal, `LINEAR_API_KEY` authenticates; in the cloud, the proxy does."""
    fake, url = linear
    run(url, "ABC", "Abc team", "Abc app", key="lin_api_test")
    assert set(fake.auth) == {"lin_api_test"}


def test_setup_creates_the_team_before_asking_the_owner() -> None:
    """Setup runs the script, and only an unmade team stays on the owner's list."""
    where = step(skill("setup"), "Where craft works.")
    assert "scripts/linear_team.py" in where
    assert "the Linear team" not in step(skill("setup"), "Owner checklist.")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "api.linear.app" in readme


def test_one_linear_project_per_project() -> None:
    """Briefs, plans, and tickets live in the Linear project from the config."""
    rules = skill("rules")
    assert "| Linear project |" in rules
    assert "Linear project from the config" in step(
        skill("brainstorm"), "Write the brief."
    )
    assert "as a Linear document in the Linear project" in step(
        skill("plan"), "Write the plan"
    )
    assert "sub-issue of the plan ticket" in skill("plan")
    assert "Create a Linear project for" not in skill("brainstorm")
    assert "Create a Linear project named" not in skill("setup")


def test_no_step_reads_a_plan_from_the_plan_ticket() -> None:
    """The plan is a `Plan: <name>` document, not a `## Plan` ticket section."""
    for path in SKILLS.rglob("*.md"):
        assert "## Plan`" not in path.read_text(encoding="utf-8"), path


def test_several_plans_share_one_linear_project() -> None:
    """Several plans share one Linear project, and old projects get the key."""
    nxt = skill("next")
    assert "ticket's plan document" in nxt
    assert "For each open plan ticket" in nxt
    assert "`<plan name>: <milestone>`" in skill("plan")
    assert "no `Linear project` key" in skill("rules")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "Upgrade to 2.3" in readme
