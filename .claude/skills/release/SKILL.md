---
name: release
description: Release craft from `dev` to `main` when the owner sends a "release" message, such as "release" or "release 2.7.0". Bumps the version, merges both PRs with GitHub auto-merge, waits for the tag, and writes the release note.
---

# release

The owner's "release" message is the owner's approval for this release: to merge the bump PR into `dev`, and to merge the `dev` to `main` PR into `main`, each when its required checks are green. It also approves turning on GitHub auto-merge on those two PRs, because auto-merge merges only when the required checks pass. It approves nothing else. Do not ask again. Do not merge any other PR. The rules are in `docs/adr/0004`, `docs/adr/0005`, and `docs/adr/0006`, and the README section **Release** has the short form.

Do all GitHub work as the owner, with the GitHub tools of the session. Note the time of the owner's message: the release note gives the release time from it. Tell the owner once that the release has started, with the action it approves: "Release started: I will merge the two release PRs, with auto-merge where GitHub allows it." Put each step on the checklist, and reply again only with the result or a stop.

The script `.claude/skills/release/scripts/release_prep.py` does the fixed local steps with `git` only. Run it with `python3` from the repo root.

## Check the start

1. Run `release_prep.py status`. It fetches `main`, `dev`, and the tags. It exits non-zero when `main` has a hotfix that is not merged back into `dev`, or when there is nothing to release. Then give its message to the owner, and stop.
2. Otherwise it prints the last tag, the version on `dev`, and the PRs since the last tag. When it prints "The bump is done", use the version on `dev` and skip step 1.
3. When a `dev` to `main` PR is already open, use it in step 3 below, and do not open a second one.

## Pick the version

- When the owner names a version, such as "release 2.7.0", use it.
- When the owner says "patch", "minor", or "major", give that part to `release_prep.py bump`.
- Otherwise read the PRs that `release_prep.py status` lists. When every one is a fix, bump the patch. When one adds or changes behavior, bump the minor. Never bump the major unless the owner names it.

## Auto-merge

Turn on auto-merge with the GitHub tool of the session (`enable_pr_auto_merge`), with the merge method of the step. When GitHub or the session refuses to turn it on, use the fallback: wait for green required checks, then merge the PR yourself with the same merge method. `docs/adr/0005` approves that merge, so it is not a way around the refusal. Keep the reason for the reply.

## Steps

1. **Bump.** Run `release_prep.py bump <part or version> <branch>`. It commits `Bump craft to <version>` on the branch from `dev`, and pushes it. Do not run `project-verify`: CI runs the same checks before auto-merge merges. Open the bump PR to `dev`, named `Bump craft to <version>`, and turn on auto-merge with squash.
2. **Wait for `dev`.** Subscribe to PR activity, and end the turn until the merge event of the bump PR or a failed check. Do not poll. On a failed check, stop as **Stop and ask** says.
3. **Merge into `main`.** After the bump PR merged, open the `dev` to `main` PR, named `Release craft <version>`, or use the open one. Its body lists the PRs from `release_prep.py status`. Turn on auto-merge with a merge commit. Never squash or rebase it: `main` and `dev` keep the same history.
4. **Release note.** While CI runs on the `dev` to `main` PR, write `/mnt/project-files/releases/craft-v<version>.md` in the form of the earlier notes there: one paragraph on what the release does, a section per change for the owner, and the release steps with the PR numbers and the tag.
5. **Tag.** In the same turn, run `release_prep.py wait-tag <version>`. Do not end the turn for a PR event. After auto-merge merges, the `release` workflow tags the merge commit `v<version>`. Do not push a tag yourself. When `wait-tag` succeeds, add the release time to the note: from the owner's message to the tag.
   When `wait-tag` fails, read the state and the checks of the `dev` to `main` PR, and stop with one reason:
   - A check failed: name that check.
   - The PR did not merge and no check failed: give the PR link, the state of each check, and say whether auto-merge is still on.
   - The PR merged: give the `release` workflow run link.
6. **Reply.** Give the version, the tag, the two PRs, and the release time, and attach the release note. When the fallback was used, say so and why. Ask the owner to check the craft version in a new thread: this thread cannot see the new version.

## Stop and ask

On every stop, turn off auto-merge on each open release PR (`disable_pr_auto_merge`), and say so in the reply. A later push to `dev` then cannot release without a new "release" message. Tell the owner what happened, and wait. Stop when:

- `release_prep.py status` stops: `main` has a hotfix that is not merged back into `dev`, or there is nothing to release;
- a required check fails, and one fix on the same PR does not make it green;
- a PR has a merge conflict;
- `wait-tag` fails, as step 5 says, or the `release` workflow failed. Give the run link;
- GitHub refuses a merge, for example because a rule wants a review.

Do not retry a refused merge with other flags, and do not push to `main`.
