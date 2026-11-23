# Copyright (C) 2026 Theo van Oostrum
"""`craft:audit` scores merged craft PRs in a blind audit.

These tests check the text that the audit step reads: its skill, the core
rubric, and the lines in `craft:rules`, `craft:bstack`, and `models.md`.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "craft" / "skills"
AUDIT = SKILLS / "audit"
ITEMS = ("Design", "Complexity", "Duplication", "Naming", "Tests")


def rubric() -> str:
    """Return the text of the core rubric."""
    return (AUDIT / "rubric.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return the body of the `## <heading>` section of `text`."""
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


# Criterion 2: the core rubric.


def test_the_rubric_has_version_1() -> None:
    """The rubric names its version on its own line."""
    assert re.search(r"^Rubric version: 1$", rubric(), re.MULTILINE)


def test_the_rubric_has_exactly_the_five_items() -> None:
    """Design, complexity, duplication, naming, and tests, in that order."""
    items = re.findall(r"^### (.+)$", section(rubric(), "Items"), re.MULTILINE)
    assert tuple(items) == ITEMS


def test_each_item_says_what_to_look_for() -> None:
    """Each item has a `Look for:` line."""
    for body in section(rubric(), "Items").split("\n### ")[1:]:
        assert "Look for:" in body, body.splitlines()[0]


def test_the_rubric_defines_major_and_minor() -> None:
    """Major asks for a change before merge; minor still approves."""
    text = section(rubric(), "Severity")
    assert "**major**: a careful reviewer would ask for a change before merge" in text
    assert "**minor**: worth a comment, but the reviewer would still approve" in text


def audit() -> str:
    """Return the text of the `craft:audit` skill."""
    return (AUDIT / "SKILL.md").read_text(encoding="utf-8")


def step(name: str) -> str:
    """Return the numbered step of `craft:audit` whose bold name is `name`."""
    rest = audit().split(f"**{name}.**", 1)[1].split("\n## ", 1)[0]
    end = re.search(r"\n\d+\. \*\*", rest)
    return rest[: end.start()] if end else rest


def models() -> str:
    """Return the text of `models.md`."""
    return (SKILLS / "rules" / "models.md").read_text(encoding="utf-8")


# Criterion 1: the skill and its models.


def test_the_skill_has_its_name_and_model() -> None:
    """The skill is `audit`, on opus."""
    header = audit().split("\n---\n", 1)[0]
    assert re.search(r"^name: audit$", header, re.MULTILINE)
    assert re.search(r"^model: opus$", header, re.MULTILINE)


def test_models_lists_the_audit_step_and_the_blind_auditor() -> None:
    """`models.md` has the step row and the subagent row."""
    assert "| Audit | `craft:audit` | opus |" in section(models(), "Steps")
    assert "| blind auditor | `craft:audit` | opus |" in section(models(), "Subagents")


def test_the_skill_loads_rules_and_bstack_first() -> None:
    """Like every step, the audit loads `craft:rules`, then `craft:bstack`."""
    intro = audit().split("\n## ", 1)[0]
    assert "Load the `craft:rules` skill first" in intro
    assert "`craft:bstack`" in intro


# Criterion 3: which PRs the audit selects.


def test_the_projects_come_from_three_sources() -> None:
    """Linear projects, repos in the session, and bucket folders."""
    text = step("Projects")
    assert "Linear project of the `CRAFT` team" in text
    assert "`Linear project` in its `.claude/craft.md`" in text
    assert "every repository in the session" in text
    assert "gs://craft-transcripts" in text
    assert "The Craft Linear project matches `vanoostrum/craft`" in text


def test_an_unreadable_project_gets_a_skipped_row_with_a_reason() -> None:
    """Review focus 2: a project with no readable repo is skipped, with its reason."""
    text = step("Projects")
    assert '"skipped"' in text
    assert "repo not in the environment" in text
    assert "no repository names this Linear project" in text
    assert "even when it has no bucket folder" in text


def test_a_readable_project_without_a_bucket_folder_is_audited() -> None:
    """Review focus 2: such as LibRag; its PRs get "no transcripts"."""
    text = step("Projects")
    assert "A project with a readable repository and no bucket folder" in text
    assert "is still audited" in text
    assert '"no transcripts"' in text


def test_an_unreadable_bucket_does_not_stop_the_audit() -> None:
    """Review focus 2: the audit goes on with the rest."""
    text = step("Projects")
    assert "If the bucket cannot be read, go on" in text


def test_a_craft_pr_is_matched_by_title_and_base_branch() -> None:
    """Merged into the base branch from `.claude/craft.md`, title `[CRAFT-<n>]`."""
    text = audit()
    assert "merged into the project's base branch" in text
    assert "`Base branch` in its `.claude/craft.md`" in text
    assert "title starts with `[CRAFT-<n>]`" in text


def test_the_window_starts_at_the_end_of_the_previous_window() -> None:
    """Or 7 days before the audit starts, and it ends when the audit starts."""
    text = step("Audit window")
    assert "end of the previous report's window" in text
    assert "7 days before" in text
    assert "ends when the audit starts" in text


def test_the_fill_up_takes_earlier_prs_up_to_5() -> None:
    """Fewer than 5 PRs to judge: add the latest earlier PRs no report lists."""
    text = step("Craft PRs")
    assert "fewer than 5" in text
    assert "merged before the window" in text
    assert "that no audit report from before today lists" in text


def test_the_cap_of_40_is_spread_over_projects() -> None:
    """Above 40 PRs to judge, take 40 spread evenly, newest first."""
    text = step("Craft PRs")
    assert "40" in text
    assert "spread evenly over the projects, newest first" in text
    assert "over the cap of 40" in text


# Criterion 4: the blind auditor.


def test_one_fresh_blind_auditor_per_pr_one_at_a_time() -> None:
    """Each PR to judge gets its own fresh subagent, on the `blind auditor` model."""
    text = step("Blind audit")
    assert "one fresh subagent per PR to judge, one at a time" in text
    assert "`blind auditor` model from `models.md`" in text


def test_the_auditor_works_in_a_temporary_directory_without_history() -> None:
    """The files at the merge commit, with no git history."""
    text = step("Blind audit")
    assert "temporary directory" in text
    assert "git archive" in text
    assert "no git history" in text
    assert "Never check out" in text


def test_the_auditor_gets_only_what_the_spec_lists() -> None:
    """The files, the diff, the list of files to judge, conventions, and rubric."""
    text = step("Blind audit")
    for item in ("pr.diff", "files.txt", "`CLAUDE.md`", "linter", "rubric.md"):
        assert item in text


def test_the_auditor_prompt_names_every_ban() -> None:
    """The prompt forbids what would let craft's view leak into the audit."""
    prompt = step("Blind audit").split("> ", 1)[1]
    for banned in (
        "PR title",
        "PR body",
        "PR comments",
        "commit messages",
        "ticket",
        "spec",
        "transcripts",
        "Linear",
        "GitHub",
        "the bucket",
        "git history",
        "the web",
    ):
        assert banned in prompt, banned


# Criterion 5: what is not judged.


def test_the_files_not_judged_are_named() -> None:
    """Review focus 4: lockfiles, generated files, Markdown, and gallery pages."""
    text = step("Files to judge")
    for kind in ("Lockfiles", "Generated files", "Markdown", "`design/`"):
        assert kind in text
    for path in (
        "plugins/craft/hooks/",
        "plugins/craft/skills/*/scripts/",
        "tests/",
        ".github/",
    ):
        assert path in text


def test_a_pr_with_nothing_to_judge_gets_no_auditor() -> None:
    """It does not count in the scores, and is listed as "nothing to judge"."""
    text = step("Files to judge")
    assert '"nothing to judge"' in text
    assert "gets no blind auditor" in text
    assert "does not count in the scores" in text


def test_a_large_diff_leaves_out_only_the_excluded_files() -> None:
    """Review focus 4: the auditor still judges the rest."""
    text = step("Files to judge")
    assert "only the files to judge" in text


# Criterion 6: the craft version of a PR.


def test_the_craft_version_comes_from_the_latest_build_segment() -> None:
    """Else from the release tags, and the PR is marked "no transcripts"."""
    text = step("Craft version")
    assert "latest `build` segment" in text
    assert "`craft_version`" in text
    assert "release time" in text
    assert "`v<version>`" in text
    assert '"no transcripts"' in text


# Criteria 9 and 10: the report and the previous report.


def test_the_report_is_a_linear_document_with_four_sections() -> None:
    """`Audit: <yyyy-mm-dd>` in the Craft project, with its four sections."""
    text = step("Report")
    assert "`Audit: <today>`" in text
    assert "Craft Linear project" in text
    for heading in ("## Summary", "## Scores", "## Findings", "## PRs"):
        assert f"`{heading}`" in text
    assert "headline per project and craft version" in text


def test_the_scores_section_is_the_script_output() -> None:
    """The model does not compute the table."""
    assert "scripts/scores.py" in step("Scores")
    assert "unchanged" in step("Report")


def test_a_second_run_on_the_same_day_replaces_the_report() -> None:
    """Review focus 3: one report, rebuilt; no second document."""
    text = step("Report")
    assert "replace its content" in text
    assert "never create a second" in text


def test_the_previous_report_is_from_an_earlier_day() -> None:
    """Review focus 3: today's own report is never the previous report."""
    text = step("Previous report")
    assert "latest audit report from a day before today" in text
    assert "Today's own report is never the previous report" in text


def test_the_trend_and_window_come_from_the_previous_report() -> None:
    """A rerun takes its window and trend from the report before today's."""
    assert "previous report" in step("Audit window")
    assert "previous report" in step("Scores")


def test_today_is_the_date_in_europe_madrid() -> None:
    """A run just after midnight gets the owner's date, not UTC's."""
    assert "Europe/Madrid" in audit()


# Criterion 11: the PR list.


def test_the_pr_list_names_the_window_and_every_pr() -> None:
    """Window, audited PRs with their fields, nothing to judge, and skipped."""
    text = step("Report")
    assert "Window: <start> to <end>" in text
    for column in ("Repository", "PR", "Ticket", "Craft version", "Status"):
        assert column in text
    for status in ('"audited"', '"nothing to judge"', '"skipped"'):
        assert status in text


# Review focus 1: no PRs.


def test_no_prs_still_writes_the_report_and_says_so() -> None:
    """The report has the empty table, and the message says no PRs were audited."""
    assert "with no PRs too" in step("Report")
    assert "no PRs were audited" in step("Message")


# Criterion 12: the audit message.


def test_the_audit_message() -> None:
    """One chat message, a push notification where available, and its content."""
    text = step("Message")
    assert "one chat message" in text
    assert "push notification" in text
    assert "report link" in text
    assert "each project total and each group total" in text
    assert "trend" in text
    assert '"audited", "nothing to judge", and "skipped"' in text


def test_the_audit_keeps_its_data_in_linear() -> None:
    """No ticket comment, branch, commit, or repo file holds audit data."""
    text = section(audit(), "Outside the ticket flow")
    assert "no ticket, no gate, and no step comment" in text
    assert "no branch" in text
    assert "commits nothing" in text
    assert "`docs/adr/0009`" in text


# Criterion 13: the rules and bstack.


def test_rules_name_the_audit_outside_the_ticket_flow() -> None:
    """`craft:rules` has the audit in its Flow, with its exceptions."""
    flow = section((SKILLS / "rules" / "SKILL.md").read_text(encoding="utf-8"), "Flow")
    assert "`craft:audit`" in flow
    assert "outside the ticket flow" in flow
    assert "no ticket, no gate, and no step comment" in flow
    assert "`docs/adr/0009`" in flow


def test_bstack_names_the_blind_auditor_as_single_purpose() -> None:
    """One blind auditor per PR is not a cluster."""
    text = (SKILLS / "bstack" / "SKILL.md").read_text(encoding="utf-8")
    single = text.split("single-purpose subagents", 1)[1].split("\n\n", 1)[0]
    assert "blind auditor" in single
