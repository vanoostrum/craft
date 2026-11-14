# CLAUDE.md

**Craft** is a Claude Code plugin that takes a Linear ticket through spec, build, review, and merge. This repo builds craft with craft.

## Project

| Path | What |
|---|---|
| `plugins/craft/` | The plugin: step skills, hooks, and scripts. This is the product. |
| `.claude-plugin/marketplace.json` | The marketplace that projects install craft and pstack from. |
| `plugins/craft/evals/` | The smoke suite: `claude plugin eval` cases that run the plugin in a real session. |
| `tests/` | pytest tests on the skill text, the hooks, and the scripts. |
| `docs/adr/` | Decisions about how craft is built and released. |
| `.github/workflows/ci.yml` | CI: the `checks` job, and the `evals` job that runs the smoke suite. |
| `.github/workflows/release.yml` | Tags `main` as `v<version>` from `plugin.json` on each push. A release runs from the owner's "release" message with the `release` skill. |

- Python 3.12, managed with **uv**. Add dependencies with `uv add`, never `pip`.
- Lint with **ruff**, format with **ruff format**, type-check with **ty**, check `plugins/craft/skills/rules/scripts/gallery-shot` with **shellcheck**, and test with **pytest**. All must pass.
- Run the checks with the `project-verify` skill, as the `checks` job does. Run the smoke suite with the `verify` skill, as the `evals` job does.
- Write tests first.
- **Test seams.** A pytest test checks skill text, hook behavior, and script behavior. An eval case checks how a step behaves when Claude runs it. Do not check in an eval what a pytest test already checks.
- The agents run the account plugin, not this checkout. The account marketplace syncs from `main`, so `main` holds only releases. PRs target `dev`, and a merge reaches the projects only through a release (`docs/adr/0004`). When craft itself is broken, the owner fixes it by hand, outside craft (`docs/adr/0002`).
- **Unknown skills.** If a skill is unknown, read `.claude/skills/<name>/SKILL.md` and follow it.

## Craft

The `craft:*` skills hold the steps, and `craft:rules` holds the rules for every step. They read the values below.

@.claude/craft.md

Every code change goes through craft. Start with `craft:spec` for a single ticket, or `craft:plan` for bigger work. Never edit code outside a craft step.
