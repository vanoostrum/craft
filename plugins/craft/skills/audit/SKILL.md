---
name: audit
description: Craft audit, outside the ticket flow. Judge how well craft's phases did their job on the craft tickets merged since the last audit, against the phase rubrics and the custom rubrics, and write the audit report in Linear. Use when the owner or the weekly scheduled task says "Run craft:audit", optionally with rubric=<name>.
model: opus
---

# craft:audit

Load the `craft:rules` skill first, and follow it where this skill does not say otherwise. Then load `craft:bstack` with the Skill tool, before any pstack skill.

The audit judges the craft process (`docs/adr/0010`). Each rubric asks whether one phase did its job, such as whether the review read the changed files in context. The audit may read code, such as a PR's diff, as evidence of what a phase saw or missed. Every finding points at craft: a phase, skill, step, hook, or rubric to change. The audit never proposes a fix to a project's code, and it never scores the code on its own: it is not a code review.

## Input

No ticket. The owner, or the weekly scheduled task, says "Run craft:audit", optionally with `rubric=<name>`. The session holds the repositories of the projects, the Linear connector, and read access to the bucket `gs://craft-transcripts`.

## Outside the ticket flow

The audit has no ticket, no gate, and no step comment. It makes no branch, commits nothing, and pushes nothing. It writes its scores and findings only into the audit report in Linear (`docs/adr/0009`): never into a repository, a PR, a GitHub comment, or a project file. Its only chat message is the audit message at the end.

**Today** is the date in Europe/Madrid when the audit starts, as `yyyy-mm-dd`. Times in the report are UTC, in ISO 8601.

An **audited ticket** is a craft ticket whose PR merged in the audit window: a PR merged into the project's `Base branch` from its `.claude/craft.md`, whose title starts with `[CRAFT-<n>]`. Other PRs are not audited. Each rubric judges each audited ticket at most once.

Keep the working files of the audit in a scratch directory outside every repository, such as one from `mktemp -d`. `<audit>` below is this skill's directory.

## Rubric file

A rubric is a Markdown file in `<audit>/rubrics/`, a phase rubric, or in `<audit>/rubrics/custom/`, a custom rubric that the owner adds. Its name is the file name without `.md`, such as `review`. A file whose name starts with `_`, such as `rubrics/custom/_example.md`, is a template: the audit skips it. A change to a rubric gets a new rubric version, and the audit compares scores only within one rubric version.

A rubric file has, in this order:

- `# <Name> rubric`, such as `# Review rubric`.
- `Rubric version: <n>`, a whole number.
- `Phase: <phase>`, the craft phase it judges, such as `review`, or `Phase: custom` for a custom rubric.
- Optionally `Applies to: tickets with a spec`. Such a rubric judges only audited tickets whose Linear description has a `## Spec`. It lists the other audited tickets as "not in this phase", and they count in none of its scores. Without the line, the rubric judges every audited ticket.
- `## Items`, with one `### <item name>` heading per item. Each item has the lines `Kind:` (Measure, Check, or Escape), `Reads:` (where its data comes from), and `Score:` (how it is scored).
  - A **Check** also has `Pass:`, `Partial:`, and `Fail:` lines. With the line `Per: craft version`, it is judged once per craft version instead of per ticket.
  - A **Measure** names its script in `Score:`, such as `scripts/rounds.py`, and the values that the script prints.
  - An **Escape** item is "not scored yet": the audit lists it as "not scored yet" in the rubric's section, and `scores.py` prints no row for it.

`python3 <audit>/scripts/rubric.py check <file>` checks that a file follows this format.

## Steps

1. **Rubrics.** With no argument, the audit judges every rubric that `python3 <audit>/scripts/rubric.py names` prints: each file in `rubrics/` and `rubrics/custom/` whose name does not start with `_`. With `rubric=<name>`, it judges only that rubric: `python3 <audit>/scripts/rubric.py find <name>` looks in `rubrics/` first, then in `rubrics/custom/`. An unknown name stops the audit: tell the owner in chat that the rubric is unknown, with the list of rubric names that `find` prints, and write no report. Check each rubric with `rubric.py check`; a rubric that fails stops the audit the same way, with its error.
2. **Previous report.** List the Linear documents of the Craft Linear project whose title is `Audit: <yyyy-mm-dd>`. The previous report is the latest audit report from a day before today. Today's own report is never the previous report: `Audit: <today>`, from an earlier run today, is not read. Read the listed tickets of every audit report from before today, from its `## Tickets` section, or from `## PRs` in a report in the CRAFT-85 format, such as `Audit: 2026-11-23`. The fill-up in step 5 leaves out each ticket that any of them lists. With no report from before today, there is no previous report.
3. **Audit window.** It starts at the end of the previous report's window, from the `Window: <start> to <end>` line in its `## Tickets`, or in its `## PRs` in the CRAFT-85 format. With no previous report, it starts 7 days before the audit starts. It ends when the audit starts.
4. **Projects.** The projects are the Linear projects of the `CRAFT` team. The project name is the Linear project's name, such as `Craft Console`. Match each one to the repository in the session that names it as `Linear project` in its `.claude/craft.md`. The Craft Linear project matches `vanoostrum/craft`. A repository or a bucket folder is not a source of projects: a repository that names no Linear project of the team is not audited.

   A project is readable when it has a matched repository and the session can read it on GitHub (`gh api repos/<owner>/<repo>`). Each project that is not readable gets a "skipped" row in `## Tickets` with its reason: "repo not in the environment" when no repository in the session names this Linear project, or "repo cannot be read" when the matched repository fails on GitHub. A project with a readable repository and no bucket folder, such as LibRag, is still audited: its tickets get "no transcripts". If the bucket cannot be read, go on: every ticket gets "no transcripts", and `## Summary` says that the bucket was not read.
5. **Audited tickets.** For each readable project, read `Base branch` in its `.claude/craft.md` on the default branch. List its closed PRs into that branch with `gh api "repos/<repo>/pulls?state=closed&base=<base>&sort=updated&direction=desc&per_page=100&page=<n>"`, page by page, and keep each PR whose title starts with `[CRAFT-<n>]` and whose `merged_at` is in the audit window. A PR merged in the window was updated in it too, so stop at the first PR whose `updated_at` is before the window start. The ticket is the `CRAFT-<n>` in the title; read its Linear description.

   For each rubric that runs, a ticket is judged unless the rubric has `Applies to: tickets with a spec` and the ticket's description has no `## Spec`, such as a plan ticket like `[CRAFT-89] Plan: …`. Then the rubric lists it as "not in this phase". The limits below count only tickets that at least one rubric that runs judges. A ticket that every rubric lists as "not in this phase" is listed in `## Tickets` and counts toward neither limit.
   - **Fill-up.** When the window holds fewer than 5 tickets to judge, over all projects together, add the latest audited tickets merged before the window that no audit report from before today lists, newest first over all projects, until there are 5 to judge or none are left. For the fill-up, keep paging until there are 5 to judge or no page is left, because an older merged PR can have any `updated_at`.
   - **Cap.** When there are more than 40 tickets to judge, take 40, spread evenly over the projects, newest first: take the newest ticket of each project in turn until 40 are taken. Each ticket left out is listed as "skipped" with the reason "over the cap of 40".
6. **Craft version.** Read the `metadata.json` of each session in the project's bucket folder, `gs://craft-transcripts/<owner>/<repo>/sessions/<id>/metadata.json`. A rubric's segments for a ticket are the segments whose `ticket` is the ticket and whose `step` is the rubric's phase: `review` for the Review rubric. A custom rubric (`Phase: custom`) uses the review segments, as the Review rubric does. Per rubric, the craft version of the ticket is the `craft_version` of the latest of its segments, by `started_at`. With no such segment, take the release tags `v<version>` of `vanoostrum/craft`: the release time of a tag is the committer time of the commit it points to. The craft version is the version with the latest release time before the PR's `merged_at`, and the ticket is marked "no transcripts" for that rubric.
7. **Digests.** The full review is the first review of the PR; follow-up reviews count only in measures. Its transcript is the first subagent, by `started_at`, of the earliest review segment whose `role` contains "review", case-insensitive: `sessions/<id>/subagents/agent-<agent_id>.jsonl.gz`. With no such subagent, it is the segment's own part of the session transcript: `python3 <audit>/scripts/digest.py sessions/<id>/session.jsonl.gz <started_at> <ended_at>` of the segment. Download the transcript to the scratch directory and run `python3 <audit>/scripts/digest.py <transcript>` on it. The digest holds the assistant text, each tool call with its input cut at 500 characters, and each tool result cut at 300 characters. The judge reads the digest, never the raw transcript.

   A ticket with no review segment, such as a LibRag ticket or a session from before craft recorded segments, has no digest. Its checks that read a transcript are "no data", not fail: each check whose `Reads:` line names the transcript digest, also when it reads a PR comment too, such as Design and maintainability. Its checks that read GitHub or Linear, such as Criteria evidence, and its measures are still scored.
8. **Measures.** For each Measure, run the script that its `Score:` line names. For Findings rounds: save the PR's issue comments with `gh api "repos/<repo>/issues/<n>/comments?per_page=100"` to `comments.json`, and run `python3 <audit>/scripts/rounds.py comments.json`. It prints the status and the values: `PASS`, `no PASS` for a PR that merged without a PASS, such as an escalated merge, or `no data` for a PR with no verdict line, such as a review from before craft 2.9.0. Keep its `values` for `audit.json`, and its status for the rubric's section.
9. **Judge.** Start one fresh audit judge per audited ticket and rubric that judges it, one at a time, on the `audit judge` model from `models.md` from `craft:rules`. Give it:
   - the rubric file;
   - the ticket's `## Spec`;
   - the PR title, the PR body, and the list of changed files from `gh api "repos/<repo>/pulls/<n>/files?per_page=100"`;
   - the PR diff, saved to a file with `gh api -H "Accept: application/vnd.github.diff" repos/<repo>/pulls/<n>`, as evidence of what the phase saw or missed;
   - the project's repository at the PR's `merge_commit_sha`, which it may read with `git show <sha>:<path>`, such as a whole changed file or the existing code next to it;
   - the PR's review comments: the issue comments of step 8;
   - the digests of step 7, or the line "no transcripts".

   The prompt says: "You are an audit judge. Judge how craft's process worked on one ticket, against the rubric. You may read the code, such as the diff, as evidence of what the phase saw or missed. Judge the phase, not the code: do not score the code, and never propose a fix to the project's code. When a result points at a problem, name the craft phase, skill, or rule it comes from. Answer each Check without `Per: craft version` as one line `<item> | <pass, partial, fail, or no data> | <evidence>`, with the evidence you cite: a quote, a tool call, or a comment. Answer `no data` when the data the item reads is missing: a check whose `Reads:` line names the transcript digest is `no data` when there is no transcript, even when it also reads a comment." Keep each line whose item is a per-ticket Check of the rubric and whose result is one of the four. A Check without an answer is "no data", and so is a check that reads the transcript digest of a ticket with no digest, whatever the judge answered.
10. **Process logic.** A Check with `Per: craft version` is judged once per rubric and craft version that the audit has a ticket for, not per ticket. For the Review rubric, it is Process logic. When the previous report's `## Scores` has a row for the same rubric, rubric version, craft version, and item, copy its value and do not judge again. With another rubric version, judge again. Otherwise start one more fresh audit judge on the `audit judge` model, with the rubric file and the files that the item's `Reads:` line names, at the release tag `v<version>` of `vanoostrum/craft`, from `git show v<version>:<path>`. A file that does not exist at that tag, such as `hooks/one_step_per_session.py` before `v2.8.1` or `skills/rules/findings.md` before `v2.9.0`, is left out of the judge's input, and the judge judges the files that exist. The judge may read any other file at that tag with `git show v<version>:<path>` as evidence, such as `hooks/hooks.json`, which decides whether a hook runs at all, or the hook tests. It judges only the files that `Reads:` names. When none of the hooks or scripts that the item names exist at that tag, the result is "no data", with no judge. The judge answers `<item> | <pass, partial, fail, or no data> | <evidence>`.
11. **Scores.** Write `audit.json` in the scratch directory: the rubrics that ran, by name; each audited ticket with its project, ticket, PR number, and per rubric either `"not in this phase"` or its craft version, check results, and measure values; and the per craft version results, as the usage text of `scripts/scores.py` shows. Save the previous report's content to `previous.md`. Run `python3 <audit>/scripts/scores.py audit.json previous.md`, or without `previous.md` when there is no previous report. Its output is the `## Scores` section: one row per rubric, rubric version, craft version, and item, with the Phase score (the share of per-ticket checks passed; the Process logic result is shown next to it, not in it), and the value at the last audit from the previous report of the same rubric version, else a dash. A previous report in the CRAFT-85 format gives dashes.
12. **Report.** Write the audit report as the Linear document `Audit: <today>` in the Craft Linear project, with these sections in this order, also when no ticket was judged:
    - `## Summary`: the rubrics that ran, with their rubric versions (with `rubric=<name>`, say that only that rubric ran); the audit window; the counts of "audited", "not in this phase", and "skipped" tickets, and the audited tickets per project; and the phase score of each rubric per craft version. With no ticket judged, say "No tickets judged." If the bucket was not read, say so.
    - `## Scores`: the output of `scores.py`, unchanged.
    - A `## <Rubric name>` section per rubric, such as `## Review`: a `### <repo>#<n> (<ticket>)` heading per ticket it judged, with each check's result and evidence, and each measure's values and status; then the line "Not in this phase:" with the tickets it does not judge; then the Process logic result per craft version, with its evidence or "copied from <previous report>"; then each Escape item with "not scored yet".
    - `## Tickets`: the line `Window: <start> to <end>`, then a table with the columns Repository, PR, Ticket, Craft version, Status, and Note. Status is "audited", "not in this phase", or "skipped". Note holds "no transcripts" where it applies, and the reason of each skip. A skipped project has a row with `—` as PR.

    If `Audit: <today>` exists already, replace its content and keep the document: never create a second one. Then read the document back, and check that its `## Scores` table has the same rows and cells as the output of `scores.py`, apart from Linear's backslash escapes and separator rows.
13. **Message.** Send one chat message to the owner, and a push notification too where the environment has one. It holds the report link; the phase score of each rubric per craft version, each with its trend, such as `0.50 (last audit 0.75)` or `0.50 (last audit —)`; and the counts of "audited", "not in this phase", and "skipped" tickets. When no ticket was judged, say so, and that the report says why. Use the `craft:clear-technical-prose` skill.

## Done when

`Audit: <today>` in the Craft Linear project has its sections, its `## Scores` matches `scores.py`, and the owner has the audit message.
