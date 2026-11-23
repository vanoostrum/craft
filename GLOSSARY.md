# Glossary

| Term | Meaning |
|---|---|
| Released craft | The craft version that the agents run, not the checkout they change. It is the craft on `main`, which holds only releases (`docs/adr/0004`). |
| Release | A `version` bump in `plugins/craft/.claude-plugin/plugin.json` on `dev`, a merge of `dev` into `main`, and a tag on `main`. |
| Smoke suite | The `claude plugin eval` cases in `plugins/craft/evals/`. They load the plugin in a real Claude Code session and check that key steps behave. |
| Smoke case | One case of the smoke suite. |
| Feature map | The table in the skill verify that names, for each smoke case, the craft step or hook it covers. |
| Merge approval | The owner's own chat message at a one-shot plan gate that lets craft merge the plan PR and each ticket PR of that plan into its base branch of its repo once review passes and checks are green. Craft attaches it by message id to each one-shot build thread. |
| Finding | One problem that a review reports. It is blocking or non-blocking. |
| Blocking finding | A finding that makes the review FAIL, such as an unmet acceptance criterion or a contradiction between specs. `rules/findings.md` has the full list. |
| Non-blocking finding | A finding that does not make the review FAIL. The gate lists it, and the owner decides whether to fix it. Not a note: a note is a `note=` argument. |
| Follow-up review | A review after a fix. It checks the earlier blocking findings, the changed text, and every place that states a changed rule. |
| Ripple check | The search a fix step makes for every other place that states the rule it changed. |
| Segment | The part of a session from one craft step call to the next, with its own ticket, tokens, and times. In a spec session, a change of the current ticket also starts a segment. `metadata.json` lists the segments of a session. |
| Incoming message | A message that reaches a session from outside: a `queue-operation` line with `operation` `enqueue`, or a typed prompt. Not a tool result, and not a skill's text. |
| Craft time | The working time of a segment: the gaps between transcript lines, except the gaps that end with an incoming message. `metadata.json` holds it as `work_seconds`. |
| Waiting time | The gaps of a segment that end with an incoming message. `metadata.json` holds it as `wait_seconds`. The Console shows it as "Waiting on you". |
| Craft version | The version of craft that ran a segment, such as `2.9.0`, from the plugin's `plugin.json`. `metadata.json` holds it as `craft_version`. |
| Spec session | A session whose first craft step call is `craft:spec`. |
| Session ticket | The ticket of a spec session as a whole: the ticket key in the arguments of its first `craft:spec` call, else the key in its `one-shot plan <key>` prompt, else the branch's ticket. In a one-shot run that `craft:next` starts, it is the plan ticket. |
| Current ticket | In a spec session, the ticket that was last moved to **Specifying**, until it moves to another state. Otherwise the session ticket. |
| Brief URL | The URL of the `Brief: <name>` document that a brainstorm or setup segment saved. `metadata.json` holds it as `brief`. |
| Re-process | A run of `plugins/craft/hooks/reprocess_transcripts.py`. It rebuilds `metadata.json` of each stored session that lacks the ADR 0005 fields, from the session's transcripts, with the upload hook's code. |
| Release time | The committer time of the commit that a release tag `v<version>` points to. The re-process uses it to find the craft version of a session from before craft recorded it. |
| Audit | A run of `craft:audit`. It judges merged craft PRs against the core rubric, finds what craft's own review missed, traces the cause in the transcripts, and proposes changes to craft. It runs weekly, outside the ticket flow: it has no ticket and no gate. |
| Core rubric | The fixed list of code quality items that every audit uses in the same way: design, complexity, duplication, naming, and tests. It lives in `plugins/craft/skills/audit/rubric.md`. |
| Rubric version | The version line of the core rubric. Each change to the rubric gets a new rubric version. Scores are compared only within one rubric version (`docs/adr/0008`). |
| Blind audit | The phase of an audit that judges each PR against the core rubric. It runs in a blind auditor. |
| Blind auditor | The subagent of the blind audit. It sees only the merged code, the project's own conventions (`CLAUDE.md`, linters), and the core rubric. It does not see the spec, craft's review, or the transcripts (`docs/adr/0008`). |
| Audit finding | One problem that the blind audit reports, on one rubric item, marked major or minor. Not a review finding, which is blocking or non-blocking. |
| Audit score | The count of audit findings per PR, per rubric item, each marked major or minor. Its headline is the number of major audit findings per PR, per project and per craft version. The scores of craft's own PRs are kept apart from those of the app projects. |
| Blind spot | An audit finding that craft's own review of that PR did not report. |
| Miss rate | The share of audit findings that are blind spots, per project. |
| Trace back | The phase of an audit that reads the build and review transcripts of a ticket with a blind spot, and names its cause. |
| Cause | Why craft missed a blind spot: the skill says nothing about it, the agent skipped a rule, the reviewer called it non-blocking, or the build step pushed it there. |
| Conformance | Whether each step of an audited ticket did what its skill says, as the trace back reads it from the transcripts. |
| Deep dive | The part of an audit that looks harder at one theme, after a web search for current practice. The theme is the lens. |
| Lens | The theme of a deep dive, such as `error-handling`. `lens=<theme>` picks it; otherwise the audit picks it. |
| Proposal | A change to a craft skill or step that an audit proposes, with the metric it should move and that metric's current value. It is a ticket in **Backlog** with the label `audit`. It links the audit report, and its ticket and spec may describe the findings behind it, with short examples. Its title names only the craft change. Its PR, branch, and repo files quote only craft's own skill text and summary numbers, and a `note=` on the ticket tells every step so (`docs/adr/0009`). |
| Audit report | The Linear document `Audit: <yyyy-mm-dd>` in the Craft project that an audit writes. Its `## Scores` table is what the next audit reads for the trend. |
| Audit window | The span of merge times an audit covers. It starts at the end of the window of the latest audit report from an earlier day, or 7 days before the first audit, and ends when the audit starts. |
