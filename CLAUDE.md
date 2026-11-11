# CLAUDE.md

**Craft** is a Claude Code plugin that takes a Linear ticket through spec, build, review, and merge. This repo builds craft with craft.

## Project

| Path | What |
|---|---|
| `plugins/craft/` | The plugin: step skills, hooks, and scripts. This is the product. |
| `.claude-plugin/marketplace.json` | The marketplace that projects install craft and pstack from. |
| `tests/` | pytest tests on the skill text, the hooks, and the scripts. |
| `docs/adr/` | Decisions about how craft is built and released. |
| `.github/workflows/ci.yml` | CI. |

- Python 3.12, managed with **uv**. Add dependencies with `uv add`, never `pip`.
- Lint with **ruff**, format with **ruff format**, type-check with **ty**, check `plugins/craft/skills/rules/scripts/gallery-shot` with **shellcheck**, and test with **pytest**. All must pass.
- Write tests first.
- **Test seams.** A pytest test checks skill text, hook behavior, and script behavior. An eval case checks how a step behaves when Claude runs it. Do not check in an eval what a pytest test already checks.
- The agents run the account plugin, not this checkout. Until craft is pinned to a release tag (`docs/adr/0003`), the account marketplace syncs from `main`, so every merge reaches every project at once. After the pin, a merge reaches the projects only through a release. When craft itself is broken, the owner fixes it by hand, outside craft (`docs/adr/0002`).
- **Unknown skills.** If a skill is unknown, read `.claude/skills/<name>/SKILL.md` and follow it.

## Craft

The `craft:*` skills hold the steps, and `craft:rules` holds the rules for every step. They read the values below.

@.claude/craft.md
