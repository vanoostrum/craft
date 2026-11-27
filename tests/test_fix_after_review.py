# Copyright (C) 2026 Theo van Oostrum
"""A fix after a review FAIL, or after merge-gate feedback, runs in its own build.

The session loads `craft:build` again with the Skill tool before it fixes, and
`craft:review` again after, so the upload hook records the fix in a `build`
segment, and the audit's Build rubric sees all build work (CRAFT-94).
"""

from pathlib import Path
from typing import Any

import pytest

from tests.skill_text import section, skill
from tests.test_one_step_per_session import run_hook as run_step_hook
from tests.test_require_bstack import skill_call
from tests.test_upload_transcripts import timed, typed, uploaded_segments
from tests.transcripts import OPUS, SONNET, in_dir, reply, write_jsonl
from tests.transcripts import skill as skill_block

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "craft" / "skills"
TICKET = "LIBRAG-30"
RELOAD_BUILD = "load `craft:build` again with the Skill tool, with the ticket key"
RELOAD_REVIEW = "load `craft:review` again with the Skill tool, with the ticket key"
NEW_COMMIT_CHECKS = 2  # Step 1 of `craft:merge`: the gated and the one-shot check.
DESIGN_RULE = (
    "Feedback that changes the design goes back to `craft:design` in ticket mode, "
    "then through the spec gate again."
)


def rule(name: str) -> str:
    """Return the text of the `- **<name>.**` rule in `craft:rules`."""
    return skill("rules").split(f"- **{name}.**", 1)[1].split("\n- **", 1)[0]


def fix() -> str:
    """Return the **Fix** section of `craft:build`."""
    return section(skill("build"), "Fix")


# The step hook.

FIX_ROUNDS = {
    "build after a FAIL": (
        [skill_call("craft:build"), skill_call("craft:review")],
        "craft:build",
    ),
    "review after the fix": (
        [
            skill_call("craft:build"),
            skill_call("craft:review"),
            skill_call("craft:build"),
        ],
        "craft:review",
    ),
    "build after merge-gate feedback": (
        [
            skill_call("craft:build"),
            skill_call("craft:review"),
            skill_call("craft:build"),
            skill_call("craft:review"),
        ],
        "craft:build",
    ),
}


@pytest.mark.parametrize("round_name", sorted(FIX_ROUNDS))
def test_a_build_session_loads_build_and_review_again(
    tmp_path: Path, round_name: str
) -> None:
    """The `one_step_per_session` hook allows a fix round in a build session."""
    entries, step = FIX_ROUNDS[round_name]
    assert run_step_hook(tmp_path, step, entries) == ""


# The upload hook.

WORK = {"build": 40.0, "review": 10.0, "merge": 5.0}


def fix_session(tmp_path: Path, project: Path, steps: list[str]) -> Path:
    """Write a build session with one Skill call per step, each with the ticket.

    Each step starts 100 seconds after the one before. A wake comes 1 second
    before its Skill call, and the step works `WORK[step]` seconds after it.
    """
    lines: list[dict[str, Any]] = []
    for number, step in enumerate(steps):
        base = 100.0 * (number + 1)
        model = SONNET if step == "build" else OPUS
        call = skill_block(f"craft:{step}", TICKET)
        call["id"] = f"call-{number}"
        lines += [
            typed(base - 1, f"Wake {number}."),
            timed(base, reply(0, f"c{number}", model, 9, call)),
            timed(base + WORK[step], reply(0, f"w{number}", model, 9)),
        ]
    lines[0] = in_dir(project, lines[0])
    session = tmp_path / "fix.jsonl"
    write_jsonl(session, lines)
    return session


@pytest.mark.parametrize(
    "steps",
    [
        ["build", "review", "build", "review", "merge"],
        ["build", "review", "build", "review", "build", "review", "merge"],
    ],
    ids=["one FAIL", "two FAILs"],
)
def test_each_fix_round_gets_its_own_build_segment(
    tmp_path: Path, project: Path, steps: list[str]
) -> None:
    """Each Skill call starts a segment, and the fix work counts in its build."""
    segments = uploaded_segments(
        tmp_path, fix_session(tmp_path, project, steps), project
    )

    assert [(s["step"], s["ticket"]) for s in segments] == [
        (step, TICKET) for step in steps
    ]
    for segment, step in zip(segments, steps, strict=True):
        # 1 second from the wake into the Skill call, then the step's own work.
        assert float(segment["work_seconds"]) == 1 + WORK[step]


# The skill text.


def test_review_fail_loads_build_again_before_any_fix() -> None:
    """`craft:review` step 4 loads `craft:build` again before it changes a file."""
    step = section(skill("review"), "Steps").split("4. **If FAIL:**", 1)[1]
    step = step.split("\n5. ", 1)[0]
    assert RELOAD_BUILD in step
    assert "before you change any file" in step
    assert "**Fix** in `craft:build`" in step
    assert "failed attempt" in step


def test_fix_loads_review_again_for_a_follow_up_review() -> None:
    """**Fix** loads `craft:review` again, and its next review is a follow-up."""
    text = fix()
    assert RELOAD_REVIEW in text
    assert "follow-up review" in text
    assert "continue with `craft:review`" not in text


def test_next_loads_review_with_the_skill_tool() -> None:
    """**Next** in `craft:build` loads `craft:review` with the ticket key."""
    text = section(skill("build"), "Next")
    assert "Load `craft:review` with the Skill tool, with the ticket key" in text


def test_fix_covers_merge_gate_feedback_with_a_new_build_call() -> None:
    """**Fix** runs in a new `craft:build` call, for a FAIL and for gate feedback."""
    text = fix()
    assert "owner feedback at the merge gate, a polish fix included" in text
    assert RELOAD_BUILD in text
    assert "`build` segment" in text
    assert "**UI feedback at the merge gate**" in text


def test_fix_run_keeps_the_ticket_state() -> None:
    """A fix run skips steps 1 to 3, so it never moves a ticket to Building."""
    text = fix()
    assert "skips steps 1 to 3" in text
    assert "no claim, no ready checks, and no move to **Building**" in text
    assert "never puts a second ticket in **Building**" in text


def test_gate_rule_sends_merge_gate_feedback_to_a_new_build_call() -> None:
    """**The gate**: merge-gate feedback reloads `craft:build`; other gates stay."""
    text = rule("The gate")
    feedback = text.split("Any other reply from the owner is feedback", 1)[1]
    assert "At the plan gate and the spec gate, go back to the step before" in (
        feedback
    )
    assert f"At the merge gate, {RELOAD_BUILD}" in feedback
    assert "except as **UI feedback at the merge gate** says" in feedback


def test_ui_feedback_polish_fix_reloads_build_and_design_rule_stays() -> None:
    """A polish fix reloads `craft:build`; a design change still goes to design."""
    text = rule("UI feedback at the merge gate")
    polish = "A polish fix goes back to `craft:build`, loaded again with the Skill tool"
    assert polish in text
    assert DESIGN_RULE in text


# The ripple check.


def test_merge_sends_new_commits_to_a_new_review_call() -> None:
    """`craft:merge` step 1 loads `craft:review` again for commits after the gate."""
    step = section(skill("merge"), "Steps").split("\n2. ", 1)[0]
    assert "go back to `craft:review`." not in step
    assert step.count(RELOAD_REVIEW) == NEW_COMMIT_CHECKS


@pytest.mark.parametrize(
    "path", sorted(SKILLS.rglob("*.md")), ids=lambda p: str(p.relative_to(SKILLS))
)
def test_no_skill_keeps_the_fix_in_the_review_step(path: Path) -> None:
    """No skill file sends a fix or a review on without a new Skill call."""
    text = path.read_text(encoding="utf-8")
    for phrase in (
        "go back to `craft:build` with the review",
        "continue with `craft:review`: its next review",
        "go back to `craft:review`.",
    ):
        assert phrase not in text


def test_build_rubric_keeps_version_one() -> None:
    """The Build rubric's items do not change; only its data gets complete."""
    rubric = SKILLS / "audit" / "rubrics" / "build.md"
    assert "Rubric version: 1" in rubric.read_text(encoding="utf-8")
