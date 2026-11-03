---
name: merge
description: Sous step 4. Merge an approved sous pull request and close the Linear ticket. Use after the merge pass is approved.
model: haiku
---

# sous:merge

Load the `sous:rules` skill first, and follow it.

## Input

A ticket whose merge pass is approved.

## Steps

1. **Check the pass.** The merge pass must be approved, and no commits may have been pushed after the `🤖 Pass: merge` comment. If there were, go back to `sous:review`.
2. **Check CI.** Each required check must be green on the PR's latest commit (`gh api repos/<repo>/commits/<head sha>/check-runs`).
3. **Merge**: `gh api -X PUT repos/<repo>/pulls/<num>/merge -f merge_method=squash -f sha=<head sha> -f commit_title="<PR title> (#<num>)" -f commit_message="Factory-Issue: <TEAM>-<num>"`.
4. **Check the branch is gone.** The repo setting "Automatically delete head branches" deletes it on merge; the cloud sandbox blocks branch deletes and settings writes, so do not delete it yourself. Confirm with `gh api repos/<repo>/branches/<branch>`: a 404 means it is gone. If it still exists, check `gh api repos/<repo> --jq .delete_branch_on_merge`; when that is `false`, tell chef to turn on Settings → General → Pull Requests → "Automatically delete head branches" and to delete `<branch>` by hand.
5. Move the ticket to **Done** and comment `🤖 merge: success — <merge commit url>`.
6. **Replan check.** Run the replan check from `sous:next` with the merged PR, in a subagent on the `replan check` model from `models.md` from `sous:rules`. The subagent returns the proposals.
7. Tell chef in chat what shipped, with the PR link, and the replan proposals. Use the `sous:clear-technical-prose` skill. If there are proposals, wait for chef's approval and apply them.
8. **Next.** If the ticket was the last open ticket of its Linear milestone, run the milestone checkpoint from `sous:next`. Otherwise run `sous:next`.

## Done when

The PR is merged, its branch is deleted (or chef was told why not), and the ticket is Done.

## Escalation

If the merge fails (conflict, check not green), follow Refires in `sous:rules`. Fix conflicts in `sous:build`.
