# Copyright (C) 2026 Theo van Oostrum
"""`craft:audit` judges craft's phases against rubrics; fixes go to craft, not the code.

These tests check the text that the audit step reads: its skill, and the lines
in `craft:rules`, `craft:bstack`, and `models.md`. The rubric files and the
scripts have their own tests.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "craft" / "skills"
AUDIT = SKILLS / "audit"


def audit() -> str:
    """Return the text of the `craft:audit` skill."""
    return (AUDIT / "SKILL.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return the body of the `## <heading>` section of `text`."""
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def step(name: str) -> str:
    """Return the numbered step of `craft:audit` whose bold name is `name`."""
    rest = audit().split(f"**{name}.**", 1)[1].split("\n## ", 1)[0]
    end = re.search(r"\n\d+\. \*\*", rest)
    return rest[: end.start()] if end else rest


def models() -> str:
    """Return the text of `models.md`."""
    return (SKILLS / "rules" / "models.md").read_text(encoding="utf-8")


# Criterion 1: the skill, outside the ticket flow, and its models.


def test_the_skill_has_its_name_and_model() -> None:
    """The skill is `audit`, on opus."""
    head = audit().split("\n---\n", 1)[0]
    assert re.search(r"^name: audit$", head, re.MULTILINE)
    assert re.search(r"^model: opus$", head, re.MULTILINE)


def test_the_audit_judges_the_process_not_the_code() -> None:
    """`docs/adr/0010`: code is evidence; fixes go to craft, never the code."""
    text = audit()
    assert "The audit judges the craft process (`docs/adr/0010`)" in text
    assert "may read code" in text
    assert "never proposes a fix to a project's code" in text
    assert "never scores the code on its own" in text


def test_the_audit_keeps_its_data_in_linear() -> None:
    """No ticket comment, branch, commit, or repo file holds audit data."""
    text = section(audit(), "Outside the ticket flow")
    assert "no ticket, no gate, and no step comment" in text
    assert "makes no branch, commits nothing" in text
    assert "only into the audit report in Linear (`docs/adr/0009`)" in text


def test_models_lists_the_audit_step_and_the_audit_judge() -> None:
    """Both on opus; the blind auditor is gone."""
    text = models()
    assert "| Audit | `craft:audit` | opus |" in text
    assert "| audit judge | `craft:audit` | opus |" in text
    assert "blind auditor" not in text


def test_the_skill_loads_rules_and_bstack_first() -> None:
    """As every craft step does."""
    text = audit()
    assert "Load the `craft:rules` skill first" in text
    assert "load `craft:bstack`" in text


def test_rules_name_the_audit_outside_the_ticket_flow() -> None:
    """`craft:rules` has the audit in its Flow, with its exceptions."""
    flow = section((SKILLS / "rules" / "SKILL.md").read_text(encoding="utf-8"), "Flow")
    assert "`craft:audit`" in flow
    assert "outside the ticket flow" in flow
    assert "no ticket, no gate, and no step comment" in flow
    assert "`docs/adr/0009`" in flow


def test_bstack_names_the_audit_judge_as_single_purpose() -> None:
    """One audit judge per ticket is not a cluster."""
    text = (SKILLS / "bstack" / "SKILL.md").read_text(encoding="utf-8")
    single = text.split("single-purpose subagents", 1)[1].split("\n\n", 1)[0]
    assert "audit judge" in single


# Criterion 2: how the audit finds its tickets.


def test_the_projects_come_only_from_the_linear_team() -> None:
    """Matched by `Linear project` in `.claude/craft.md`; repos are no source."""
    text = step("Projects")
    assert "the Linear projects of the `CRAFT` team" in text
    assert "`Linear project` in its `.claude/craft.md`" in text
    assert "A repository or a bucket folder is not a source of projects" in text


def test_an_audited_ticket_is_a_craft_pr_merged_in_the_window() -> None:
    """A `[CRAFT-<n>]` PR into the project's `Base branch`."""
    text = section(audit(), "Outside the ticket flow")
    assert "merged into the project's `Base branch`" in text
    assert "starts with `[CRAFT-<n>]`" in text
    assert "`merged_at` is in the audit window" in step("Audited tickets")


def test_the_window_starts_at_the_end_of_the_previous_window() -> None:
    """Read from `## Tickets`, or `## PRs` in the CRAFT-85 format; else 7 days."""
    text = step("Audit window")
    assert "end of the previous report's window" in text
    assert "`## Tickets`" in text
    assert "`## PRs` in the CRAFT-85 format" in text
    assert "7 days before the audit starts" in text


def test_earlier_reports_list_tickets_in_either_format() -> None:
    """Review focus 2: `Audit: 2026-11-23` lists its PRs under `## PRs`."""
    text = step("Previous report")
    assert "from its `## Tickets` section, or from `## PRs`" in text
    assert "`Audit: 2026-11-23`" in text
    assert "leaves out each ticket that any of them lists" in text


def test_the_previous_report_is_from_an_earlier_day() -> None:
    """Today's own report is never the previous report."""
    text = step("Previous report")
    assert "latest audit report from a day before today" in text
    assert "Today's own report is never the previous report" in text


def test_the_fill_up_takes_earlier_tickets_up_to_5() -> None:
    """Tickets that no earlier report lists."""
    text = step("Audited tickets")
    assert "fewer than 5 tickets to judge" in text
    assert "that no audit report from before today lists" in text


def test_the_cap_of_40_is_spread_over_projects() -> None:
    """Newest first, one project at a time."""
    text = step("Audited tickets")
    assert "more than 40 tickets to judge" in text
    assert "spread evenly over the projects, newest first" in text
    assert '"over the cap of 40"' in text


def test_the_limits_count_only_judged_tickets() -> None:
    """Review focus 5: a plan PR counts toward neither limit."""
    text = step("Audited tickets")
    assert "count only tickets that at least one rubric that runs judges" in text
    assert "counts toward neither limit" in text


# Criterion 3: which rubrics run.


def test_no_argument_runs_every_rubric_without_an_underscore() -> None:
    """From `rubrics/` and `rubrics/custom/`."""
    text = step("Rubrics")
    assert "each file in `rubrics/` and `rubrics/custom/`" in text
    assert "whose name does not start with `_`" in text


def test_a_rubric_argument_runs_one_rubric() -> None:
    """`rubric=<name>`, phase rubrics first, then custom rubrics."""
    text = step("Rubrics")
    assert "With `rubric=<name>`, it judges only that rubric" in text
    assert "looks in `rubrics/` first, then in `rubrics/custom/`" in text


def test_an_unknown_rubric_stops_the_audit() -> None:
    """Review focus 3: the list of names, and no report."""
    text = step("Rubrics")
    assert "An unknown name stops the audit" in text
    assert "with the list of rubric names" in text
    assert "write no report" in text


# Criterion 4: the rubric file format.


def test_the_skill_describes_the_rubric_file_format() -> None:
    """Every line of the format."""
    text = section(audit(), "Rubric file")
    for line in (
        "`# <Name> rubric`",
        "`Rubric version: <n>`",
        "`Phase: <phase>`",
        "`Phase: custom`",
        "`Applies to: tickets with a spec`",
        "`## Items`",
        "`Kind:` (Measure, Check, or Escape)",
        "`Reads:`",
        "`Score:`",
        "`Pass:`, `Partial:`, and `Fail:`",
        "`Per: craft version`",
    ):
        assert line in text, line


def test_an_escape_item_is_not_scored_yet() -> None:
    """Until CRAFT-92."""
    text = section(audit(), "Rubric file")
    assert 'An **Escape** item is "not scored yet"' in text
    assert "`scores.py` prints no row for it" in text


def test_a_rubric_that_applies_to_tickets_with_a_spec() -> None:
    """Review focus 5: other tickets are "not in this phase" and count nowhere."""
    text = section(audit(), "Rubric file")
    assert "description has a `## Spec`" in text
    assert '"not in this phase"' in text
    assert "count in none of its scores" in text


# Criterion 6: the audit judge.


def test_the_judge_gets_the_process_inputs_and_the_diff() -> None:
    """The rubric, the spec, the PR and its diff, the comments, and the digests."""
    text = step("Judge")
    for part in (
        "the rubric file",
        "the ticket's `## Spec`",
        "the PR title, the PR body, and the list of changed files",
        "the PR diff",
        "as evidence of what the phase saw or missed",
        "the project's repository at the PR's `merge_commit_sha`",
        "the PR's review comments",
        "the digest of the rubric's phase from step 7",
    ):
        assert part in text, part
    assert "one at a time" in text
    assert "`audit judge` model" in text


def test_the_judge_answers_with_evidence() -> None:
    """Pass, partial, fail, or no data, with what it cites."""
    text = step("Judge")
    assert "`<item> | <pass, partial, fail, or no data> | <evidence>`" in text
    assert "Judge the phase, not the code" in text
    assert "never propose a fix to the project's code" in text
    assert "name the craft phase, skill, or rule" in text


def test_no_review_segment_gives_no_data_not_fail() -> None:
    """Review focus 1: GitHub checks and measures are still scored."""
    text = step("Digests")
    assert 'Its checks that read a digest are "no data", not fail' in text
    assert "Criteria evidence" in text
    assert "measures are still scored" in text
    assert "whose `Reads:` line names the transcript digest" in text
    assert "whatever the judge answered" in step("Judge")


def test_the_digest_comes_from_the_full_review() -> None:
    """The first review subagent, else the segment's part of the session."""
    text = step("Digests")
    assert 'whose `role` contains "review", case-insensitive' in text
    assert "scripts/digest.py" in text
    assert "never the raw transcript" in text


def test_process_logic_is_judged_once_per_craft_version() -> None:
    """At the release tag, copied only for the same rubric version."""
    text = step("Process logic")
    assert "once per rubric and craft version" in text
    assert "the release tag `v<version>`" in text
    assert "same rubric, rubric version, craft version, and item" in text
    assert "With another rubric version, judge again" in text


def test_process_logic_may_read_other_craft_files_as_evidence() -> None:
    """It judges the `Reads:` files, and may read any file at the tag."""
    text = step("Process logic")
    assert "may read any other file at that tag" in text
    assert "`hooks/hooks.json`" in text
    assert "the hook tests" in text


def test_process_logic_leaves_out_missing_files() -> None:
    """A hook or rule file missing at an old tag; with no hooks, no data."""
    text = step("Process logic")
    assert "does not exist at that tag" in text
    assert "is left out of the judge's input" in text
    assert 'the result is "no data"' in text


def test_the_craft_version_comes_from_the_rubrics_phase() -> None:
    """The latest review segment, else the release before the merge."""
    text = step("Craft version")
    assert "`step` is the rubric's phase: `review` for the Review rubric" in text
    assert "`craft_version` of the latest of its segments" in text
    assert "release time" in text
    assert '"no transcripts"' in text


# Review focus 4 and criterion 8: a PR that merged without a PASS.


def test_findings_rounds_marks_no_pass() -> None:
    """The status goes into the rubric's section."""
    text = step("Measures")
    assert "scripts/rounds.py" in text
    assert "`no PASS` for a PR that merged without a PASS" in text
    assert "`no data` for a PR with no verdict line" in text


# Criteria 9 and 10: the scores, the report, and the message.


def test_the_scores_section_is_the_script_output() -> None:
    """The model does not compute the table."""
    assert "scripts/scores.py" in step("Scores")
    assert "previous report" in step("Scores")
    assert "`scores.py`, unchanged" in step("Report")


def test_the_report_has_its_sections() -> None:
    """`Audit: <today>` in the Craft project, with its sections in order."""
    text = step("Report")
    assert "`Audit: <today>` in the Craft Linear project" in text
    positions = [
        text.index(heading)
        for heading in (
            "`## Summary`",
            "`## Scores`",
            "`## <Rubric name>`",
            "`## Tickets`",
        )
    ]
    assert positions == sorted(positions)
    assert "the audited tickets per project" in text


def test_a_rubric_section_lists_what_it_did_not_judge() -> None:
    """Not in this phase, Process logic per craft version, and escapes."""
    text = step("Report")
    assert '"Not in this phase:"' in text
    assert "the Process logic result per craft version" in text
    assert '"not scored yet"' in text


def test_the_ticket_list_names_the_window_and_every_ticket() -> None:
    """Window, then each ticket with its status."""
    text = step("Report")
    assert "`Window: <start> to <end>`" in text
    for column in ("Repository", "PR", "Ticket", "Craft version", "Status"):
        assert column in text
    for status in ('"audited"', '"not in this phase"', '"skipped"'):
        assert status in text


def test_a_second_run_on_the_same_day_replaces_the_report() -> None:
    """One report, rebuilt; no second document."""
    text = step("Report")
    assert "replace its content" in text
    assert "never create a second" in text


def test_the_audit_message() -> None:
    """One chat message, a push notification where available, and its content."""
    text = step("Message")
    assert "one chat message" in text
    assert "push notification" in text
    assert "report link" in text
    assert "phase score of each rubric per craft version" in text
    assert "trend" in text


def test_today_is_the_date_in_europe_madrid() -> None:
    """A run just after midnight gets the owner's date, not UTC's."""
    assert "Europe/Madrid" in audit()


# CRAFT-91: the audit is generic over the rubric's phase (criteria 3, 4, 5, 8).


def test_the_craft_version_of_the_build_rubric_comes_from_build_segments() -> None:
    """The latest build segment for the Build rubric."""
    assert "`build` for the Build rubric" in step("Craft version")


def test_each_phase_has_its_digest() -> None:
    """Criterion 3: the full review for review and custom; build gets its own."""
    text = step("Digests")
    assert "the full review for `Phase: review` and for custom rubrics" in text
    assert "the build digest for `Phase: build`" in text


def test_the_build_digest_holds_every_build_segment_and_subagent() -> None:
    """Criterion 3 and Review focus 2: in `started_at` order, each after its line."""
    text = step("Digests")
    assert "every build segment" in text
    assert "digest.py sessions/<id>/session.jsonl.gz <started_at> <ended_at>" in text
    assert "sessions/<id>/subagents/agent-<agent_id>.jsonl.gz" in text
    assert "in `started_at` order" in text
    assert "`== <role> <started_at> ==`" in text
    assert "retries and fixes after a review FAIL" in text


def test_the_build_digest_keeps_subagent_results_readable() -> None:
    """Criterion 5: a cap of 2,000 for subagent transcripts, 300 for the session."""
    text = step("Digests")
    assert "`--result-cap 2000`" in text
    assert "head and the tail" in text


def test_a_ticket_with_no_segment_of_the_phase_has_no_digest() -> None:
    """Criterion 3 and Review focus 1: a LibRag ticket's build checks."""
    text = step("Digests")
    assert "A ticket with no segment of the rubric's phase" in text
    assert "has no digest" in text
    assert "names the transcript digest or the build digest" in text
    assert "Tests check behavior" in text


def test_the_judge_gets_the_extra_inputs_that_reads_names() -> None:
    """Criterion 4: each extra input, as its own file."""
    text = step("Judge")
    for part in (
        "each extra input that an item of the rubric names in its `Reads:` line",
        "`python3 <audit>/scripts/test_diff.py files.json`",
        "the project's `CLAUDE.md` at the PR's `merge_commit_sha`",
        'gh api "repos/<repo>/pulls/<n>/commits?per_page=100"',
        "each commit's SHA, message, and time",
        "`gh api repos/<repo>/commits/<sha>`",
        "the titles of the ticket's Linear attachments",
    ):
        assert part in text, part


def test_reads_sets_what_to_judge_not_what_to_read() -> None:
    """Criterion 4: no limit on which code the judge may read."""
    text = step("Judge")
    assert "`Reads:` sets what an item must judge" in text
    assert "may still read other code as evidence" in text
    skill = audit().lower()
    for limit in ("only the diff", "not the diff", "may not read", "must not read"):
        assert limit not in skill, limit


def test_the_judge_prompt_says_a_cut_result_is_no_evidence_against() -> None:
    """Criterion 5: the judge compares only what the digest keeps."""
    text = step("Judge")
    assert "A cut result is never evidence against a match or a red run" in text
    assert "compare only the part that the digest keeps" in text


def test_measures_run_per_rubric() -> None:
    """Criterion 8: `rounds.py` for Review, `build.py` for Build."""
    text = step("Measures")
    assert "each Measure of each rubric that judges the ticket" in text
    assert "`rounds.py` for Review" in text
    assert "`build.py` for Build" in text
    for part in (
        "python3 <audit>/scripts/build.py attempts build.json",
        "python3 <audit>/scripts/build.py speed build.json",
        "`Required CI checks`",
        "check-runs?filter=all&per_page=100",
    ):
        assert part in text, part


def test_build_process_logic_is_judged_on_its_reads_at_the_tag() -> None:
    """Criterion 8: the hooks and the script of the Build rubric."""
    text = step("Process logic")
    assert "For the Build rubric" in text
    assert "`skills/rules/scripts/gallery-shot`" in text
    assert "the files that the item's `Reads:` line names" in text
    assert "It judges only the files that `Reads:` names" in text


def test_ci_reds_see_runs_that_were_run_again() -> None:
    """Review 1: the default `filter=latest` hides a red run that was re-run."""
    assert "re-run" in step("Measures")
