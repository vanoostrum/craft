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
| Audit | A run of `craft:audit`. It judges how well each craft phase did its job on the audited tickets, against one rubric per phase and the custom rubrics, and proposes changes to craft. It judges the craft process: it may read code as evidence, but it proposes fixes only to craft, never to the code (`docs/adr/0010`). It runs weekly, outside the ticket flow: it has no ticket and no gate. |
| Audited ticket | A craft ticket whose PR merged in the audit window. Each rubric judges each audited ticket at most once: a rubric that applies only to some tickets, such as tickets with a spec, lists the others as not in this phase. |
| Audit window | The span of merge times an audit covers. It starts at the end of the window of the latest audit report from an earlier day, or 7 days before the first audit, and ends when the audit starts. |
| Rubric | A list of rubric items that the audit judges in the same way each time. A phase rubric judges one craft phase, such as Review or Build. A custom rubric is one the owner adds next to the phase rubrics. Every rubric is a file in the craft plugin. |
| Rubric item | One thing a rubric looks at in its phase. It has a kind (measure, check, or escape), the data it reads, and how it is scored. |
| Rubric version | The version line of a rubric. Each change to a rubric gets a new rubric version. Scores are compared only within one rubric version (`docs/adr/0010`). |
| Rubric file | The Markdown file of one rubric, in `plugins/craft/skills/audit/rubrics/` or in `rubrics/custom/`. It holds the rubric's name, its rubric version, its phase, the tickets it applies to, and its items, each with its kind, the data it reads, and how it is scored. A file whose name starts with _ is a template that the audit skips. |
| Measure | A rubric item that a script scores from metadata, Linear, or GitHub, with no AI judge, such as review rounds per ticket. Reported as a median per craft version. |
| Check | A rubric item that an audit judge answers as pass, partial, or fail, per ticket or once per craft version, with the evidence it cites. Its score is the share that passes. |
| Escape | A problem found after a ticket passed a phase: a fix PR that merged within 14 days after the ticket's PR and changes a file it changed, or the owner's feedback at a gate. An audit judge traces each escape to the one phase that should have caught it. As a rubric item, it shows these escapes per searched ticket, per craft version. |
| Escape trace | The audit judge's answer for one escape: the phase that should have caught it, the other phases that missed it, and why, with evidence. |
| Fix PR candidate | A PR that merged in the audit window, at most 14 days after a ticket's PR, and changes a file that the ticket's PR changed. The audit judge decides whether it fixes a problem of the ticket. |
| Owner choice | Gate feedback in which the owner changes their mind or adds a new wish. No phase should have caught it, so it is not an escape. |
| Audit judge | The fresh subagent that answers the checks and traces the escapes of an audit. |
| Phase score | The share of per-ticket checks passed, per rubric and craft version. The report shows it next to the checks judged once per craft version, the measures, and the escapes. |
| Audit-wide row | A row of `## Scores` with the craft version `all`: the Phase score, a per-ticket check, a measure value, or an escape row, over all tickets of one audit that its rows per craft version count. The Pattern rule compares these rows between audits. |
| Process logic | The craft code that carries a step's rules: the hooks and the skill scripts. The audit judges whether it does what the skill text and the rules say. Craft's own tests and the repo CI are not process logic, but a check may read them as evidence. |
| Environment failure | A verify, app driver, or CI failure that the change did not cause, such as a flaky test, a missing tool, a network block, or a CI runner problem. |
| Test file | A file that a PR changes whose path has a part `tests`, `test`, `e2e`, or `__tests__`, or a part that ends with `Tests`, or whose name matches `test_*`, `*_test.*`, `*.test.*`, or `*.spec.*`. The Build rubric's Tests check behavior item judges the diff of the test files. |
| Pattern | A problem that an audit finds across tickets or audits: a check that fails or is partial on at least 3 audited tickets in one audit; a measure or escape rate whose audit-wide row is worse than at the last audit, two audits in a row; or a Process logic check that fails or is partial at one or more craft versions, which is one pattern per rubric and item. A minor problem counts only as part of a pattern. Only a pattern leads to a proposal. |
| Blind spot | An escape that an audit judge traces to the review phase. The Review rubric counts blind spots in its Blind spots item. |
| Proposal | A change to a craft skill or step that an audit proposes from a pattern, with the measure it should move and that measure's value at the proposal. It is a ticket in **Backlog** with the label `audit`. It links the audit report, and its ticket and spec may describe the evidence behind it, with short examples. Its title names only the craft change. Its PR, branch, and repo files quote only craft's own skill text and summary numbers, and a `note=` on the ticket tells every step so (`docs/adr/0009`). Later audits report how its measure moved after its release. |
| Audit report | The Linear document `Audit: <yyyy-mm-dd>` in the Craft project that an audit writes. Its `## Scores` table is what the next audit reads for the trend. |
| Engineering rules | The written rules that a project's code must follow, in three layers: the shared rules, the stack profiles, and the project rules. The project rules win over the profile, and the profile wins over the shared rules (`docs/adr/0011`). `craft:spec`, `craft:build`, and `craft:review` read all three. |
| Shared rules | The engineering rules for every project: `plugins/craft/skills/rules/engineering.md`. |
| Stack profile | The engineering rules for one stack, such as `python-fastapi`: `plugins/craft/skills/rules/profiles/<stack>.md`. It names the structure, the naming, the libraries, the error handling, and the metric tools with their thresholds. |
| Project rules | A project's own engineering rules: `docs/engineering.md` in its repo. Each rule links the ADR, the `CLAUDE.md` line, or the code behind it. |
| Stacks | The key in `.claude/craft.md` that names the stack profile of each path of the repo, such as `` `/` → `python-fastapi` ``, or `none`. |
| Functional part | The part of a build review that checks the PR against its spec. |
| Technical part | The part of a build review that checks the code against the engineering rules and the metric report. |
| Finding label | The kind of a build review finding, next to its severity: `spec`, `rule`, `lens`, or `lesson` (`docs/adr/0012`). The spec review and the plan review have no labels. |
| Lesson | A rule candidate from a blocking technical finding or from technical owner feedback at the merge gate, marked `project` or `stack`. A `lens` finding turned into feedback counts only the second time for the same kind of problem. The owner approves its wording at the merge gate. A stack lesson also becomes a Backlog ticket with the label `profile` in the Craft project, or adds its PR as evidence to an open `profile` ticket with the same rule. |
| Metric report | The report that a project's verify skill and CI print for a PR: complexity, CRAP, duplication, and file length of what the PR touches, at the base and at the head. It adds no required check. |
| Codebase review | A run of `craft:review scope=codebase`. It runs the technical part over the whole repo, module by module, writes the Linear document `Codebase review: <date>`, and files its findings as Backlog tickets with the label `cleanup`. |
