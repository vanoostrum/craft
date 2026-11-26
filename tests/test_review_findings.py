# Copyright (C) 2026 Theo van Oostrum
"""Reviews find every blocking problem in one pass, and fixes check their ripple."""

import re
from collections.abc import Callable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "craft" / "skills"
FINDINGS = SKILLS / "rules" / "findings.md"
BUILD_REVIEW_BLOCKING_CHECKS = 5


def skill(name: str) -> str:
    """Return the text of a skill's `SKILL.md`."""
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def findings() -> str:
    """Return the text of `rules/findings.md`."""
    return FINDINGS.read_text(encoding="utf-8")


def spec_review() -> str:
    """Return the text of `rules/spec-review.md`."""
    return (SKILLS / "rules" / "spec-review.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return the body of the `## <heading>` section of `text`."""
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def step(text: str, name: str) -> str:
    """Return the numbered step or item whose bold name is `name`."""
    rest = text.split(f"**{name}**", 1)[1].split("\n## ", 1)[0]
    end = re.search(r"\n\s*\d+\. \*\*", rest)
    return rest[: end.start()] if end else rest


def one_shot_spec() -> str:
    """Return the One-shot section of `craft:spec`."""
    return section(skill("spec"), "One-shot")


# Criterion 1: the complete pass.


def test_findings_asks_for_one_complete_pass() -> None:
    """A reviewer checks every criterion, focus line, path, and changed part."""
    text = section(findings(), "Full review")
    assert "one complete pass" in text
    for item in ("acceptance criterion", "Review focus", "**Paths**", "changed file"):
        assert item in text
    assert "all findings at once" in text
    assert "List what you checked" in text


# Criterion 2: blocking and non-blocking findings, and the verdict.


def test_findings_defines_blocking_findings() -> None:
    """The blocking list holds every kind from Decision 1."""
    text = section(findings(), "Blocking and non-blocking findings")
    blocking = text.split("**Blocking**", 1)[1].split("**Non-blocking**", 1)[0]
    for kind in (
        "not met or cannot be tested",
        "Review focus",
        "normal path",
        "contradiction",
        "later ticket consumes",
        "security issue",
        "outside the scope",
        "app evidence",
        "without screenshots",
        "difference from the gallery",
        "`design/`",
    ):
        assert kind in blocking


def test_findings_defines_non_blocking_findings() -> None:
    """The non-blocking list holds the kinds from Decision 1, and doubt blocks."""
    text = section(findings(), "Blocking and non-blocking findings")
    non_blocking = text.split("**Non-blocking**", 1)[1]
    for kind in ("rare edge case", "wording", "clearer structure", "stronger"):
        assert kind in non_blocking
    assert "When in doubt, a finding is blocking" in text


def test_findings_fails_only_on_a_blocking_finding() -> None:
    """FAIL needs a blocking finding, and the verdict line names the counts."""
    text = section(findings(), "Verdict")
    assert "FAIL only when it has at least one blocking finding" in text
    assert "PASS — 0 blocking, 2 non-blocking" in text


def test_a_review_with_no_findings_passes() -> None:
    """Review focus 5: no findings is PASS, and the gate may say none."""
    assert "with no findings at all" in section(findings(), "Verdict")
    assert "**Non-blocking findings:** none" in section(findings(), "At the gate")


# Criterion 3: the follow-up review.


def test_findings_defines_the_follow_up_review() -> None:
    """A later review checks the earlier findings, the changes, and the ripple."""
    text = section(findings(), "Follow-up review")
    assert "each blocking finding of the previous review" in text
    assert "each item of owner feedback" in text
    assert "the changed text" in text
    assert "every place that states a changed rule" in text
    assert "does not review unchanged parts again" in text
    assert "still counts" in text


def test_follow_up_searches_the_changed_rule_itself() -> None:
    """Review focus 1: the reviewer does not trust the fix summary's list."""
    text = section(findings(), "Follow-up review")
    assert "Search for them yourself" in text


def test_follow_up_never_loses_a_disputed_finding() -> None:
    """Review focus 2: a disputed finding is dropped with a reason, or stays."""
    text = section(findings(), "Follow-up review")
    assert "disputes" in text
    assert "drop it" in text
    assert "stays blocking" in text
    assert "never silently lost" in text


def test_follow_up_after_a_re_spec() -> None:
    """Decision 16: after a re-spec, both reviews are follow-up reviews."""
    text = section(findings(), "Follow-up review")
    assert "re-spec" in text
    assert "plan-scope findings on that ticket" in text
    assert "next plan-scope review" in text


# Criterion 4: the ripple check and the fix summary.


def test_findings_defines_the_ripple_check() -> None:
    """A fix searches every place that states the changed rule, and fixes them."""
    text = section(findings(), "Ripple check")
    assert "every place that states it" in text
    for place in ("the spec", "the other specs", "the skills", "the tests", "docs"):
        assert place in text
    assert "in the same fix" in text


def test_ripple_check_posts_a_fix_summary() -> None:
    """The fix summary covers each blocking finding and each item of feedback."""
    text = section(findings(), "Ripple check")
    assert "fix summary" in text
    assert "each blocking finding and each item of owner feedback" in text
    assert "disputed, with a reason" in text
    assert "`🤖 fix: <one line>`" in text
    assert "PR comment" in text


def test_fix_never_fixes_a_non_blocking_finding_on_its_own() -> None:
    """Review focus 4: only owner feedback turns a non-blocking finding into a fix."""
    text = section(findings(), "Ripple check")
    assert "Never fix a non-blocking finding" in text
    assert "turns it into feedback" in text


# Criterion 5: the review tasks and their calling steps.


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("review", lambda: step(skill("review"), "Review in a fresh agent.")),
        ("plan", lambda: step(skill("plan"), "Review in a fresh agent.")),
        ("spec-review.md", spec_review),
    ],
)
def test_review_tasks_follow_findings(name: str, text: Callable[[], str]) -> None:
    """Each review task tells the reviewer to follow `findings.md`."""
    assert "`findings.md`" in text(), name


@pytest.mark.parametrize(
    "path", sorted(SKILLS.rglob("*.md")), ids=lambda p: str(p.relative_to(SKILLS))
)
def test_no_skill_lists_real_problems_only(path: Path) -> None:
    """No skill file keeps the old review instruction, in any case."""
    text = path.read_text(encoding="utf-8").lower()
    assert "list real problems only" not in text
    assert "is a real problem" not in text


def test_build_review_marks_its_checks() -> None:
    """Decision 14: the build review's checks are blocking, seam repeats are not."""
    text = step(skill("review"), "Review in a fresh agent.")
    assert text.count("is a blocking finding") >= BUILD_REVIEW_BLOCKING_CHECKS
    assert "only repeats a test at the seam is a non-blocking finding" in text


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("review", lambda: step(skill("review"), "Review in a fresh agent.")),
        ("plan", lambda: step(skill("plan"), "Review in a fresh agent.")),
        ("spec", lambda: step(skill("spec"), "Spec review.")),
        ("one-shot review", lambda: step(one_shot_spec(), "Review.")),
        ("next", lambda: step(skill("next"), "Plan-scope review.")),
        ("spec-review.md", spec_review),
    ],
)
def test_calling_steps_pass_the_follow_up_inputs(
    name: str, text: Callable[[], str]
) -> None:
    """Decision 15: a follow-up reviewer gets the previous review and fix summaries."""
    assert "the previous review" in text(), name
    assert "fix summaries" in text(), name


def test_plan_scope_follow_up_gets_each_tickets_fix_summary() -> None:
    """A plan-scope follow-up gets the fix summary of each ticket that went back."""
    assert "fix summary of each ticket that went back" in spec_review()


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("spec", lambda: step(skill("spec"), "Spec review.")),
        ("one-shot review", lambda: step(one_shot_spec(), "Review.")),
        ("next", lambda: step(skill("next"), "Plan-scope review.")),
    ],
)
def test_verdict_templates_carry_the_counts(name: str, text: Callable[[], str]) -> None:
    """Decision 11: each `🤖 spec review:` template names the counts."""
    assert "<n> blocking, <m> non-blocking" in text(), name


# Criteria 6 and 8: the fix steps, and the plan-scope FAIL.


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("build", lambda: skill("build")),
        ("spec step 1", lambda: step(skill("spec"), "Get the ticket.")),
        ("spec step 6", lambda: step(skill("spec"), "Spec review.")),
        ("one-shot review", lambda: step(one_shot_spec(), "Review.")),
        ("one-shot write", lambda: step(one_shot_spec(), "Write.")),
        ("plan review", lambda: step(skill("plan"), "Review in a fresh agent.")),
        ("rules gate", lambda: skill("rules").split("- **The gate.**", 1)[1]),
    ],
)
def test_fix_steps_run_the_ripple_check(name: str, text: Callable[[], str]) -> None:
    """Every fix step follows the ripple check in `findings.md`."""
    assert "**Ripple check** in `findings.md`" in text(), name


def test_build_fixes_review_fails_and_merge_gate_feedback() -> None:
    """`craft:build` runs the ripple check after a review FAIL and gate feedback."""
    text = skill("build")
    fix = text.split("**Fix.**", 1)[1].split("\n## ", 1)[0]
    assert "review FAIL" in fix
    assert "merge gate" in fix
    assert "PR comment" in fix


def test_plan_fixes_review_fails_and_plan_gate_feedback() -> None:
    """`craft:plan` runs the ripple check after a review FAIL and gate feedback."""
    text = step(skill("plan"), "Review in a fresh agent.")
    assert "owner feedback at the plan gate" in text
    assert "PR comment" in text


def test_spec_feedback_includes_a_plan_scope_review() -> None:
    """A `🤖 spec review:` from the plan-scope review is a fix with a fix summary."""
    text = step(skill("spec"), "Get the ticket.")
    assert "plan-scope" in text
    assert "`🤖 fix: <one line>`" in text


def test_plan_scope_fail_acts_on_blocking_findings_only() -> None:
    """Review focus 3: only blocking findings send a ticket back to Todo."""
    text = step(skill("next"), "Plan-scope review.")
    assert "blocking finding" in text
    assert "A ticket with only non-blocking findings stays" in text


def test_rules_one_shot_sends_back_only_blocking_findings() -> None:
    """Item 4 of One-shot mode in `craft:rules` names blocking findings."""
    text = step(skill("rules"), "Plan-scope review.")
    assert "A blocking finding in a ticket" in text


# Criterion 7: the gates and the done report.


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("spec", lambda: step(skill("spec"), "Gate.")),
        ("review", lambda: step(skill("review"), "If PASS:")),
        ("plan", lambda: step(skill("plan"), "Gate.")),
    ],
)
def test_gates_list_non_blocking_findings(name: str, text: Callable[[], str]) -> None:
    """Each gate lists the non-blocking findings, and the owner can pick any."""
    gate = text()
    assert "**Non-blocking findings**" in gate, name
    assert "turn any of them into feedback" in gate, name


def test_plan_gate_keeps_the_merge_approval_sentence() -> None:
    """The findings go next to the merge approval sentence, not in its place."""
    gate = step(skill("plan"), "Gate.")
    assert "**Non-blocking findings**" in gate
    assert "Standing approval: craft may squash-merge" in gate


def test_done_report_counts_non_blocking_findings() -> None:
    """The one-shot done report counts the non-blocking findings per ticket."""
    report = step(skill("next"), "Done report.")
    assert "non-blocking findings" in report
    assert "per ticket" in report


# Criterion 9: the Paths table and the split proposal.


def test_spec_writes_a_paths_table() -> None:
    """A spec with states gets a Paths table, and the spec review checks it."""
    write = step(skill("spec"), "Write the spec")
    assert "**Paths:**" in write
    for column in ("start state", "event", "result", "criterion"):
        assert column in write
    assert "**Paths** row" in spec_review()


def test_split_proposal_above_ten_criteria() -> None:
    """The spec gate and the one-shot grill propose a split above 10 criteria."""
    assert "more than 10 acceptance criteria" in step(skill("spec"), "Gate.")
    assert "more than 10 acceptance criteria" in one_shot_spec()
    assert "never splits" in step(skill("spec"), "Gate.")


# Criterion 10: the glossary.


def test_glossary_has_the_review_terms() -> None:
    """`GLOSSARY.md` names the new terms."""
    glossary = (ROOT / "GLOSSARY.md").read_text(encoding="utf-8")
    for term in (
        "| Finding |",
        "| Blocking finding |",
        "| Non-blocking finding |",
        "| Follow-up review |",
        "| Ripple check |",
    ):
        assert term in glossary


# CRAFT-95: the reviewer reads each changed file in full.


def reviewer_task() -> str:
    """Return the quoted task that `craft:review` step 2 gives the fresh reviewer."""
    text = step(skill("review"), "Review in a fresh agent.")
    lines = (line.strip() for line in text.splitlines())
    return " ".join(line[1:].strip() for line in lines if line.startswith(">"))


def files_read_text() -> str:
    """Return the part of the reviewer task that defines **Files read**."""
    task = reviewer_task()
    start = task.index("add a **Files read** list")
    return task[start : task.index("End with the verdict line", start)]


def test_reviewer_opens_each_changed_file_in_full() -> None:
    """Criterion 1, Review focus 4: every changed file, test files too, in full."""
    task = reviewer_task()
    assert "open each changed file of the PR in full on the PR branch" in task
    assert "test files too" in task
    assert "do not rely on the diff alone" in task


def test_review_lists_files_read_before_the_verdict() -> None:
    """Criterion 2: **Files read** comes before the verdict line, each file marked."""
    task = reviewer_task()
    assert "Before the verdict line, add a **Files read** list" in task
    assert task.index("**Files read**") < task.index("End with the verdict line")
    text = files_read_text()
    assert "read in full or skipped" in text
    assert "in a full review, each changed file of the PR" in text


def test_follow_up_files_read_holds_the_files_the_fix_changed() -> None:
    """Criterion 2: a follow-up review lists the files that the fix changed."""
    text = files_read_text()
    assert (
        "in a follow-up review, each file that the fix changed since the previous"
        " review" in text
    )


def test_reviewer_may_skip_deleted_binary_lock_and_generated_files() -> None:
    """Criterion 3, Review focus 1 and 2: the skips, each with its reason."""
    task = reviewer_task()
    assert (
        "You may skip a deleted file, a binary file, a lock file, and a generated"
        " file" in task
    )
    assert "with the reason for each skip" in files_read_text()


def test_follow_up_review_opens_the_files_the_fix_changed() -> None:
    """Criterion 4, Review focus 3: a follow-up opens the fix's files in full."""
    assert (
        "In a follow-up review, open in full each file that the fix changed since"
        " the previous review" in reviewer_task()
    )


def test_findings_lists_each_changed_file_of_a_pr_in_craft_review() -> None:
    """Criterion 5: the clause is scoped to `craft:review`, not the plan review."""
    line = next(
        line
        for line in section(findings(), "Full review").splitlines()
        if "List what you checked" in line
    )
    assert (
        "For a PR in `craft:review`, list each changed file with whether you read"
        " it in full" in line
    )
    assert "craft:plan" not in line


def test_reviewer_task_keeps_the_spec_diff_and_verdict() -> None:
    """Criterion 6: the task still reads the spec and diff, and ends the review."""
    task = reviewer_task()
    assert "Read the `## Spec` of the Linear ticket and the PR diff" in task
    assert task.rstrip().endswith("such as `PASS — 0 blocking, 2 non-blocking`.")


def test_reviewer_opens_and_lists_the_file_of_each_cited_test() -> None:
    """Criterion 8, Review focus 5: a cited test's file is opened and listed."""
    task = reviewer_task()
    assert (
        "open in full the file that holds each test that you cite as evidence for"
        " a criterion or a Review focus line, also when the PR did not change that"
        " file" in task
    )
    assert (
        "name each file that holds a cited test and that the PR did not change" in task
    )
