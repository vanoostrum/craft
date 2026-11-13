---
name: release
description: Release craft from `dev` to `main` when the owner sends a "release" message, such as "release" or "release 2.7.0". Bumps the version, merges both PRs, waits for the tag, writes the release note, and checks the account version.
---

# release

The owner's "release" message is the owner's approval for this release: to merge the bump PR into `dev`, and to merge the `dev` to `main` PR into `main`, each when its required checks are green. It approves nothing else. Do not ask again. Do not merge any other PR. The rules are in `docs/adr/0004` and `docs/adr/0005`, and the README section **Release** has the short form.

Do all GitHub work as the owner, with the GitHub tools of the session. Tell the owner once that the release has started, put each step on the checklist, and reply again only with the result or a stop.

## Check the start

1. Fetch `main` and `dev`. When `main` has a commit that `dev` does not have, stop (a hotfix is not merged back).
2. When `dev` has no commit that `main` does not have, there is nothing to release. Say so, and stop.
3. When a `dev` to `main` PR is already open, use it in step 3 below, and do not open a second one.

## Pick the version

- When the owner names a version, such as "release 2.7.0", use it.
- When the owner says "patch", "minor", or "major", bump that part of the last tag.
- Otherwise read the PRs merged into `dev` since the last tag, `git describe --tags --abbrev=0 origin/main`. When every one is a fix, bump the patch. When one adds or changes behavior, bump the minor. Never bump the major unless the owner names it.
- When `version` in `plugin.json` on `dev` is already above the last tag, the bump is done: use that version and skip step 1.

## Steps

1. **Bump.** On a branch from `dev`, set `version` in `plugins/craft/.claude-plugin/plugin.json`. Run the `project-verify` skill. Open the bump PR to `dev`, named `Bump craft to <version>`. When its required checks are green, merge it with a squash.
2. **Wait for `dev`.** Subscribe to PR activity, and end the turn while checks run. Do not poll.
3. **Merge into `main`.** Open the `dev` to `main` PR, named `Release craft <version>`. Its body lists the PRs since the last tag. When its required checks (`checks`, `evals`) are green, merge it with a merge commit. Never squash or rebase it: `main` and `dev` keep the same history.
4. **Tag.** The `release` workflow tags the merge commit as `v<version>` within a minute or two. Check it with `git ls-remote --tags origin v<version>`. Do not push a tag yourself.
5. **Release note.** Write `/mnt/project-files/releases/craft-v<version>.md` in the form of the earlier notes there: one paragraph on what the release does, a section per change for the owner, and the release steps with the PR numbers and the tag.
6. **Check the account.** The account plugin syncs from `main` within seconds. Check which craft version the account loads, for example by listing the account plugins. When this session cannot see it, ask the owner to check in a new thread.
7. **Reply.** Give the version, the tag, and the two PRs, and attach the release note.

## Stop and ask

Stop, tell the owner what happened, and wait, when:

- a required check fails, and one fix on the same PR does not make it green;
- a PR has a merge conflict;
- `main` has a hotfix that is not merged back into `dev`;
- the tag is not there five minutes after the merge, or the `release` workflow failed. Give the run link;
- GitHub refuses a merge, for example because a rule wants a review.

Do not retry a refused merge with other flags, and do not push to `main`.
