# Main is the release branch

ADR 0003 pinned craft to a release tag with a `git-subdir` source and a `ref`. The `claude` CLI honors that `ref`, but the claude.ai account marketplace does not: after the pin merged, it stopped syncing craft at all. Three later merges to `main`, including the bump of `ref` to `v2.5.0`, left the account on the copy synced just before the pin (checked on 2026-11-12). With `"source": "./plugins/craft"`, it syncs from `main` within seconds of a merge. A marketplace cannot name a branch.

So the craft source is `./plugins/craft` again, and `main` holds only releases. Craft PRs target `dev`. A release bumps `version` on `dev`, merges `dev` into `main` with a merge commit, and tags `main`. pstack keeps its `git-subdir` pin, because it lives in another repository. Craft is installed only as an account plugin; projects do not pin craft in their `.claude/settings.json` (owner, 2026-11-11). The owner approved this on 2026-11-12.
