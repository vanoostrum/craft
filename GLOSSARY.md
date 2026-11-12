# Glossary

| Term | Meaning |
|---|---|
| Released craft | The craft version that the agents run, not the checkout they change. It is the craft on `main`, which holds only releases (`docs/adr/0004`). |
| Release | A `version` bump in `plugins/craft/.claude-plugin/plugin.json` on `dev`, a merge of `dev` into `main`, and a tag on `main`. |
| Smoke suite | The `claude plugin eval` cases in `plugins/craft/evals/`. They load the plugin in a real Claude Code session and check that key steps behave. |
| Smoke case | One case of the smoke suite. |
| Feature map | The table in the skill verify that names, for each smoke case, the craft step or hook it covers. |
