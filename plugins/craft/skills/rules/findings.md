# Review findings

These rules hold for every fresh review in craft: the build review in `craft:review`, the spec review in `spec-review.md` in ticket scope and in plan scope, and the plan review in `craft:plan`. Every fix step follows **Ripple check** below. The brief checks in `craft:brainstorm` and `craft:setup` do not use these rules.

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

## Follow-up review

Each later review of the same spec, plan, or PR, in the same scope, is a follow-up review. Its inputs are the previous review and the fix summaries since it. It checks:

- each blocking finding of the previous review, and each item of owner feedback in the fix summaries: fixed or not;
- the changed text;
- every place that states a changed rule, name, or value. Search for them yourself, in the spec, the other specs, the skills, the code, the tests, and the docs. The fix summary lists the places that the fix changed, but a place that it missed is what this check is for.

A follow-up review does not review unchanged parts again. A blocking problem that it sees outside that scope still counts.

When a fix summary disputes a blocking finding, with a reason, decide. If you accept the reason, drop it and say why. If not, it stays blocking. Name each earlier blocking finding as fixed, dropped, or still open, so a finding is never silently lost. Add `(follow-up review)` to the verdict line.

After a re-spec from a plan-scope FAIL, the ticket-scope review of that ticket is a follow-up review. Its previous review is the plan-scope review, and the findings it checks are the plan-scope findings on that ticket and any owner feedback. The next plan-scope review is a follow-up review too.

## Ripple check

Every fix step runs it: a fix after a blocking finding, and a fix after owner feedback at a gate. An item of owner feedback counts as a blocking finding here, and in the follow-up review.

1. Fix each blocking finding and each item of owner feedback. Never fix a non-blocking finding on your own. Fix one only when the owner turns it into feedback.
2. For each rule, name, or value that the fix changes, search every place that states it: the spec, the other specs, the skills, the code, the tests, and the docs. Search without case, and for each way the text can say it. Change each place in the same fix.
3. Post a fix summary: each blocking finding and each item of owner feedback, as fixed, or as disputed, with a reason; and every place that the fix changed. A spec fix posts it on the ticket as `🤖 fix: <one line>`, with the list below it. A build fix or a plan fix posts it as a PR comment.

The follow-up reviewer reads the fix summary, but searches the changed rules itself.

## At the gate

A gate lists the non-blocking findings of the latest review under **Non-blocking findings**, and says that the owner can turn any of them into feedback. With no non-blocking findings, write `**Non-blocking findings:** none`, or leave the list out.

In one-shot mode there is no gate. The non-blocking findings stay in the review comment, and the done report in `craft:next` counts them per ticket.
