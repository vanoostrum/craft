# Glossary

| Term | Meaning |
|---|---|
| Released craft | The craft version that the agents run, not the checkout they change. It is the craft on `main`, which holds only releases (`docs/adr/0004`). |
| Release | A `version` bump in `plugins/craft/.claude-plugin/plugin.json` on `dev`, a merge of `dev` into `main`, and a tag on `main`. |
| Smoke suite | The `claude plugin eval` cases in `plugins/craft/evals/`. They load the plugin in a real Claude Code session and check that key steps behave. |
| Smoke case | One case of the smoke suite. |
| Feature map | The table in the skill verify that names, for each smoke case, the craft step or hook it covers. |
| Merge approval | The owner's own chat message at a one-shot plan gate that lets craft merge the plan PR and each ticket PR of that plan into its base branch of its repo once review passes and checks are green. Craft attaches it by message id to each one-shot build thread. |
| Finding | One problem that a review reports. It is blocking or non-blocking. |
| Blocking finding | A finding that makes the review FAIL, such as an unmet acceptance criterion or a contradiction between specs. `rules/findings.md` has the full list. |
| Non-blocking finding | A finding that does not make the review FAIL. The gate lists it, and the owner decides whether to fix it. Not a note: a note is a `note=` argument. |
| Follow-up review | A review after a fix. It checks the earlier blocking findings, the changed text, and every place that states a changed rule. |
| Ripple check | The search a fix step makes for every other place that states the rule it changed. |
