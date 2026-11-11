# Glossary

| Term | Meaning |
|---|---|
| Released craft | The craft version that the agents run: the tag that the marketplace `ref` points to. Not the checkout they change. |
| Release | A `version` bump in `plugins/craft/.claude-plugin/plugin.json`, a tag on `main`, and the PR that bumps craft's `ref` in `.claude-plugin/marketplace.json`. |
| Smoke suite | The `claude plugin eval` cases in `plugins/craft/evals/`. They load the plugin in a real Claude Code session and check that key steps behave. |
| Smoke case | One case of the smoke suite. |
