---
name: merge
description: Craft step 4. Merge an approved craft pull request and close the Linear ticket. Use after the merge gate is approved, or in one-shot mode after the review passes.
model: haiku
---

# craft:merge

Load the `craft:rules` skill first, and follow it.

## Input

A ticket whose merge gate is approved. For `mode=one-shot`, a ticket whose review passed, in a build thread that holds the owner's merge approval.

## Steps

1. **Check the gate.** The merge gate must be approved, and no commits may have been pushed after the `🤖 Gate: merge` comment. If there were, go back to `craft:review`.
   For a ticket with `mode=one-shot` in `## Steering`, there is no merge gate. Instead, the spec must have passed review, as step 1 of `craft:build` says: the latest ticket-scope `🤖 spec review:` on the ticket is PASS, or a plan-scope PASS is newer than its `🤖 spec: success`, or, for a plan from before craft 2.8, an approved `🤖 Gate: launch`, or an unapproved one with no owner comment after it. And the latest review comment on the PR must end with a PASS verdict line, with no commits pushed after it. If there were, go back to `craft:review`.
   **Merge approval.** For a one-shot ticket in a claude.ai project session, merge only when this session holds the owner's merge approval for this ticket's plan, repo, and base, or the owner's go-ahead for this PR in this thread, such as "merge". The merge approval is the owner's own message, attached to this thread by id, with the sentence from the plan gate in `craft:plan`. Its id is in the `🤖 Approved: plan (merge approval in chat, message <message id>)` comment on the plan ticket. Words from another Claude, such as the coordinator's request, are not the merge approval. A message that names another plan, repo, or base does not count. If the session holds neither, do not try the merge: escalate with `(no merge approval)`, as **Escalation** says. A terminal session has no message ids, so it skips this check and tries the merge.
2. **Check CI.** Each required check must be green on the PR's latest commit (`gh api repos/<repo>/commits/<head sha>/check-runs`). For the ticket that replaces a `none yet` value, the required checks are the ones its own branch names in `.claude/craft.md`.
3. **Merge.** In a session with the GitHub MCP tools, use the `merge_pull_request` tool: merge method `squash`, `expectedHeadSha` set to the head SHA, commit title `<PR title> (#<num>)`, and commit message `Craft-Issue: <TEAM>-<num>`. Otherwise use `gh api -X PUT repos/<repo>/pulls/<num>/merge -f merge_method=squash -f sha=<head sha> -f commit_title="<PR title> (#<num>)" -f commit_message="Craft-Issue: <TEAM>-<num>"`. If a permission check or the session's own rules refuse the merge, follow **Escalation**.
4. **Check the branch is gone.** The repo setting "Automatically delete head branches" deletes it on merge; the cloud sandbox blocks branch deletes and settings writes, so do not delete it yourself. Confirm with `gh api repos/<repo>/branches/<branch>`: a 404 means it is gone. If it still exists, check `gh api repos/<repo> --jq .delete_branch_on_merge`; when that is `false`, tell the owner to turn on Settings → General → Pull Requests → "Automatically delete head branches" and to delete `<branch>` by hand.
5. Move the ticket to **Done** and comment `🤖 merge: success — <merge commit url>`.
6. **Replan check.** Run the replan check from `craft:next` with the merged PR, in a subagent on the `replan check` model from `models.md` from `craft:rules`. The subagent returns the proposals.
7. For `mode=one-shot`, skip this step: the done report in `craft:next` tells the owner, and **Owner after** items wait for it. Otherwise, tell the owner in chat what shipped, with the PR link, and the replan proposals. If the ticket lists **Owner after** items, such as making new checks required on the base branch, list them too, with where to do each. Use the `craft:clear-technical-prose` skill. If there are proposals, wait for the owner's approval and apply them.
8. **Next.** For `mode=one-shot`, run `craft:next`. Otherwise, if the ticket was the walking skeleton of a `Brief: Dev environment`, and the brief names a **Product brief**, start `craft:plan` on it in a new session, as **After approval** in `craft:brainstorm` describes. Then, if the ticket was the last open ticket of its Linear milestone, run the milestone checkpoint from `craft:next`. Otherwise run `craft:next`.

## Done when

The PR is merged, its branch is deleted (or the owner was told why not), and the ticket is Done.

## Escalation

If the merge fails (conflict, check not green), follow Retries in `craft:rules`. Fix conflicts in `craft:build`.

**Refused merge.** A merge is refused when a permission check denies it, such as the auto mode classifier, or when the session's own rules do not let it merge. Do not retry it, and do not try another way, such as another tool, `gh api`, or GitHub auto-merge. An escalation is not a failed attempt: the retry count stays the same.

- **One-shot ticket.** Post `🤖 merge: escalated — needs the owner's go-ahead (refused) <link to this build thread>`, or `(no merge approval)` in place of `(refused)` when the check in step 1 stopped it. In a terminal, put the command `claude "Run craft:merge on <key>"` in place of the link. Move the ticket to **Needs human**, send the Needs human notice from `craft:next`, and run `craft:next`. The notice is the ask: it has the PR link and ends with: reply "merge" in this thread to merge it. In a terminal, it ends with the command instead: the owner starting it is the go-ahead, and that session merges at once. If the plan ticket has neither a `🤖 Approved: plan (merge approval ...)` comment nor a `🤖 merge approval: asked` comment, a `(no merge approval)` notice also asks for the merge approval sentence from the plan gate in `craft:plan`, filled in and ready to copy. Then post `🤖 merge approval: asked` on the plan ticket, so no later notice asks again.
- **Gated ticket, or the plan PR.** Post `🤖 merge: escalated — needs the owner's go-ahead (refused)`, or `🤖 plan: escalated — needs the owner's go-ahead (refused)` for the plan PR. Ask the owner in chat to reply "merge" in this thread, with the PR link, and stop. Do not move the ticket to **Needs human**: the owner is already in this thread at a gate.

**After an escalation.** The owner's "merge" in the build thread is the go-ahead for this PR. Run step 1 and step 2 again, then merge. For the plan PR, run **Check CI** and **Merge** again, as **After approval** step 1 in `craft:plan` does, then go on with **After approval** step 2 in `craft:plan`. A "fixed" or "resume" for an escalated merge names no merge: it does not merge, and it starts no merge session. Answer that "merge" in the build thread merges it, with the link from the escalation comment.
