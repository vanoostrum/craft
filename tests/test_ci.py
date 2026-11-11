# Copyright (C) 2026 Theo van Oostrum
"""The CI workflow runs the checks and the eval smoke suite as agreed."""

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
EVAL_COMMAND = (
    "claude plugin eval plugins/craft --trust-plugin --no-publish "
    "--ablation none --runs 1 --max-cost-usd 1"
)


def workflow() -> dict[Any, Any]:
    """Return the parsed CI workflow."""
    return yaml.safe_load(CI.read_text(encoding="utf-8"))


def job(name: str) -> dict[str, Any]:
    """Return one job of the CI workflow."""
    return workflow()["jobs"][name]


def step_named(job_steps: list[dict[str, Any]], name: str) -> dict[str, Any]:
    """Return the step called `name`."""
    return next(s for s in job_steps if s.get("name") == name)


def check_steps() -> list[str]:
    """Return the `run` commands of the `checks` job, in order."""
    return [s["run"] for s in job("checks")["steps"] if "run" in s]


def test_checks_uses_shellcheck_from_uv() -> None:
    """`checks` runs shellcheck from the `shellcheck-py` dev dependency."""
    assert "uv run shellcheck plugins/craft/skills/rules/scripts/gallery-shot" in (
        check_steps()
    )


def test_evals_runs_only_on_pull_requests() -> None:
    """A push to `main` was checked on its PR, so `evals` runs on PRs only."""
    assert job("evals")["if"] == "github.event_name == 'pull_request'"


def test_evals_checks_out_the_full_history() -> None:
    """The gate diffs against the PR base, so the checkout fetches every commit."""
    checkout = job("evals")["steps"][0]
    assert checkout["uses"].startswith("actions/checkout@")
    assert checkout["with"]["fetch-depth"] == 0


def test_evals_runs_the_suite_only_after_the_gate_says_so() -> None:
    """The gate runs first, with the secret and the base SHA; then the suite."""
    steps = job("evals")["steps"]
    gate = step_named(steps, "Gate")
    suite = step_named(steps, "Smoke suite")
    assert steps.index(gate) < steps.index(suite)
    assert "python3 .github/scripts/evals_gate.py" in gate["run"]
    assert "github.event.pull_request.base.sha" in gate["run"]
    assert gate["env"]["ANTHROPIC_API_KEY"] == "${{ secrets.ANTHROPIC_API_KEY }}"
    assert suite["if"] == f"steps.{gate['id']}.outputs.run == 'true'"


def test_evals_runs_the_agreed_command() -> None:
    """The suite runs word for word as agreed, without a tool grant."""
    suite = step_named(job("evals")["steps"], "Smoke suite")
    assert EVAL_COMMAND in suite["run"]
    assert "--allow-tools" not in suite["run"]
    assert suite["env"]["ANTHROPIC_API_KEY"] == "${{ secrets.ANTHROPIC_API_KEY }}"


def test_evals_keeps_the_traces() -> None:
    """The suite keeps each run's trace, so `Show scores` can print its Skill calls."""
    suite = step_named(job("evals")["steps"], "Smoke suite")
    assert "--keep-temp" in suite["run"]


def test_evals_uploads_no_transcripts() -> None:
    """The upload hook is off in CI, under its new and its old name."""
    suite = step_named(job("evals")["steps"], "Smoke suite")
    assert "env -u CRAFT_GCS_BUCKET -u SOUS_GCS_BUCKET" in suite["run"]


def test_evals_installs_a_pinned_cli() -> None:
    """A new Claude Code release cannot turn `evals` red on its own."""
    install = step_named(job("evals")["steps"], "Install Claude Code")
    assert "npm install -g @anthropic-ai/claude-code@2." in install["run"]


def test_evals_prints_the_scores_also_on_failure() -> None:
    """The job log names each case and each failed grader, so a red run is readable."""
    show = step_named(job("evals")["steps"], "Show scores")
    assert show["if"] == "always() && steps.suite.outcome != 'skipped'"
    assert (
        "python3 .github/scripts/eval_scores.py eval-results/result.json"
        in (show["run"])
    )


def test_evals_uploads_the_results_also_on_failure() -> None:
    """The JSON result and the report are uploaded, also when the suite fails."""
    steps = job("evals")["steps"]
    suite = step_named(steps, "Smoke suite")
    upload = step_named(steps, "Upload results")
    assert upload["uses"].startswith("actions/upload-artifact@")
    assert upload["if"] == "always()"
    assert upload["with"]["name"] == "eval-results"
    folder = upload["with"]["path"]
    assert f"--json {folder}/" in suite["run"]
    assert f"--report {folder}/" in suite["run"]
