---
name: merge
description: Craft step 4. Merge an approved craft pull request and close the Linear ticket. Use after the merge gate is approved.
model: haiku
---

# craft:merge

Load the `craft:rules` skill first, and follow it.

## Input

A ticket whose merge gate is approved.

## Steps

1. **Check the gate.** The merge gate must be approved, and no commits may have been pushed after the `🤖 Gate: merge` comment. If there were, go back to `craft:review`.
   For a ticket with `mode=one-shot` in `## Steering`, there is no merge gate. Instead, the plan ticket's `🤖 Gate: launch` must be approved, and the latest review comment on the PR must end in PASS, with no commits pushed after it. If there were, go back to `craft:review`.
2. **Check CI.** Each required check must be green on the PR's latest commit (`gh api repos/<repo>/commits/<head sha>/check-runs`). For the ticket that replaces a `none yet` value, the required checks are the ones its own branch names in `.claude/craft.md`.
3. **Merge**: `gh api -X PUT repos/<repo>/pulls/<num>/merge -f merge_method=squash -f sha=<head sha> -f commit_title="<PR title> (#<num>)" -f commit_message="Craft-Issue: <TEAM>-<num>"`.
4. **Check the branch is gone.** The repo setting "Automatically delete head branches" deletes it on merge; the cloud sandbox blocks branch deletes and settings writes, so do not delete it yourself. Confirm with `gh api repos/<repo>/branches/<branch>`: a 404 means it is gone. If it still exists, check `gh api repos/<repo> --jq .delete_branch_on_merge`; when that is `false`, tell the owner to turn on Settings → General → Pull Requests → "Automatically delete head branches" and to delete `<branch>` by hand.
5. Move the ticket to **Done** and comment `🤖 merge: success — <merge commit url>`.
6. **Replan check.** Run the replan check from `craft:next` with the merged PR, in a subagent on the `replan check` model from `models.md` from `craft:rules`. The subagent returns the proposals.
7. For `mode=one-shot`, skip this step: the done report in `craft:next` tells the owner, and **Owner after** items wait for it. Otherwise, tell the owner in chat what shipped, with the PR link, and the replan proposals. If the ticket lists **Owner after** items, such as making new checks required on the base branch, list them too, with where to do each. Use the `craft:clear-technical-prose` skill. If there are proposals, wait for the owner's approval and apply them.
8. **Next.** For `mode=one-shot`, run `craft:next`. Otherwise, if the ticket was the walking skeleton of a `Brief: Dev environment`, and the brief names a **Product brief**, start `craft:plan` on it in a new session, as **After approval** in `craft:brainstorm` describes. Then, if the ticket was the last open ticket of its Linear milestone, run the milestone checkpoint from `craft:next`. Otherwise run `craft:next`.

## Done when

The PR is merged, its branch is deleted (or the owner was told why not), and the ticket is Done.

## Escalation

If the merge fails (conflict, check not green), follow Retries in `craft:rules`. Fix conflicts in `craft:build`.
