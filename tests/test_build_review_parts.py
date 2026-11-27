# Copyright (C) 2026 Theo van Oostrum
"""The build review has a Functional and a Technical part, and labels findings."""

from collections.abc import Callable

import pytest

from tests.skill_text import ROOT, RULES, findings, section, skill, step

LABELS = ("`spec`", "`rule`", "`lens`", "`lesson`")
BLOCKING_RULE_LINES = 2


def build_review() -> str:
    """Return the `## Build review` section of `findings.md`."""
    return section(findings(), "Build review")


def reviewer_task() -> str:
    """Return the task that `craft:review` gives the fresh reviewer."""
    return step(skill("review"), "Review in a fresh agent.").split("> ", 1)[1]


def item(text: str, name: str) -> str:
    """Return the bullet of `text` whose bold name is `name`."""
    return text.split(f"- **{name}**", 1)[1].split("\n- ", 1)[0].split("\n\n", 1)[0]


# Criterion 1: two parts, in the build review only.


def test_build_review_has_two_parts() -> None:
    """The build review has a Functional part and a Technical part."""
    text = build_review()
    assert "The build review in `craft:review` has two parts" in text
    assert "**Functional part**" in text
    assert "**Technical part**" in text


def test_spec_and_plan_reviews_have_no_parts_and_no_labels() -> None:
    """Review focus 5: the spec review and the plan review keep their form."""
    text = build_review()
    assert "The spec review and the plan review have no parts and no labels" in text
    assert "a broken engineering rule is no finding there" in text


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("spec-review.md", lambda: (RULES / "spec-review.md").read_text("utf-8")),
        ("plan review", lambda: step(skill("plan"), "Review in a fresh agent.")),
    ],
)
def test_spec_and_plan_review_tasks_name_no_labels(
    name: str, text: Callable[[], str]
) -> None:
    """Review focus 5: the other review tasks name no label and no part."""
    body = text()
    for label in LABELS:
        assert label not in body, name
    assert "Technical part" not in body, name


# Criterion 2: the labels and their severity.


def test_labels_have_their_severity() -> None:
    """`spec` by the lists, `rule` always blocking, `lens` and `lesson` never."""
    lines = build_review().splitlines()
    rows = {
        label: line
        for line in lines
        for label in LABELS
        if line.startswith(f"| {label} |")
    }
    assert set(rows) == set(LABELS)
    assert "Blocking or non-blocking" in rows["`spec`"]
    assert "Always blocking" in rows["`rule`"]
    assert "Always non-blocking" in rows["`lens`"]
    assert "Always non-blocking" in rows["`lesson`"]


def test_each_finding_has_one_label_in_a_fixed_order() -> None:
    """Review focus 3: a finding that fits two labels takes the stronger one."""
    text = build_review()
    assert "Each finding of the build review has exactly one label" in text
    assert "takes the first of `rule`, `spec`, `lens`" in text
    assert "A `lesson` is always a finding of its own" in text


# Criterion 3: `rule` findings and new duplicates.


def test_rule_finding_names_its_rule_and_respects_exceptions() -> None:
    """Review focus 2: a `rule` finding names file and rule; an exception holds."""
    text = item(build_review(), "`rule`.")
    assert "names its rule by file and bold name" in text
    assert "`(exception: <rule name>)`" in text
    assert "is no finding" in text
    assert "the Technical part names each exception that it applied" in text


def test_new_duplicate_cites_the_right_rule() -> None:
    """A copy of repo code and a copy within the PR cite different rules."""
    text = item(build_review(), "New duplicate.")
    assert (
        "A copy of code already in the repo is a `rule` finding against "
        "**Reuse before you write**" in text
    )
    assert (
        "A copy of other new code in the same PR is a `rule` finding against "
        "**Clean up what you touch**" in text
    )
    assert "Each names both places" in text
    assert "at most a `lens` finding" in text


# Criterion 4: `lens` findings.


def test_lens_finding_names_a_smell_or_principle() -> None:
    """A `lens` finding without a named smell or principle is not reported."""
    text = item(build_review(), "`lens`.")
    assert "names one smell" in text
    assert "or one principle" in text
    assert "A finding without such a name is not reported" in text
    assert "No style nitpicks" in text


# Criterion 5: `lesson` findings.


def test_lesson_sits_next_to_a_blocking_rule_finding() -> None:
    """A `lesson` is a rule candidate the build never fixes."""
    text = item(build_review(), "`lesson`.")
    assert "next to a blocking `rule` finding" in text
    assert (
        "only when a more specific rule for this project or stack "
        "would have stopped the problem" in text
    )
    assert "`project` or `stack`" in text
    assert "a bold name and one sentence" in text
    assert "the finding it comes from by its number" in text
    assert "the build never fixes it" in text
    assert "the owner decides on it at the merge gate" in text


# Criterion 6: layout and line format.


def test_layout_lists_the_parts_in_order() -> None:
    """The layout runs from the parts to the verdict line."""
    text = build_review().split("### Layout", 1)[1].split("\n### ", 1)[0]
    order = [
        "`### Functional part`",
        "`### Technical part`",
        "**Blocking**",
        "**Non-blocking**",
        "**Gone**",
        "**Files read**",
        "verdict line",
    ]
    positions = [text.index(part) for part in order]
    assert positions == sorted(positions)
    assert "numbered across both lists" in text
    assert (
        "its label, its number and a link to the review that holds it, and the reason"
        in text
    )


def test_technical_part_always_shows_it_ran() -> None:
    """Review focus 1: with no technical findings, the part still says so."""
    text = build_review().split("### Layout", 1)[1]
    assert "the rule files read" in text
    assert "the duplicate search" in text
    assert "`No technical findings`" in text


def test_finding_line_starts_with_its_label() -> None:
    """The finding line has the number, then the label in backticks."""
    text = build_review()
    assert "its number, its label in backticks, what and where, then why" in text
    assert "`` 3. `rule` — " in text
    assert "A `lesson` adds `(project)` or `(stack)` after its label" in text
    assert "`FAIL — 2 blocking, 3 non-blocking`" in text


# Criterion 7: the blocking list.


def test_blocking_list_has_build_review_rule_findings() -> None:
    """A broken rule and a new duplicate are `rule` findings of the build review."""
    blocking = findings().split("**Blocking**", 1)[1].split("**Non-blocking**", 1)[0]
    lines = [line for line in blocking.splitlines() if "`rule` finding" in line]
    assert any(
        "a broken engineering rule, unless the spec has an exception for it" in line
        for line in lines
    )
    assert any("a new duplicate of existing code" in line for line in lines)
    assert all("in the build review only" in line for line in lines)
    assert len(lines) == BLOCKING_RULE_LINES


# Criterion 12: follow-up review.


def test_follow_up_build_review_keeps_labels_and_copies_forward() -> None:
    """Review focus 4: labels stay, `lens` and `lesson` findings are copied."""
    text = section(findings(), "Follow-up review")
    assert "each earlier blocking finding keeps its label" in text
    assert (
        "copies each earlier `lens` and `lesson` finding forward "
        "with its label, as still open" in text
    )
    assert "mark it `gone`, with a reason" in text
    assert "A copied `lesson` is never `gone`" in text
    assert (
        "keeps its source as the number and a link to the review that holds it" in text
    )
    assert "A `gone` finding is not counted in the verdict line" in text
    assert "the merge gate and the done report leave it out" in text


# Criterion 10: the merge gate.


def test_at_the_gate_has_three_lists() -> None:
    """The merge gate lists lens findings, non-blocking findings, and lessons."""
    text = section(findings(), "At the gate")
    order = [
        "**Lens findings**",
        "**Non-blocking findings** for the `spec` findings",
        "**Lessons**",
    ]
    positions = [text.index(part) for part in order]
    assert positions == sorted(positions)
    assert "owner feedback on it changes no code in the PR" in text


def test_merge_gate_step_has_three_lists() -> None:
    """Step 5 of `craft:review` posts the three lists in `🤖 Gate: merge`."""
    text = step(skill("review"), "If PASS:")
    order = ["**Lens findings**", "**Non-blocking findings**", "**Lessons**"]
    positions = [text.index(part) for part in order]
    assert positions == sorted(positions)
    assert "owner feedback on a `lesson` changes no code in the PR" in text


def test_one_shot_comment_counts_lens_findings() -> None:
    """The one-shot review comment names the number of `lens` findings."""
    text = step(skill("review"), "If PASS:")
    assert (
        "`🤖 review: success — PASS — 0 blocking, <m> non-blocking (<k> lens), "
        "merging (one-shot)`" in text
    )


# Criteria 8 and 9: the reviewer task.


def test_reviewer_writes_both_parts_with_labels() -> None:
    """The reviewer task asks for both parts as `findings.md` describes them."""
    task = reviewer_task()
    assert (
        "the **Functional part** and the **Technical part** "
        "of `## Build review` in `findings.md`" in task
    )
    for label in LABELS:
        assert label in task


def test_reviewer_searches_for_duplicates_and_judges_structure() -> None:
    """Absorbs CRAFT-96: a duplicate search and structure as `lens` findings."""
    task = reviewer_task()
    assert "For each new function, type, or constant in the PR, search the repo" in task
    assert "structure and fit of the change" in task
    assert "as a `lens` finding" in task
    assert (
        "always lists the rule files you read and the duplicate search you made" in task
    )
    assert "`No technical findings`" in task


def test_reviewer_reports_a_test_seam_break_as_a_rule_finding() -> None:
    """A test below the seam that repeats a seam test is a blocking `rule` finding."""
    task = reviewer_task()
    assert "only repeats a test at the seam is a blocking `rule` finding" in task
    assert "seam is a non-blocking finding" not in task
    assert "the `## In CLAUDE.md` bullet of `docs/engineering.md`" in task
    assert "`CLAUDE.md` **Test seams**" in task


# Criterion 11: the done report.


def test_done_report_lists_lens_findings_per_ticket() -> None:
    """The one-shot done report lists each `lens` finding of each ticket."""
    report = step(skill("next"), "Done report.")
    line = next(line for line in report.splitlines() if "`lens` finding" in line)
    assert "each ticket's latest build review" in line
    assert "one line each with its smell or principle and a link to the review" in line
    assert "non-blocking findings per ticket" in report


# Domain docs.


def test_glossary_defines_the_parts_and_new_duplicate() -> None:
    """The glossary has the changed terms and **New duplicate**."""
    glossary = (ROOT / "GLOSSARY.md").read_text(encoding="utf-8")
    assert "| New duplicate |" in glossary
    label = next(
        line for line in glossary.splitlines() if line.startswith("| Finding label |")
    )
    assert "`rule` always blocks; `lens` and `lesson` never do" in label


def test_adr_0012_lets_spec_findings_be_non_blocking() -> None:
    """ADR 0012: a `spec` finding follows the blocking list."""
    adr = (
        ROOT / "docs" / "adr" / "0012-technical-findings-block-only-on-written-rules.md"
    ).read_text("utf-8")
    line = next(line for line in adr.splitlines() if line.startswith("- `spec`:"))
    assert (
        "Blocking or non-blocking, as the blocking list in `findings.md` says" in line
    )


# Owner feedback on a `lesson` (review 1, finding 1).


def test_ripple_check_notes_feedback_on_a_lesson() -> None:
    """Feedback on a `lesson` changes no file, and the fix summary notes it."""
    text = section(findings(), "Ripple check")
    assert "Owner feedback on a `lesson` changes no file" in text
    assert "as `noted`" in text


def test_follow_up_review_accepts_a_noted_lesson() -> None:
    """The follow-up review accepts `noted` for feedback on a `lesson`."""
    text = section(findings(), "Follow-up review")
    assert "`noted` for an item on a `lesson`" in text


def test_build_fix_changes_no_file_for_a_lesson() -> None:
    """The Fix step of `craft:build` notes feedback on a `lesson`."""
    text = section(skill("build"), "Fix")
    assert "owner feedback on a `lesson` changes no file" in text


def test_merge_gate_feedback_on_a_lesson_is_noted() -> None:
    """The gate rule in `craft:rules` excepts feedback on a `lesson`."""
    text = skill("rules")
    gate = text.split("Any other reply from the owner is feedback.", 1)[1]
    gate = gate.split("\n- **", 1)[0]
    assert "feedback on a `lesson`" in gate


def test_glossary_says_a_lesson_is_never_fixed() -> None:
    """The glossary entry of a non-blocking finding names the `lesson`."""
    glossary = (ROOT / "GLOSSARY.md").read_text(encoding="utf-8")
    line = next(
        line
        for line in glossary.splitlines()
        if line.startswith("| Non-blocking finding |")
    )
    assert "A `lesson` is never fixed" in line
