---
name: project-verify
description: How to install, lint, format-check, type-check, shellcheck, and test the craft repo, as the `checks` CI job does. Use before every commit, and to reproduce a red `checks` job.
---

# project-verify

Run these commands from the repo root, in this order. They are the steps of the `checks` job in `.github/workflows/ci.yml`, in the same order.

```bash
uv sync --frozen
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run shellcheck plugins/craft/skills/rules/scripts/gallery-shot
uv run pytest
```

Run each one, also after one fails, so you see every failure in one pass. All must pass.

## Report

- When all pass, say so.
- When one fails, name the step that failed, such as `Ruff format`, and give its error and the file. Do not report a pass while a step is red.

## Fixes

- Formatting: `uv run ruff format .`.
- Safe lint fixes: `uv run ruff check --fix .`.
- Ruff runs with `select = ["ALL"]`. Fix the code rather than adding an ignore. If an ignore is truly needed, scope it to one line, with a reason.
- shellcheck comes from the `shellcheck-py` dev dependency, so no system shellcheck is needed.
- Add dependencies with `uv add` or `uv add --dev`, and commit `uv.lock`.

## Notes

- The `evals` CI job runs the smoke suite. The app driver skill `verify` runs it locally.
- Follow the test seam rule in `CLAUDE.md`: pytest checks skill text, hooks, and scripts; a smoke case checks what Claude does with the plugin.
