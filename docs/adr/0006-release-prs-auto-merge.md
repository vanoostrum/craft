# Release PRs use auto-merge

A release spent about 3 of its 8 minutes waiting for GitHub's "checks done" event on the `dev` to `main` PR, after CI was already green (v2.8.1 and v2.8.2). So the release skill turns on GitHub auto-merge on both release PRs: squash on the bump PR, and a merge commit on the `dev` to `main` PR. GitHub merges each one when its required checks pass, which is the approval that ADR 0005 gives. `dev` requires `checks` and `evals`, so auto-merge never merges an unchecked bump.

On the `dev` to `main` PR, the skill waits for the tag in the same turn instead of for a PR event. When GitHub or the session refuses auto-merge, the skill waits for green checks and merges, as before. ADR 0005 approves that merge, so it is not a way around the refusal. When a release stops, the skill turns off auto-merge on its open PRs, so a later push cannot release without a new message from the owner.

A script in the release skill, `.claude/skills/release/scripts/release_prep.py`, does the fixed local steps: the start checks, the bump commit, and the tag wait.

The owner approved this on 2026-11-17.
