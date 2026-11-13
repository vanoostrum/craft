# Release from the owner's message

ADR 0004 made a release four manual steps: bump on `dev`, merge `dev` into `main`, tag `main`, check the tag. The owner merged the `dev` to `main` PR and pushed the tag by hand, because a cloud session could not push tags and needed the owner's approval to merge into `main`.

Now a release runs from one "release" message from the owner in a thread. The thread follows the repo skill `.claude/skills/release/`. The message is the owner's approval for the two merges of that release, the bump PR into `dev` and the `dev` to `main` PR into `main`, each only when its required checks are green. It approves nothing else. A red check, a conflict, or a refused merge stops the release and goes back to the owner.

The tag comes from the `release` workflow. On every push to `main`, it reads `version` from `plugins/craft/.claude-plugin/plugin.json` and tags the commit `v<version>` when that tag does not exist. It uses the built-in `GITHUB_TOKEN`, with no bot user and no extra token. A tag pushed with that token starts no other workflow, and none needs to start. A later merge at the same version, such as a rollback, keeps the tag on the commit that released it.

The owner approved this on 2026-11-13.
