# The eval smoke suite is the app driver, and `evals` is a required check

Craft's product is skill text and hooks, so tidy files do not prove that it works. Every project gets a merged change when craft is released, so a craft PR must show that the plugin still works in a real Claude Code session. The app driver is a `claude plugin eval` smoke suite in `plugins/craft/evals/`, and the CI job `evals` runs it on every PR as a required check, with one run per case, `--ablation none`, and `--max-cost-usd 1`. The owner approved this budget on 2026-11-11, with a $20 monthly spend limit on the API key.

The cases stay inside the repo and the plugin. They do not touch Linear or GitHub, because the eval tool can only mock MCP servers that the plugin ships, and craft ships none.
