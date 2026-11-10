#!/usr/bin/env python3
# Copyright (C) 2026 Theo van Oostrum
"""Create or complete the Linear team and the Linear project of a craft project.

Usage: linear_team.py <TEAM KEY> <team name> <project name>

The team gets the craft states and the `ui` label, and the project is created
in the team if it is missing. One team holds many projects. A team that exists keeps
its own states and labels, and gets only what craft still misses. A second
run changes nothing.

In a cloud session, the proxy adds the Linear API key: the cloud environment
has a network secret for `api.linear.app`. In a terminal, set `LINEAR_API_KEY`.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

URL = os.environ.get("LINEAR_API_URL", "https://api.linear.app/graphql")
# The cloud proxy replaces this value with the real key.
PLACEHOLDER_KEY = "set-by-the-cloud-proxy"

# Each craft state, its Linear type, and its color.
STATES = [
    ("Backlog", "backlog", "#bec2c8"),
    ("Todo", "unstarted", "#e2e2e2"),
    ("Specifying", "started", "#f2c94c"),
    ("Ready to build", "started", "#4cb782"),
    ("Building", "started", "#4cb782"),
    ("In Review", "started", "#bb87fc"),
    ("Needs human", "started", "#eb5757"),
    ("Done", "completed", "#5e6ad2"),
    ("Canceled", "canceled", "#95a2b3"),
    ("Duplicate", "duplicate", "#95a2b3"),
]
# A new Linear team has "In Progress"; craft calls that state "Specifying".
RENAMED = {"In Progress": "Specifying"}
# Craft does not use these types itself: a team that has a state of the type,
# under any name, keeps it and gets no second one.
OWN_NAME_TYPES = {"backlog", "canceled", "duplicate"}
KEY_HINT = (
    "Linear needs an API key. In a cloud session, add a network secret for "
    "api.linear.app (header Authorization, the key without Bearer). "
    "In a terminal, set LINEAR_API_KEY."
)
UI_LABEL = {
    "name": "ui",
    "color": "#2f5d50",
    "description": "Adds or changes a screen.",
}


class LinearError(Exception):
    """Linear refused a request."""


def say(line: str) -> None:
    """Tell the caller what changed."""
    sys.stdout.write(line + "\n")


def gql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """Send one GraphQL operation to Linear and return its data."""
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    key = os.environ.get("LINEAR_API_KEY", PLACEHOLDER_KEY)
    headers = {"Content-Type": "application/json", "Authorization": key}
    request = urllib.request.Request(URL, body, headers)  # noqa: S310 - fixed host.
    out: dict[str, Any]
    try:
        with urllib.request.urlopen(request) as response:  # noqa: S310 - fixed host.
            out = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            out = json.load(error)
        except ValueError:
            out = {"errors": [{"message": f"HTTP {error.code} {error.reason}"}]}
        if error.code == 401:  # noqa: PLR2004 - HTTP Unauthorized.
            out.setdefault("errors", []).append({"message": KEY_HINT})
    except urllib.error.URLError as error:
        out = {"errors": [{"message": f"cannot reach Linear: {error.reason}"}]}
    errors: list[dict[str, Any]] = out.get("errors") or []
    if errors:
        messages = [
            e.get("extensions", {}).get("userPresentableMessage") or e["message"]
            for e in errors
        ]
        if any("authenticat" in m.lower() for m in messages):
            messages.append(KEY_HINT)
        raise LinearError("; ".join(dict.fromkeys(messages)))
    return out["data"]


def find_or_create_team(key: str, name: str) -> str:
    """Return the id of the team with this key, created if it is missing."""
    teams = gql("query Teams { teams(first: 250) { nodes { id key } } }")["teams"][
        "nodes"
    ]
    for team in teams:
        if team["key"] == key:
            return str(team["id"])
    created = gql(
        "mutation CreateTeam($input: TeamCreateInput!) "
        "{ teamCreate(input: $input) { team { id } } }",
        {"input": {"key": key, "name": name}},
    )
    say(f"Created team {key}.")
    return str(created["teamCreate"]["team"]["id"])


def update_state(state_id: str, changes: dict[str, Any]) -> None:
    """Change a workflow state."""
    gql(
        "mutation UpdateState($id: String!, $input: WorkflowStateUpdateInput!) "
        "{ workflowStateUpdate(id: $id, input: $input) { success } }",
        {"id": state_id, "input": changes},
    )


def complete_states(team_id: str, states: list[dict[str, Any]]) -> None:
    """Add the craft states the team misses, and put them in craft's order."""
    by_name = {s["name"]: s for s in states}
    for old, new in RENAMED.items():
        if new not in by_name and old in by_name:
            update_state(by_name[old]["id"], {"name": new})
            by_name[new] = by_name.pop(old)
            say(f"Renamed state {old} to {new}.")
    types = {s["type"] for s in states}
    for position, (name, kind, color) in enumerate(STATES):
        state = by_name.get(name)
        if state is None and kind in OWN_NAME_TYPES and kind in types:
            continue
        if state is None:
            gql(
                "mutation CreateState($input: WorkflowStateCreateInput!) "
                "{ workflowStateCreate(input: $input) { success } }",
                {
                    "input": {
                        "teamId": team_id,
                        "name": name,
                        "type": kind,
                        "color": color,
                        "position": position,
                    }
                },
            )
            say(f"Created state {name}.")
        elif kind == "started" and state["position"] != position:
            # Only the started states need craft's order. Linear refuses
            # changes to its reserved states, such as Duplicate.
            update_state(state["id"], {"position": position})


def main(key: str, name: str, project: str) -> None:
    """Create or complete the team, its states, its `ui` label, and the project."""
    team_id = find_or_create_team(key, name)
    team = gql(
        "query TeamSetup($id: String!) { team(id: $id) { "
        "states(first: 250) { nodes { id name type position } } "
        "labels(first: 250) { nodes { name } } "
        "projects(first: 250) { nodes { name } } } }",
        {"id": team_id},
    )["team"]
    complete_states(team_id, team["states"]["nodes"])
    if not any(label["name"] == "ui" for label in team["labels"]["nodes"]):
        gql(
            "mutation CreateLabel($input: IssueLabelCreateInput!) "
            "{ issueLabelCreate(input: $input) { success } }",
            {"input": {"teamId": team_id, **UI_LABEL}},
        )
        say("Created label ui.")
    if not any(p["name"] == project for p in team["projects"]["nodes"]):
        gql(
            "mutation CreateProject($input: ProjectCreateInput!) "
            "{ projectCreate(input: $input) { success } }",
            {"input": {"name": project, "teamIds": [team_id]}},
        )
        say(f"Created project {project}.")
    say(f"Team {key} and project {project} are ready for craft.")


if __name__ == "__main__":
    if len(sys.argv) != 4:  # noqa: PLR2004 - the key, the team, the project.
        sys.exit(__doc__)
    try:
        main(sys.argv[1], sys.argv[2], sys.argv[3])
    except LinearError as error:
        sys.exit(f"Linear refused: {error}")
