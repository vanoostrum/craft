---
name: verify
description: Run the craft eval smoke suite against this branch's plugin, and save the JSON result and the HTML report as evidence. Holds the feature map of smoke cases. Use to prove that a change to a step, a hook, or the rules still works in a real Claude Code session. For lint, type check, and tests, use project-verify.
---

# verify

Craft is skill text and hooks, so the app is the plugin running in a Claude Code session. The app driver is the `claude plugin eval` smoke suite in `plugins/craft/evals/` (`docs/adr/0001`). Each smoke case loads the plugin from this checkout in a sandboxed session, sends a prompt, and grades what Claude does.

## Run the suite

From the repo root:

```bash
env -u CRAFT_GCS_BUCKET -u SOUS_GCS_BUCKET \
  claude plugin eval plugins/craft --trust-plugin --no-publish --ablation none --runs 1
```

- Add `--case <glob>` to run only the cases that a change touches, such as `--case spec-loads-rules-first`.
- `env -u` turns off the transcript upload hook. It reads `CRAFT_GCS_BUCKET`, and falls back to the old name `SOUS_GCS_BUCKET`, so unset both.
- Locally the suite runs on the session's own login and needs no API key. CI uses the secret `ANTHROPIC_API_KEY`.
- CI pins Claude Code `2.1.322`. If your `claude --version` differs and a case fails, check the version first.
- Each case costs about $0.10. The CI job adds `--max-cost-usd 1`.

## Evidence

Each run writes a folder `plugins/craft/evals/results/<timestamp>/` with:

- `aggregate-result.json`: the JSON result, with the score, the turns, the cost, and every grader verdict per case;
- the HTML report, with the prompts and the grader verdicts.

The folder is in `.gitignore`. Read the scores from the JSON result:

```bash
python3 -c "import json,sys; d=json.load(open(sys.argv[1]))
for c in d['cases']:
    for r in c['arms']['with']:
        print(c['name'], r['score'], [(g['name'], g['passed']) for g in r['graders']])" \
  plugins/craft/evals/results/<timestamp>/aggregate-result.json
```

The command exits non-zero when any case scores below 1.0.

## Feature map

| Smoke case | Covers |
|---|---|
| `setup-asks-for-the-repo` | `craft:setup dev` in a repo without `.claude/craft.md`: it asks the owner for the GitHub repo first, and writes no brief. |
| `spec-loads-rules-first` | `craft:spec` on a ticket key: it loads `craft:rules` before any other skill. This is the first step of every craft step. |

Not covered by a smoke case:

- `require_bstack.py` (hook `PreToolUse` on `Skill`): pytest covers it in `tests/test_require_bstack.py`.
- `upload_transcripts.py` (hooks `Stop`, `SubagentStop`, `SessionEnd`): pytest covers it in `tests/test_upload_transcripts.py`. The suite runs with it off.
- Every step that reads or writes Linear or GitHub. The suite cannot reach them (`docs/adr/0001`).

When you add a smoke case, add its row here.

## Add a smoke case

A case is a folder in `plugins/craft/evals/` with `prompt.md` and `graders/*.md`. Run `claude plugin eval init --bare <name>` from `plugins/craft/` for a blank one.

- Allow only `Read`, `Glob`, `Grep`, and `Skill` in `allowed_tools`, so a case cannot reach Bash, Linear, or GitHub.
- Set `runs: 1`, a low `max_turns`, and a `timeout_seconds`.
- Prefer free graders: `tool_used`, `tool_order`, `regex`. Use at most one `llm` grader per case, because a wavering judge makes `evals` flaky at the threshold of 1.0.

## Try a step by hand

Start a terminal session on this branch's plugin, and run a step on a live ticket:

```bash
claude --plugin-dir plugins/craft
```

The session runs the checkout, not the account plugin. It reaches Linear and GitHub, so use a test ticket.
