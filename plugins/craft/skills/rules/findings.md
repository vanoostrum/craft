# Review findings

These rules hold for every fresh review in craft: the build review in `craft:review`, the spec review in `spec-review.md` in ticket scope and in plan scope, and the plan review in `craft:plan`. Every fix step follows **Ripple check** below. **Build review** below holds for the build review only. The brief checks in `craft:brainstorm` and `craft:setup` do not use these rules.

A finding is one problem that a review reports. It is blocking or non-blocking.

## Full review

The first review of a spec, a plan, or a PR is a full review.

- Make one complete pass. Check each acceptance criterion, each line under **Review focus**, each row of the **Paths** table, and each changed file or spec section. Do not stop at the first problem.
- Report all findings at once, in one review. A problem that you see now and hold back costs the ticket a round.
- List what you checked: each criterion, each Review focus line, and each Paths row, and for a PR each changed file, with the result of each one. For a PR in `craft:review`, list each changed file with whether you read it in full. The owner and the follow-up reviewer then see that the pass was complete.

## Blocking and non-blocking findings

**Blocking**
- an acceptance criterion that is not met or cannot be tested;
- a line under **Review focus** without a test;
- a bug that a user or a later step hits on a normal path;
- a contradiction between two specs, or between two places in the text;
- a name that a later ticket consumes that is missing or different;
- a security issue;
- a change outside the scope;
- in the build review only, a broken engineering rule, unless the spec has an exception for it: a `rule` finding;
- in the build review only, a new duplicate of existing code: a `rule` finding;
- missing or wrong app evidence;
- for a `ui` ticket, a platform without screenshots, or a difference from the gallery;
- a change to `design/` that is not a polish fix asked at the merge gate.

**Non-blocking**
- a rare edge case that no criterion and no Review focus line names;
- wording;
- a clearer structure;
- a test that could be stronger.

When in doubt, a finding is blocking. Say why.

## Verdict

A review is FAIL only when it has at least one blocking finding. A review with only non-blocking findings, or with no findings at all, is PASS.

List the blocking findings under **Blocking**, then the non-blocking findings under **Non-blocking**, numbered across both lists. For each finding, name the ticket, the file, or the spec lines it concerns. The review ends with the verdict line, which names the counts, such as `PASS — 0 blocking, 2 non-blocking` or `FAIL — 1 blocking, 3 non-blocking`. A step that posts the review as a `🤖 spec review:` comment also puts the verdict line in that comment's first line.

## Build review

The build review in `craft:review` has two parts: a **Functional part** and a **Technical part**. Each finding of the build review has exactly one label. The spec review and the plan review have no parts and no labels: their findings follow the lists above, and a broken engineering rule is no finding there.

- The **Functional part** checks the PR against its spec: the criteria, **Review focus**, the **Paths** rows, app evidence, the gallery, scope, and bugs. Its findings have the label `spec`.
- The **Technical part** checks the code against the engineering rules: the rule files, the exceptions in the spec, the search for duplicates, and the structure and fit of the change. Its findings have the label `rule`, `lens`, or `lesson`.

### Labels

| Label | What | Severity |
|---|---|---|
| `spec` | A finding against the spec. | Blocking or non-blocking, by the lists in **Blocking and non-blocking findings**. |
| `rule` | A broken written rule, or a new duplicate. | Always blocking. |
| `lens` | A judgement call on the structure and fit of the change. | Always non-blocking. |
| `lesson` | A rule candidate, next to a blocking `rule` finding. | Always non-blocking. |

A finding that fits two labels takes the first of `rule`, `spec`, `lens`: it is one finding, not two. A `lesson` is always a finding of its own, never the label of a merged finding.

- **`rule`.** A `rule` finding names its rule by file and bold name, such as `engineering.md` **Reuse before you write**, or `docs/engineering.md` **<name>**. A break of a rule that the spec allows with `(exception: <rule name>)` under **Decisions** is no finding, and the Technical part names each exception that it applied. A security issue is a `rule` finding when a written rule names it, such as **No secrets in the code**, and a blocking `spec` finding otherwise. A test that breaks the test seam rule is a `rule` finding. It cites the `## In CLAUDE.md` bullet of `docs/engineering.md` by its bold name when that file exists, and otherwise `CLAUDE.md` and the bold name of the line that holds the rule, such as `CLAUDE.md` **Test seams**.
- **New duplicate.** New code in the PR that does the same job as code already in the repo, or as other new code in the same PR. A copy of code already in the repo is a `rule` finding against **Reuse before you write**. A copy of other new code in the same PR is a `rule` finding against **Clean up what you touch**. Each names both places, with file and line. Code with a similar shape that does a different job is at most a `lens` finding.
- **`lens`.** A `lens` finding names one smell from Fowler's catalogue, or one principle from a work that `engineering.md` names, such as Shotgun Surgery or Ousterhout's deep modules. A finding without such a name is not reported. No style nitpicks: the linters handle style.
- **`lesson`.** A rule candidate. Write one next to a blocking `rule` finding only when a more specific rule for this project or stack would have stopped the problem, and at most one per blocking finding. Mark it `project` or `stack`, give the proposed rule as a bold name and one sentence, and name the finding it comes from by its number. A `lesson` is not a problem in the PR: the build never fixes it, it does not change the verdict, and the owner decides on it at the merge gate. It is the one non-blocking finding that can become a rule.

### Layout

1. `### Functional part`: the criteria table, each **Review focus** line, each **Paths** row, the app evidence, the gallery, the scope, and bugs.
2. `### Technical part`: the rule files read, the exceptions of the spec that it applied, the duplicate search, and the structure and fit. With no technical findings, it says `No technical findings`.
3. **Blocking**, then **Non-blocking**: one list each for the whole review, numbered across both lists.
4. In a follow-up review, **Gone**: one line for each `gone` finding, with its label, its number and a link to the review that holds it, and the reason. A `gone` finding gets no number in the new review.
5. **Files read**.
6. The verdict line, in the form that **Verdict** gives, such as `FAIL — 2 blocking, 3 non-blocking`.

Each finding is one line: its number, its label in backticks, what and where, then why, such as `` 3. `rule` — `engineering.md` **Reuse before you write**: `src/a.py:12` copies `src/b.py:40` — <why> ``. A `lesson` adds `(project)` or `(stack)` after its label, such as `` 4. `lesson` (project) — **<name>**: <one sentence> — from 3 ``.

## Follow-up review

Each later review of the same spec, plan, or PR, in the same scope, is a follow-up review. Its inputs are the previous review and the fix summaries since it. It checks:

- each blocking finding of the previous review, and each item of owner feedback in the fix summaries: fixed or not. Accept `noted` for an item on a `lesson`;
- the changed text;
- every place that states a changed rule, name, or value. Search for them yourself, in the spec, the other specs, the skills, the code, the tests, and the docs. The fix summary lists the places that the fix changed, but a place that it missed is what this check is for.

A follow-up review does not review unchanged parts again. A blocking problem that it sees outside that scope still counts.

When a fix summary disputes a blocking finding, with a reason, decide. If you accept the reason, drop it and say why. If not, it stays blocking. Name each earlier blocking finding as fixed, dropped, or still open, so a finding is never silently lost. Add `(follow-up review)` to the verdict line.

In a build review, each earlier blocking finding keeps its label when you name it fixed, dropped, or still open, and a new finding gets a label. A build follow-up review also copies each earlier `lens` and `lesson` finding forward with its label, as still open, so the latest review holds all of them for the merge gate and the done report. When the fix removed or changed the code that a copied `lens` finding is about, so that it no longer applies, mark it `gone`, with a reason, in the **Gone** list. A copied `lesson` is never `gone`: it stays open until the merge gate, also after its source finding is fixed, and keeps its source as the number and a link to the review that holds it. A `gone` finding is not counted in the verdict line, and the merge gate and the done report leave it out.

After a re-spec from a plan-scope FAIL, the ticket-scope review of that ticket is a follow-up review. Its previous review is the plan-scope review, and the findings it checks are the plan-scope findings on that ticket and any owner feedback. The next plan-scope review is a follow-up review too.

## Ripple check

Every fix step runs it: a fix after a blocking finding, and a fix after owner feedback at a gate. An item of owner feedback counts as a blocking finding here, and in the follow-up review, except feedback on a `lesson`, which steps 1 and 3 note.

1. Fix each blocking finding and each item of owner feedback. Never fix a non-blocking finding on your own. Fix one only when the owner turns it into feedback. Owner feedback on a `lesson` changes no file: a `lesson` is not code to fix.
2. For each rule, name, or value that the fix changes, search every place that states it: the spec, the other specs, the skills, the code, the tests, and the docs. Search without case, and for each way the text can say it. Change each place in the same fix.
3. Post a fix summary: each blocking finding and each item of owner feedback, as fixed, or as disputed, with a reason, and each item on a `lesson` as `noted`; and every place that the fix changed. A spec fix posts it on the ticket as `🤖 fix: <one line>`, with the list below it. A build fix or a plan fix posts it as a PR comment.

The follow-up reviewer reads the fix summary, but searches the changed rules itself.

## At the gate

A plan gate or a spec gate lists the non-blocking findings of the latest review under **Non-blocking findings**, and says that the owner can turn any of them into feedback. With no non-blocking findings, write `**Non-blocking findings:** none`, or leave the list out.

At the merge gate, the non-blocking findings of the build review go into three lists: **Lens findings**, then **Non-blocking findings** for the `spec` findings, then **Lessons**. The owner can turn any lens or non-blocking finding into feedback, which the build fixes. A `lesson` is not code to fix: the gate shows it for the owner's information, and owner feedback on it changes no file. A list with no findings says `**Lens findings:** none`, `**Non-blocking findings:** none`, or `**Lessons:** none`, or is left out.

In one-shot mode there is no gate. The non-blocking findings stay in the review comment, and the done report in `craft:next` counts them per ticket and lists each `lens` finding.
