# Pin craft to a release tag in the marketplace

The claude.ai account marketplace syncs from `main`. With `"source": "./plugins/craft"`, every merge would reach every project thread at once. The marketplace pins craft to a tag instead, as it pins pstack: a `git-subdir` source with `url` `vanoostrum/craft`, `path` `plugins/craft`, and `ref` the release tag. A release is a tag plus a one-line PR that bumps that `ref`. Terminal sessions keep pinning a tag in each project's `.claude/settings.json`. The owner approved this on 2026-11-11.
