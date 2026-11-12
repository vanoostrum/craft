# Pin craft to a release tag in the marketplace

The claude.ai account marketplace syncs from `main`. With `"source": "./plugins/craft"`, every merge would reach every project thread at once. The marketplace pins craft to a tag instead, as it pins pstack: a `git-subdir` source with `url` `vanoostrum/craft`, `path` `plugins/craft`, and `ref` the release tag. A release bumps `version` in `plugins/craft/.claude-plugin/plugin.json`, tags `main`, and then bumps that `ref` in a one-line PR. Craft is installed only as an account plugin; projects do not pin craft in their `.claude/settings.json` (owner, 2026-11-11). The owner approved this on 2026-11-11.

Superseded by `docs/adr/0004`: claude.ai stopped syncing craft once its source was a `git-subdir` pin.
