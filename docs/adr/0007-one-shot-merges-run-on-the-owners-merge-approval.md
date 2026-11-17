# One-shot merges run on the owner's merge approval

In one-shot mode, a build thread merges its PR without the owner. Two checks refuse a merge that only another Claude asked for: the project thread's own rule, and the auto mode block on merging a PR that no human approved. Both clear on the owner's own words that name the merge and its target. A bare "approve" clears neither.

So the one-shot plan gate asks the owner for a merge approval: one sentence that names the plan, the repo, and the base branch. Craft records its message id on the plan ticket, and each one-shot build thread gets the message attached by id. A merge that is still refused escalates to the owner and is never retried or worked around.

We rejected an allow rule in `.claude/settings.json`, because a project thread starts one folder above the repos and does not load it, and it would not clear the thread's own rule. We rejected GitHub auto-merge for these merges, because it schedules the same merge that no human approved.

Probes on 2026-11-17: craft#37 (no approval) was refused, and craft#38 (approval attached) merged.
