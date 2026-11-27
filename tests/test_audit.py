# Copyright (C) 2026 Theo van Oostrum
"""`craft:audit` judges craft's phases against rubrics; fixes go to craft, not the code.

These tests check the text that the audit step reads: its skill, and the lines
in `craft:rules`, `craft:bstack`, and `models.md`. The rubric files and the
scripts have their own tests.
"""

import re

from tests.skill_text import ROOT, SKILLS, section

AUDIT = SKILLS / "audit"


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
    assert (
        "It writes only to Linear: the audit report, the proposal tickets, and the "
        "label `audit` when the team does not have it yet (`docs/adr/0009`)."
    ) in text
    assert "never into a repository, a PR, a GitHub comment, or a project file" in text


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


def test_an_escape_item_counts_the_escapes_of_its_phase() -> None:
    """CRAFT-92 criterion 1: at most one, and none in a custom rubric."""
    text = section(audit(), "Rubric file")
    assert "not scored yet" not in text
    assert "An **Escape** item counts the escapes" in text
    assert "per searched ticket" in text
    assert "at most one Escape item" in text
    assert "A custom rubric has no Escape item" in text


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
    assert "not scored yet" not in text


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


def test_the_report_names_each_ticket_by_its_title() -> None:
    """Owner feedback at the CRAFT-91 merge gate: show what each ticket was about."""
    text = step("Report")
    assert "`### <repo>#<n> (<ticket>): <title>`" in text
    assert "the Linear title of the ticket" in text
    assert "the columns Repository, PR, Ticket, Title, Craft version" in text
    not_judged = '"Not in this phase:" with the tickets it does not judge'
    assert f"{not_judged}, each with its title" in text


# CRAFT-92: escapes (criteria 2, 5, 6, 8, and 9).


def test_the_audit_searches_audited_and_look_back_tickets() -> None:
    """Criterion 2: two sets of searched tickets."""
    text = step("Escapes")
    assert 'lists as "audited" or "not in this phase"' in text
    assert "for fix PRs and for gate feedback" in text
    assert "**look-back tickets**" in text
    assert "in the 14 days before the window start, for fix PRs only" in text
    assert 'with the status "look-back"' in text
    assert "count toward no limit and get no check" in text
    assert "A ticket skipped over the cap is not searched" in text


def test_step_5_lists_the_prs_back_to_14_days_before_the_window() -> None:
    """Criterion 2: every merged PR with its changed paths in `prs.json`."""
    text = step("Audited tickets")
    assert "14 days before the window start" in text
    assert "`updated_at`" in text
    assert "every merged PR in that span, with any title" in text
    assert "`prs.json`" in text
    assert "`number`, `title`, `merged_at`, and `files`" in text


def test_each_escape_counts_once() -> None:
    """Criterion 2 and Review focus 2: no stored state."""
    text = step("Escapes")
    assert "the audit whose window holds the fix PR's `merged_at`" in text
    assert (
        "A gate feedback escape counts in the audit whose `## Tickets` lists the "
        'ticket as "audited" or "not in this phase"'
    ) in text


def test_the_skill_runs_the_escape_scripts() -> None:
    """Criteria 3 and 4: the scripts find the sources."""
    text = step("Escapes")
    assert (
        "scripts/escapes.py candidates prs.json searched.txt <window start> "
        "<window end>"
    ) in text
    assert "scripts/escapes.py gates" in text
    assert "`<merged_at>`" in text


def test_the_escape_judge_gets_its_inputs() -> None:
    """Criterion 5: the ticket, its PR, the candidates, the spans, the skills."""
    text = step("Escapes")
    for part in (
        "the ticket's description, with its `## Spec` when it has one",
        "the ticket's PR title, body, changed file list, and diff",
        "the project's repository at the PR's `merge_commit_sha`",
        (
            "each candidate's title, body, changed file list, and the patch of each "
            "shared path"
        ),
        "each gate span with feedback, as `escapes.py gates` prints it",
        "at the release tag `v<version>` of the ticket's craft version in that phase",
        "plan: `plan/SKILL.md`",
        (
            "spec: `spec/SKILL.md`, `rules/spec-review.md`, `design/SKILL.md`, and "
            "`rules/gallery.md`"
        ),
        "build: `build/SKILL.md`",
        "review: `review/SKILL.md` and `rules/findings.md`",
        "`rules/SKILL.md`, with the gates, at the latest of these tags",
        "40,000 characters",
    ):
        assert part in text, part


def test_the_escape_judge_runs_only_with_a_source() -> None:
    """Criterion 5 and Review focus 4: no source, no judge, 0 escapes."""
    text = step("Escapes")
    assert (
        "One fresh audit judge per searched ticket that has a fix PR candidate" in text
    )
    assert "one at a time" in text
    assert "A ticket with neither needs no judge and has 0 escapes" in text


def test_the_escape_judge_prompt_and_answers() -> None:
    """Criterion 5: one phase, the earlier on a tie, and code only as evidence."""
    text = step("Escapes")
    for part in (
        (
            "Name the one phase whose skill text most directly asks for the check "
            "that would have caught it; on a tie, the earlier phase."
        ),
        (
            "Read the code as evidence, but judge the phase, not the code, and never "
            "propose a fix to the project's code."
        ),
        (
            "`<source> | escape | <phase> | also missed by: <phases or none> | "
            "<why, with evidence>`"
        ),
        (
            "`<source> | not an escape | <owner choice, planned change, or unrelated> "
            "| <why>`"
        ),
        '"not judged"',
        '"Planned change"',
        '"Unrelated"',
        '"Owner choice"',
    ):
        assert part in text, part


def test_an_escape_counts_at_the_version_of_its_phase() -> None:
    """Criterion 6: that phase's segments, else the release before the merge."""
    text = step("Escapes")
    assert "the ticket's craft version in the escape's phase" in text
    assert "latest segment with that `step`" in text
    assert "the release before the ticket PR's `merged_at`" in text


def test_audit_json_holds_the_escapes() -> None:
    """Criterion 7: the shape that `scores.py` reads."""
    text = step("Scores")
    assert "`escapes`" in text
    assert "`searched`" in text
    assert "`traces`" in text


def test_a_rubric_argument_still_traces_every_escape() -> None:
    """Criterion 8: the window moves, so every escape is traced."""
    text = step("Escapes")
    assert (
        "With `rubric=<name>`, the audit still searches and traces every escape" in text
    )
    assert "`## Escapes` lists them all" in text
    assert (
        "`## Scores` prints the escape row of the rubric that ran and the "
        "`No rubric` rows"
    ) in text


def test_the_report_has_an_escapes_section() -> None:
    """Criterion 9: before `## Tickets`, with its table and Not escapes."""
    text = step("Report")
    assert text.index("`## <Rubric name>`") < text.index("`## Escapes`")
    assert text.index("`## Escapes`") < text.index("`## Tickets`")
    for column in ("Ticket", "Craft version", "Source", "Phase", "Also missed by"):
        assert column in text
    assert '"Not escapes:"' in text
    assert "Blind spots" in text
    assert '"look-back"' in text


def test_the_summary_and_the_message_give_escapes_per_phase() -> None:
    """Criterion 9."""
    assert "the escape count per phase" in step("Report")
    assert "the escape count per phase" in step("Message")


GLOSSARY_ROWS = (
    (
        "| Escape | A problem found after a ticket passed a phase: a fix PR that "
        "merged within 14 days after the ticket's PR and changes a file it changed, "
        "or the owner's feedback at a gate. An audit judge traces each escape to the "
        "one phase that should have caught it. As a rubric item, it shows these "
        "escapes per searched ticket, per craft version. |"
    ),
    (
        "| Escape trace | The audit judge's answer for one escape: the phase that "
        "should have caught it, the other phases that missed it, and why, with "
        "evidence. |"
    ),
    (
        "| Fix PR candidate | A PR that merged in the audit window, at most 14 days "
        "after a ticket's PR, and changes a file that the ticket's PR changed. The "
        "audit judge decides whether it fixes a problem of the ticket. |"
    ),
    (
        "| Owner choice | Gate feedback in which the owner changes their mind or adds"
        " a new wish. No phase should have caught it, so it is not an escape. |"
    ),
    (
        "| Blind spot | An escape that an audit judge traces to the review phase. The"
        " Review rubric counts blind spots in its Blind spots item. |"
    ),
)


def test_the_glossary_has_the_escape_terms() -> None:
    """Criterion 10: Escape, Blind spot, and the three new terms."""
    lines = (ROOT / "GLOSSARY.md").read_text(encoding="utf-8").splitlines()
    for line in GLOSSARY_ROWS:
        assert line in lines, line
    escape = lines.index(GLOSSARY_ROWS[0])
    assert lines[escape + 1 : escape + 4] == list(GLOSSARY_ROWS[1:4])


def test_a_ticket_is_searched_once() -> None:
    """Review 1 finding 1: one entry per ticket, with all of its PRs."""
    text = step("Escapes")
    assert "Each searched ticket is searched once" in text
    assert "every PR of the ticket" in text
    assert "is not also a look-back ticket" in text
    assert "one entry per searched ticket" in step("Scores")


# CRAFT-93: patterns and proposals.


def test_patterns_come_from_the_script() -> None:
    """Criteria 2 to 4: the model does not find patterns by hand."""
    text = step("Patterns")
    assert "`python3 <audit>/scripts/patterns.py find scores.md previous.md`" in text
    assert "or without `previous.md` when there is no previous report" in text
    assert (
        "`<kind> | <rubric> | <rubric version> | <craft version> | <item> | <value> "
        "| <why>`"
    ) in text
    assert "in the kind order `process logic`, `check`, `trend`" in text


def test_the_pattern_rule() -> None:
    """Q1 to Q3: audit-wide rows, partials count, Process logic by itself."""
    text = step("Patterns")
    assert "at least 3 tickets with fail or partial" in text
    assert "a minor problem counts only as part of a pattern" in text
    assert "is a pattern by itself" in text
    assert "each need Judged of at least 3" in text
    assert "The Phase score and Check rows give no trend" in text
    assert "with one that has no audit-wide rows, there is no trend pattern" in text


def test_an_old_process_logic_row_before_a_release_is_no_pattern() -> None:
    """Criterion 6, CRAFT-99 criterion 10: the pattern's craft version, by number."""
    text = step("Patterns")
    assert (
        "Leave out the pattern when its craft version is before the Released in of a "
        "**Done** proposal for the same rubric and item"
    ) in text
    assert (
        "Compare the two by number, as `version_order` in `scores.py` does, after one "
        "leading `v` is dropped from Released in, so `v2.10.0` is after 2.9.2."
    ) in text


def test_a_process_logic_item_is_one_pattern() -> None:
    """CRAFT-99 criterion 10: one pattern per rubric and item."""
    text = step("Patterns")
    assert "It gives one pattern per rubric and item" in text
    assert "the line names the newest of those craft versions and its result" in text


def test_at_most_one_proposal_per_rubric_and_item() -> None:
    """CRAFT-99 criterion 10: the Cap rule, and Moved since the release."""
    text = step("Proposals")
    assert "one per pattern, and at most one per rubric and item" in text
    assert (
        "For a released Process logic proposal, Moved uses only Process logic "
        "results at or after its Released in"
    ) in text
    assert "`no data (no result since release)`" in text
    assert "`released` may have a leading `v`." in text


def test_four_kinds_of_proposal_block_a_pattern() -> None:
    """Criterion 6, Review focus 2 and 6: open, unreleased, tracked, canceled."""
    text = step("Proposals")
    assert (
        "A pattern gets no new ticket while a proposal for the same rubric and item, "
        "at any rubric version, blocks it."
    ) in text
    for case in (
        "open: any state but **Done** and **Canceled**",
        "**Done** and not released yet",
        "**Done**, released, and still tracked",
        ("**Canceled**, and the rubric has the same rubric version as at the proposal"),
    ):
        assert case in text, case
    assert '"Already proposed:"' in text
    assert "with the proposal that blocks it" in text


def test_a_pattern_after_untracked_done_proposals_gets_a_new_one() -> None:
    """Criterion 6: the change did not fix it, so a new proposal links the old."""
    text = step("Proposals")
    assert (
        "When the only earlier proposals for the item are **Done** and no longer "
        "tracked, the pattern gets a new proposal, which links the earlier one"
    ) in text


def test_at_most_10_new_proposals_in_find_order() -> None:
    """Criterion 6 and Review focus 5: 12 patterns give 10 tickets and 2 over."""
    text = step("Proposals")
    assert "At most 10 new proposals per audit, one per pattern" in text
    assert "in the order that `find` prints them" in text
    assert "after the patterns that a blocking proposal covers are left out" in text
    assert '"Over the cap of 10:"' in text


def test_the_proposal_ticket() -> None:
    """Criterion 7: team, project, Backlog, label, title, and sections in order."""
    text = step("Proposals").split("**Proposal ticket.**", 1)[1]
    assert (
        "in the `CRAFT` team and the Craft Linear project, in **Backlog**, with the "
        "label `audit`"
    ) in text.replace("Create it in", "in")
    assert "Create the label in the team when it does not exist" in text
    assert "Its title names only the craft change" in text
    parts = [
        "`Proposed by [Audit: <today>](<report link>).`",
        "`## Goal`",
        "`## Measure`",
        "`## Evidence`",
        "`## Steering`",
    ]
    positions = [text.index(part) for part in parts]
    assert positions == sorted(positions)
    assert "`Measure: <rubric> | <rubric version> | <item>`" in text
    assert "`Value at proposal: <value> (<Judged> judged)`" in text
    assert (
        '"note: The acceptance criteria name no findings. The examples stay in the '
        "`## Evidence` section of this ticket, which links the audit report. The PR "
        "(its title, its body, every comment, and every commit), the branch name, and "
        "every repo file, tests and fixtures too, quote only craft's skill text and "
        'summary numbers."'
    ) in text


def test_proposals_stay_in_linear_and_change_only_craft() -> None:
    """Criterion 7 and the constraints."""
    text = step("Proposals")
    assert "It changes only craft, never a project's code (`docs/adr/0010`)" in text
    assert (
        "The audit writes proposals only to Linear: never to a repository, a PR, or a "
        "file."
    ) in text
    assert "no new subagent" in text


def test_the_skill_names_proposals_outside_the_flow_and_when_done() -> None:
    """Criterion 7: the description, Outside the ticket flow, and Done when."""
    assert "proposal tickets in Backlog" in audit().split("---", 2)[1]
    assert "the proposal tickets, and the label `audit`" in section(
        audit(), "Outside the ticket flow"
    )
    done = section(audit(), "Done when")
    assert (
        "the new proposals of step 14 exist in **Backlog** with the label `audit`"
        in done
    )


def test_the_earlier_proposals_that_are_listed() -> None:
    """Criterion 8: which ones, Released in, tracking, and `moved`."""
    text = step("Proposals")
    assert (
        "lists the earlier proposals that are open, **Done** and not released, or "
        "released and still tracked. It lists no **Canceled** proposal"
    ) in text
    assert "`git tag --contains <merge_commit_sha>`" in text
    assert "the first release tag `v<version>` of `vanoostrum/craft`" in text
    assert "until the 4th audit report dated after the day of its release time" in text
    assert "patterns.py moved --ran" in text
    assert "`No rubric` always counts as run" in text


def test_the_report_has_a_proposals_section() -> None:
    """Criterion 9: after `## Escapes`, before `## Tickets`, with its parts."""
    text = step("Report")
    assert text.index("`## Escapes`") < text.index("`## Proposals`")
    assert text.index("`## Proposals`") < text.index("`## Tickets`")
    section_text = text.split("`## Proposals`", 1)[1].split("`## Tickets`", 1)[0]
    positions = [
        section_text.index(part)
        for part in (
            "`### New`",
            '"Already proposed:"',
            '"Over the cap of 10:"',
            "`### Earlier proposals`",
        )
    ]
    assert positions == sorted(positions)
    assert "the count of patterns and of new proposals" in text


def test_the_message_lists_the_new_proposals_and_what_moved() -> None:
    """Criterion 9."""
    text = step("Message")
    assert "the new proposals, each with its title and link" in text
    assert "how many earlier proposals moved better and how many worse" in text


def test_a_rubric_argument_limits_the_patterns() -> None:
    """Criterion 9: the rubric that ran and the `No rubric` rows."""
    assert (
        "patterns come only from the rubric that ran and from the `No rubric` escape "
        "rows"
    ) in step("Patterns")
    assert "`no data (rubric not run)`" in step("Proposals")


PROPOSAL_GLOSSARY_ROWS = (
    (
        "| Pattern | A problem that an audit finds across tickets or audits: a check "
        "that fails or is partial on at least 3 audited tickets in one audit; a "
        "measure or escape rate whose audit-wide row is worse than at the last audit, "
        "two audits in a row; or a Process logic check that fails or is partial at "
        "one or more craft versions, which is one pattern per rubric and item. A "
        "minor problem counts only as part of a pattern. Only a pattern leads to a "
        "proposal. |"
    ),
    (
        "| Proposal | A change to a craft skill or step that an audit proposes from a "
        "pattern, with the measure it should move and that measure's value at the "
        "proposal. It is a ticket in **Backlog** with the label `audit`. It links the "
        "audit report, and its ticket and spec may describe the evidence behind it, "
        "with short examples. Its title names only the craft change. Its PR, branch, "
        "and repo files quote only craft's own skill text and summary numbers, and a "
        "`note=` on the ticket tells every step so (`docs/adr/0009`). Later audits "
        "report how its measure moved after its release. |"
    ),
    (
        "| Audit-wide row | A row of `## Scores` with the craft version `all`: the "
        "Phase score, a per-ticket check, a measure value, or an escape row, over all "
        "tickets of one audit that its rows per craft version count. The Pattern rule "
        "compares these rows between audits. |"
    ),
)


def test_the_glossary_has_the_proposal_terms() -> None:
    """Criterion 10: Pattern, Proposal, and Audit-wide row after Phase score."""
    lines = (ROOT / "GLOSSARY.md").read_text(encoding="utf-8").splitlines()
    for line in PROPOSAL_GLOSSARY_ROWS:
        assert line in lines, line
    phase = next(
        i for i, line in enumerate(lines) if line.startswith("| Phase score |")
    )
    assert lines[phase + 1] == PROPOSAL_GLOSSARY_ROWS[2]
