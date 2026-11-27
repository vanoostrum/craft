---
name: build
description: Craft step 2. Implement an approved spec with tests first, verify it, and open a pull request. Use after the spec gate is approved, in a new session, never in the session that ran `craft:spec`, or when CI fails on a craft PR.
model: sonnet
---

# craft:build

Load the `craft:rules` skill first, and follow it. Then load `craft:bstack` with the Skill tool, before any pstack skill.

Then read the engineering rules, as **Engineering rules** in `craft:rules` says.

## Input

A ticket in **Ready to build** whose spec gate is approved. For `mode=one-shot`, a ticket in **Ready to build** whose spec passed the spec review, as step 1 says. `craft:next` starts it from its build-lane prompt. A retry after a review FAIL, red CI, or a merge conflict starts it on a ticket that already has its PR. A retry after a review FAIL, or after owner feedback at the merge gate, runs **Fix** below.

It runs in a new session, never in the session that ran `craft:spec`. A hook denies `craft:build`, `craft:review`, and `craft:merge` there.

## Steps

1. **Check that the ticket is ready.**
   - **Claim.** For `mode=one-shot`, when this step starts from the build-lane prompt of `craft:next`, claim the ticket first: stop if it is not in **Ready to build**, or if another ticket of the plan is in **Building**, gated or not; else move it to **Building** before the other checks. If a later check in this step fails and does not move the ticket itself, move it back to **Ready to build** before you stop, so the plan's build lane does not stall. A retry on a ticket that already has its PR skips the claim.
   - The spec gate must be approved. For `mode=one-shot`, there is no spec gate: the ticket must have a `🤖 spec: success` comment, and the latest ticket-scope `🤖 spec review:` on the ticket is PASS, or a plan-scope `🤖 spec review: PASS` on its plan ticket is newer than its `🤖 spec: success`. For a plan from before craft 2.8, an approved `🤖 Gate: launch` on the plan ticket counts instead, if no ticket of the plan went back to **Todo** after the approval; an unapproved `🤖 Gate: launch` counts too, unless the owner commented after it, because owner feedback there moves its tickets back to **Todo**.
   - Each ticket that blocks it must be **Done**.
   - **Owner first.** If the ticket lists **Owner first** items, such as a secret or a cloud environment setting, check each one you can, for example that the secret is set. For one you cannot check, or that is missing, comment `🤖 build: escalated — owner first: <item>`, tell the owner in chat what to do and where, and stop. For `mode=one-shot`, also move the ticket to **Needs human**, send the Needs human notice from `craft:next`, and run `craft:next`, so the run goes on with other tickets.
   - **Stale spec.** Read the glossary terms, ADRs, and code merged since the `🤖 Gate: spec` comment, or for `mode=one-shot` since the `🤖 spec: success` comment. If they contradict the spec, do not guess. Move the ticket to **Todo**, comment `🤖 build: escalated — stale spec: <what changed>`, and tell the owner. The spec lane grills only the decisions that changed. For `mode=one-shot`, move it to **Needs human** instead of **Todo**, send the Needs human notice from `craft:next`, and run `craft:next`.
   - If a check fails for another reason, stop and say so.
   Then move the ticket to **Building**.
2. **Branch.** Create or check out the branch from the naming rule, based on the latest base branch.
3. **Domain docs.** If the spec has **Domain docs**, write them to `GLOSSARY.md`, `docs/adr/`, and `docs/engineering.md` as the spec says. Commit them with the `Craft-Issue` trailer.
4. **Per task in the plan:**
   1. Write a failing test for it, at the test seam from the spec.
   2. Make it pass with the smallest change.
      For a `ui` ticket, build each screen to match its gallery page in the spec, on each platform in `Platforms` in `design/README.md`: the same structure, states, copy, and look. Write the app's own styles; do not link `design/gallery.css`. Do not change `design/` in this step, except for a polish fix from the merge gate (see The gate in `craft:rules`).
   3. Run the full verify (see the verify skill from the config) in a subagent on the `verify` model from `models.md` from `craft:rules`. Fix until green. A red verify here is part of the work, not a failed attempt. If it is still red after 3 fixes for the same task, count it as a failed attempt.
   4. Commit with the `Craft-Issue` trailer.
5. **Check the acceptance criteria.** Each one must be covered by a test, or explain in the PR why it cannot be. Read the coverage report: a new line or branch under `Missing` needs a test or a reason in the PR.
6. **Prove it in the running app** with the app driver skill from the config. Run it in a subagent on the `app driver` model from `models.md` from `craft:rules`.
   - If the ticket adds or changes an entry point, as the app driver skill defines it, first add or update its file in the skill's feature map.
   - Drive every feature that the ticket adds or changes. Use the recipes in the feature map.
   - Evidence is the output of every entry point that the ticket adds or changes, and a screenshot of every screen.
   - For a `ui` ticket, take the app screenshot and the gallery screenshot of each screen state on each platform in `Platforms` in `design/README.md`. Take the gallery screenshot with `<rules>/scripts/gallery-shot <page> <platform> <evidence dir>`, into the feature's evidence folder. The subagent compares each app screenshot with its gallery screenshot. A visible difference in layout, states, copy, or look is a fail.
   - The subagent returns pass or fail, the transcripts, and the paths of the screenshots.
   - A fail counts as a failed attempt. Fix the code and go back to step 4.
   - Attach each screenshot to the Linear ticket. For a `ui` ticket, attach each app screenshot next to its gallery screenshot.
7. **Open the PR** against the base branch. Write the PR body with the `craft:clear-technical-prose` skill. First look for an existing one: `gh api "repos/<repo>/pulls?head=<owner>:<branch>&state=open"`. If there is one, pushing updates it. Otherwise create it with `gh api repos/<repo>/pulls -f title=... -f head=<branch> -f base=<base> -f body=...`. The PR body has:
   - a one-line summary and the Linear ticket link;
   - a table of acceptance criteria → evidence (test name or file, and the app evidence);
   - an **App evidence** section with the transcripts in fenced blocks, and links to the screenshots on the Linear ticket.
   - for a `ui` ticket, a **Gallery** table: screen state and platform → gallery page → app screenshot and gallery screenshot.
   - the domain docs that the PR adds or changes, if any.
8. **Wait for CI** in a subagent on the `CI polling and log reading` model from `models.md` from `craft:rules`. It polls `gh api repos/<repo>/commits/<head sha>/check-runs` about every 30 seconds until each required check has completed, for at most 30 minutes. A required check that has not completed by then, or has not started, counts as failed. If a check failed, the subagent reads the job log with `gh api repos/<repo>/actions/jobs/<job id>/logs` and returns the error. Fix and push. That counts as a failed attempt.
9. Comment `🤖 build: success — PR <url>` on the ticket. Tell the owner in chat in one line, with the PR link. For `mode=one-shot`, send no chat message.

## Fix

**Fix.** A retry after a review FAIL from `craft:review`, or after owner feedback at the merge gate, a polish fix included, fixes the PR on its branch. Before you change any file, load `craft:build` again with the Skill tool, with the ticket key in the arguments, such as `CRAFT-12`, so the fix runs in its own `build` segment of the transcript. Feedback that changes the design is the exception: it goes back to `craft:design`, as **UI feedback at the merge gate** in `craft:rules` says.

A fix run skips steps 1 to 3: no claim, no ready checks, and no move to **Building**. The ticket keeps its state, so a fix never puts a second ticket in **Building**.

Fix each blocking finding of the review, or each item of the owner's feedback, and follow **Ripple check** in `findings.md` from `craft:rules`. Do not fix a non-blocking finding unless the owner turned it into feedback. Run steps 4 to 8 for what the fix changes, so tests, verify, app evidence, and CI cover it. Then post the fix summary as a PR comment, and load `craft:review` again with the Skill tool, with the ticket key in the arguments: its next review is a follow-up review.

## Done when

The PR is open, each required check is green on its latest commit, every acceptance criterion has evidence, and the PR body has the app evidence.

## Escalation

After 5 failed attempts (app driver, CI, or a review FAIL from `craft:review`), follow Retries in `craft:rules`.

## Next

Load `craft:review` with the Skill tool, with the ticket key in the arguments, such as `CRAFT-12`.
