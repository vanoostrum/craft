---
name: review
description: Sous step 3. Review a sous pull request against its spec in a fresh agent, then stop at the merge pass. Use when a sous PR has green CI.
model: opus
---

# sous:review

Load the `sous:rules` skill first, and follow it. Then load `sous:bstack` with the Skill tool, before any pstack skill.

## Input

A ticket with an open PR and green required checks.

## Steps

1. Move the ticket to **In Review**.
2. **Review in a fresh agent.** Start a subagent on the `fresh reviewer` model from `models.md` from `sous:rules`, so the review is not biased by having written the code. Give it only the ticket key and PR number, and this task:

   > Load the `sous:bstack` skill first. Read the `## Spec` of the Linear ticket and the PR diff. For each acceptance criterion, answer met / not met, with evidence (test name, file and line). Check that the PR's **App evidence** covers every entry point that the PR adds or changes, and that its output matches the criteria. Look at the screenshots on the Linear ticket. Missing or wrong app evidence is a real problem. If the ticket has the `ui` label, compare each app screenshot with the gallery screenshot of the same state and platform. A platform from `Platforms` in `design/README.md` without screenshots is a real problem. A difference is a real problem, unless the PR also changes that gallery page and says why. A change to `design/` that is not a polish fix asked at the merge pass is a real problem. Check that the tests follow the test seam rule in `CLAUDE.md`: a test below the seam that only repeats a test at the seam is a real problem. Then list real problems only: bugs, missing tests, security issues, changes outside the scope. No style nitpicks; ruff and ty handle those. Write the review with the `sous:clear-technical-prose` skill. End with PASS or FAIL.

3. **Post the review** as a PR comment. Do not repeat it in chat.
4. **If FAIL:** go back to `sous:build` with the review as input. That counts as a failed attempt for review.
5. **If PASS:** post `🤖 Pass: merge` on the ticket with the PR link and the criteria table. In chat, ask for approval, by 👍 on the message or a reply "approve", with the PR link and the review link. Stop.

## Done when

The PR has a review comment ending in PASS and the ticket has a `🤖 Pass: merge` comment.

## Escalation

After 3 FAILs, follow Refires in `sous:rules`.

## Next

After approval, continue with `sous:merge`.
