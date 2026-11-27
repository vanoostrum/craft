---
name: review
description: Craft step 3. Review a craft pull request against its spec in a fresh agent, then stop at the merge gate. Use when a craft PR has green CI.
model: opus
---

# craft:review

Load the `craft:rules` skill first, and follow it. Then load `craft:bstack` with the Skill tool, before any pstack skill.

## Input

A ticket with an open PR and green required checks.

## Steps

1. Move the ticket to **In Review**.
2. **Review in a fresh agent.** Start a subagent on the `fresh reviewer` model from `models.md` from `craft:rules`, so the review is not biased by having written the code. Give it only the ticket key and PR number, the absolute path of each engineering rule file that applies, and this task. The rule files are `<rules>/engineering.md`, each profile that `Stacks` names, and `docs/engineering.md` in the PR branch checkout, as **Engineering rules** in `craft:rules` says. Write `<rules>` out as the base directory of `craft:rules`, because the subagent does not know it. Leave out a missing file, and name each skip in the gate comment. The first review of the PR is a full review. For a follow-up review, also give it the previous review and the fix summaries since it: the latest review comment on the PR, and the fix summary comments after it.

   > Load the `craft:bstack` skill first. Follow `findings.md` from `craft:rules`: a full review, or a follow-up review if you got the previous review. Read the `## Spec` of the Linear ticket and the PR diff. Then open each changed file of the PR in full on the PR branch, test files too: do not rely on the diff alone. In a follow-up review, open in full each file that the fix changed since the previous review. Also open in full the file that holds each test that you cite as evidence for a criterion or a Review focus line, also when the PR did not change that file. You may skip a deleted file, a binary file, a lock file, and a generated file. For each acceptance criterion, answer met / not met, with evidence (test name, file and line). An unmet criterion is a blocking finding. Check that the PR's **App evidence** covers every entry point that the PR adds or changes, and that its output matches the criteria. Look at the screenshots on the Linear ticket. Missing or wrong app evidence is a blocking finding. If the ticket has the `ui` label, compare each app screenshot with the gallery screenshot of the same state and platform. A platform from `Platforms` in `design/README.md` without screenshots is a blocking finding. A difference is a blocking finding, unless the PR also changes that gallery page and says why. A change to `design/` that is not a polish fix asked at the merge gate is a blocking finding. Read in full each engineering rule file whose path you got, and list it under **Files read**. A change that breaks a rule is a blocking finding that names the file and the rule's bold name. If the spec has `(exception: <rule name>)` under **Decisions** for that rule, its break is not a blocking finding. A project rule wins over a profile rule, and a profile rule wins over a shared rule. For each line under **Review focus** in the spec, answer covered / not covered, with the test that covers it. A line without a test is a blocking finding. Check that the tests follow the test seam rule in `CLAUDE.md`: a test below the seam that only repeats a test at the seam is a non-blocking finding. Report every finding at once, blocking or non-blocking, as `findings.md` says: bugs, missing tests, security issues, and changes outside the scope are blocking. No style nitpicks; ruff and ty handle those. Write the review with the `craft:clear-technical-prose` skill. Before the verdict line, add a **Files read** list: in a full review, each changed file of the PR; in a follow-up review, each file that the fix changed since the previous review. Mark each file as read in full or skipped, with the reason for each skip. In the list, also name each file that holds a cited test and that the PR did not change, and each engineering rule file. End with the verdict line, with the counts, such as `PASS — 0 blocking, 2 non-blocking`.

3. **Post the review** as a PR comment. Do not repeat it in chat.
4. **If FAIL:** before you change any file, load `craft:build` again with the Skill tool, with the ticket key in the arguments, such as `CRAFT-12`. The review is its input, and the fix follows **Fix** in `craft:build`. The fix then runs in its own `build` segment of the transcript, so the audit's Build rubric sees it. That counts as a failed attempt in the count that `craft:build` and `craft:review` share (see Retries in `craft:rules`).
5. **If PASS:** post `🤖 Gate: merge` on the ticket with the PR link, the criteria table, and the review's **Non-blocking findings**, as **At the gate** in `findings.md` says: the owner can turn any of them into feedback. In chat, ask for approval, by 👍 on the message or a reply "approve", with the PR link and the review link. Stop.
   For a ticket with `mode=one-shot` in `## Steering`, there is no merge gate. Comment `🤖 review: success — PASS — 0 blocking, <m> non-blocking, merging (one-shot)` on the ticket with the PR link and the criteria table, and continue with `craft:merge` at once. Send no chat message.

## Done when

The PR has a review comment that ends with a PASS verdict line, and the ticket has a `🤖 Gate: merge` comment, or, for `mode=one-shot`, a `🤖 review: success` comment.

## Escalation

After 5 failed attempts in the shared count, follow Retries in `craft:rules`.

## Next

After approval, continue with `craft:merge`.
