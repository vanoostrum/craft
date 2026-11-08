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
2. **Check CI.** Each required check must be green on the PR's latest commit (`gh api repos/<repo>/commits/<head sha>/check-runs`).
3. **Merge**: `gh api -X PUT repos/<repo>/pulls/<num>/merge -f merge_method=squash -f sha=<head sha> -f commit_title="<PR title> (#<num>)" -f commit_message="Craft-Issue: <TEAM>-<num>"`.
4. **Check the branch is gone.** The repo setting "Automatically delete head branches" deletes it on merge; the cloud sandbox blocks branch deletes and settings writes, so do not delete it yourself. Confirm with `gh api repos/<repo>/branches/<branch>`: a 404 means it is gone. If it still exists, check `gh api repos/<repo> --jq .delete_branch_on_merge`; when that is `false`, tell the owner to turn on Settings → General → Pull Requests → "Automatically delete head branches" and to delete `<branch>` by hand.
5. Move the ticket to **Done** and comment `🤖 merge: success — <merge commit url>`.
6. **Replan check.** Run the replan check from `craft:next` with the merged PR, in a subagent on the `replan check` model from `models.md` from `craft:rules`. The subagent returns the proposals.
7. Tell the owner in chat what shipped, with the PR link, and the replan proposals. Use the `craft:clear-technical-prose` skill. If there are proposals, wait for the owner's approval and apply them.
8. **Next.** If the ticket was the last open ticket of its Linear milestone, run the milestone checkpoint from `craft:next`. Otherwise run `craft:next`.

## Done when

The PR is merged, its branch is deleted (or the owner was told why not), and the ticket is Done.

## Escalation

If the merge fails (conflict, check not green), follow Retries in `craft:rules`. Fix conflicts in `craft:build`.
