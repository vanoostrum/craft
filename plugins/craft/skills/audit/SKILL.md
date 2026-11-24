---
name: audit
description: Craft audit, outside the ticket flow. Score the craft PRs merged since the last audit in a blind audit against the core rubric, and write the audit report in Linear. Use when the owner or the weekly scheduled task says "Run craft:audit".
model: opus
---

# craft:audit

Load the `craft:rules` skill first, and follow it where this skill does not say otherwise. Then load `craft:bstack` with the Skill tool, before any pstack skill.

## Input

No ticket. The owner, or the weekly scheduled task, says "Run craft:audit". The session holds the repositories of the projects, the Linear connector, and read access to the bucket `gs://craft-transcripts`.

## Outside the ticket flow

The audit has no ticket, no gate, and no step comment. It makes no branch, commits nothing, and pushes nothing. It writes its scores and findings only into the audit report in Linear (`docs/adr/0009`): never into a repository, a PR, a GitHub comment, or a project file. Its only chat message is the audit message at the end.

**Today** is the date in Europe/Madrid when the audit starts, as `yyyy-mm-dd`. Times in the report are UTC, in ISO 8601.

A **craft PR** is a PR merged into the project's base branch, the `Base branch` in its `.claude/craft.md`, whose title starts with `[CRAFT-<n>]`. Other PRs are not audited.

Keep the working files of the audit in a scratch directory outside every repository, such as one from `mktemp -d`.

## Steps

1. **Previous report.** List the Linear documents of the Craft Linear project whose title is `Audit: <yyyy-mm-dd>`. The previous report is the latest audit report from a day before today. Today's own report is never the previous report: `Audit: <today>`, from an earlier run today, is not read. Read the `## PRs` section of every audit report from before today: the fill-up in step 4 leaves out each PR they list. With no report from before today, there is no previous report.
2. **Audit window.** It starts at the end of the previous report's window, from the `Window: <start> to <end>` line in its `## PRs`. With no previous report, it starts 7 days before the audit starts. It ends when the audit starts.
3. **Projects.** The projects are the Linear projects of the `CRAFT` team. The project name is the Linear project's name, such as `Craft Console`. Match each one to the repository in the session that names it as `Linear project` in its `.claude/craft.md`. The Craft Linear project matches `vanoostrum/craft`. A repository or a bucket folder is not a source of projects: a repository that names no Linear project of the team is not audited.

   A project is readable when it has a matched repository and the session can read it on GitHub (`gh api repos/<owner>/<repo>`) and fetch it with git. Each project that is not readable gets a "skipped" row in `## PRs` with its reason: "repo not in the environment" when no repository in the session names this Linear project, or "repo cannot be read" when the matched repository fails on GitHub or git. A project with a readable repository and no bucket folder, such as LibRag, is still audited: its PRs get "no transcripts". If the bucket cannot be read, go on: every PR gets "no transcripts", and `## Summary` says that the bucket was not read.

   The group of `vanoostrum/craft` is **Craft**. The group of every other project is **Apps**.
4. **Craft PRs.** For each readable project, read `Base branch` in its `.claude/craft.md` on the default branch. List its closed PRs into that branch with `gh api "repos/<repo>/pulls?state=closed&base=<base>&sort=updated&direction=desc&per_page=100&page=<n>"`, page by page, and keep each craft PR whose `merged_at` is in the audit window. A PR merged in the window was updated in it too, so stop at the first PR whose `updated_at` is before the window start. Sort out the files of each one, as step 5 says.
   - **Fill-up.** When the window holds fewer than 5 craft PRs to judge, over all projects together, add the latest craft PRs merged before the window that no audit report from before today lists, newest first over all projects, until there are 5 to judge or none are left. For the fill-up, keep paging until there are 5 PRs to judge or no page is left, because an older merged PR can have any `updated_at`. A fill-up PR with nothing to judge is listed too, and does not count toward the 5.
   - **Cap.** When there are more than 40 craft PRs to judge, take 40, spread evenly over the projects, newest first: take the newest PR of each project in turn until 40 are taken. Each PR left out is listed as "skipped" with the reason "over the cap of 40". PRs with nothing to judge do not count toward the cap.
5. **Files to judge.** List the PR's files with `gh api "repos/<repo>/pulls/<n>/files?per_page=100"`. A file is judged when the PR adds or changes lines in it, unless it is one of these:
   - Lockfiles, such as `uv.lock`, `pnpm-lock.yaml`, `package-lock.json`, `yarn.lock`, and `Package.resolved`.
   - Generated files: files whose header says they are generated, build output, snapshots, minified files, and generated project files such as `*.xcodeproj`.
   - Markdown docs: every `*.md` file.
   - `design/` gallery pages: every file under `design/`.
   - Binary files, such as images.

   For `vanoostrum/craft`, only files under `plugins/craft/hooks/`, `plugins/craft/skills/*/scripts/`, `tests/`, and `.github/` are judged. Its Markdown skill text is not judged.

   The auditor gets only the files to judge, however large the diff. A PR with no file to judge, such as a plan PR or a PR that changes only skill text, gets no blind auditor and does not count in the scores. `## PRs` lists it as "nothing to judge".
6. **Craft version.** The PR's ticket is the `CRAFT-<n>` in its title. Read the `metadata.json` of each session in the project's bucket folder, `gs://craft-transcripts/<owner>/<repo>/sessions/<id>/metadata.json`. Take the segments whose `step` is `build` and whose `ticket` is the PR's ticket. The craft version of the PR is the `craft_version` of the latest `build` segment, by `started_at`. With no such segment, take the release tags `v<version>` of `vanoostrum/craft`: the release time of a tag is the committer time of the commit it points to. The craft version is the version with the latest release time before the PR's `merged_at`, and the PR is marked "no transcripts".
7. **Blind audit.** Start one fresh subagent per PR to judge, one at a time, on the `blind auditor` model from `models.md` from `craft:rules`. For each PR:
   1. Make a temporary directory with `mktemp -d`. Export the repository's files at the PR's merge commit into `<dir>/repo` with `git archive <merge sha> | tar -x -C <dir>/repo`, from the session's checkout after `git fetch origin <merge sha>`, or from a temporary clone. There is no git history in the directory. Never check out another commit or branch in the session's own checkouts: they stay on their branches.
   2. Write `<dir>/pr.diff`: the diff of only the files to judge, `git diff <merge sha>^1 <merge sha> -- <files to judge>`. Write `<dir>/files.txt`: the files to judge, one per line. Copy this skill's `rubric.md` to `<dir>/rubric.md`. The project's `CLAUDE.md` and its linter and formatter configs are in `<dir>/repo`.
   3. Name nothing in the directory or the prompt after the PR, its title, or its ticket. Give the subagent only this prompt, with the directory path:

      > You are a blind auditor. Judge one change against the core rubric. Your directory is `<dir>`. `<dir>/repo` holds the repository's files after the change, with the project's `CLAUDE.md` and its linter and formatter configs. `<dir>/pr.diff` is the change, and `<dir>/files.txt` lists the files to judge. `<dir>/rubric.md` is the core rubric. Judge only the lines that the change adds or changes, in the files that `files.txt` lists, read in the context of their files and the project's conventions. Use only the files in `<dir>`. Do not use, look for, or ask for the PR title, the PR body, PR comments, commit messages, the ticket, the spec, or any transcripts. Do not use Linear, GitHub, the bucket, git history, or the web. Report each audit finding on its own line, in the finding format of `rubric.md`: `<item> | <major or minor> | <file>:<line> | <one sentence>`. Report every finding you see, each once. If you find nothing, reply `No findings.` Reply with the finding lines only.

   4. Keep each line in the finding format whose item is in the rubric and whose file is in `files.txt`. Drop any other line.
   5. Delete the temporary directory.
8. **Scores.** Write `audit.json` in the scratch directory: the rubric version from `rubric.md`; each audited PR with the Linear project's name as the project, its group, PR number, and craft version; and each finding with its project, PR number, item, severity, file, and sentence, as the usage text of `scripts/scores.py` shows. Save the previous report's content to `previous.md`. Run `python3 <this skill's directory>/scripts/scores.py audit.json previous.md`, or without `previous.md` when there is no previous report. Its output is the `## Scores` section, with the trend from the previous report.
9. **Report.** Write the audit report as the Linear document `Audit: <today>` in the Craft Linear project, with these sections in this order, with no PRs too:
   - `## Summary`: the rubric version, the audit window, the counts of "audited", "nothing to judge", and "skipped" PRs, and the headline per project and craft version: the major audit findings per PR of each version row. Add each group total. With no PRs audited, say "No PRs audited." If the bucket was not read, say so.
   - `## Scores`: the output of `scores.py`, unchanged.
   - `## Findings`: a `### <repo>#<n>` heading per audited PR, with its audit findings as a list in the finding format, or "No findings."
   - `## PRs`: the line `Window: <start> to <end>`, then a table with the columns Repository, PR, Ticket, Craft version, Status, and Note. Status is "audited", "nothing to judge", or "skipped". Note holds "no transcripts" where it applies, and the reason of each skip. A skipped project has a row with `—` as PR.

   If `Audit: <today>` exists already, replace its content and keep the document: never create a second one. Then read the document back, and check that its `## Scores` table has the same rows and cells as the output of `scores.py`, apart from Linear's backslash escapes and separator rows.
10. **Message.** Send one chat message to the owner, and a push notification too where the environment has one. It holds the report link; the major per PR of each project total and each group total, each with its trend, such as `0.50 (last audit 0.75)` or `0.50 (last audit —)`; and the counts of "audited", "nothing to judge", and "skipped" PRs. When no PRs were audited, say that no PRs were audited and that the report says why. Use the `craft:clear-technical-prose` skill.

## Done when

`Audit: <today>` in the Craft Linear project has the four sections, its `## Scores` matches `scores.py`, and the owner has the audit message.
