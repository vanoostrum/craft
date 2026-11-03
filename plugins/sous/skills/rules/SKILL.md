---
name: rules
description: The rules of sous for every step. Load it first in every sous step. It holds the kitchen config, the flow, the pass, Linear comments, ticket notes, refires, models, and git naming.
---

# sous:rules

Sous takes a Linear ticket through **spec → build → test → review → merge** for chef. Chef approves at two points of the pass: the spec, and the merge. The `sous:*` skills hold the steps. They are generic, and they read the kitchen's values from `.claude/kitchen.md`.

## Kitchen terms

| Term | Meaning |
|---|---|
| sous | This plugin. It runs the work for chef. |
| the kitchen | The project that installs sous: the repository this session works in. |
| chef | The human who owns the kitchen. |
| the pass | The gates a ticket must clear: the plan pass, the spec pass, and the merge pass. |
| refire | Another try after a step fails. |
| ticket note | A `note=` argument on a ticket. |

## Files of the kitchen and of sous

Read `.claude/kitchen.md` in the kitchen first. It holds these keys:

| Key | What |
|---|---|
| Linear team | The Linear team key, such as `LIBRAG`. |
| GitHub repo | `<owner>/<repo>`. |
| Base branch | The branch that PRs target. |
| Required CI checks | The checks that must be green before a merge. |
| Verify skill | The kitchen skill that installs, lints, type-checks, and tests, as the required checks do. |
| App driver skill | The kitchen skill that launches the app, drives each entry point, and saves evidence and screenshots. |

Its `## Standing notes` section holds ticket notes for every ticket. Follow them as if each ticket had them under `## Steering`.

These paths and names are fixed in every kitchen:

| What | Where |
|---|---|
| Glossary | `GLOSSARY.md` |
| ADRs | `docs/adr/` |
| Design gallery | `design/`: `design/README.md` holds `Current stage` and `Platforms`; `design/gallery.css` and `design/pages/` hold the pages. |
| UI label | The Linear label `ui`, on tickets that add or change a screen. |
| Engineering rules | `CLAUDE.md`, including the test seam rule: where tests connect to the code. |

Sous's own files sit next to this skill, in its base directory. The steps write that directory as `<rules>`:

| File | What |
|---|---|
| `models.md` | The model for each step, each subagent, and each pstack role. |
| `gallery.md` | The gallery rules: platforms, page rules, who changes the gallery, and the rollout stages. |
| `scripts/gallery-shot` | Takes a screenshot of a gallery page for one platform. |

A kitchen skill is a skill in the kitchen's `.claude/skills/`, such as the verify skill. If the Skill tool does not know it, read `.claude/skills/<name>/SKILL.md` and follow it.

## pstack

Load `sous:bstack` with the Skill tool before any `pstack:` skill. A hook blocks pstack skills until it is loaded. Where bstack differs from pstack, including pstack's session-start instruction to use `pstack:poteto-mode`, bstack wins. If no `pstack:` skill is available, stop and tell chef to enable `pstack@sous`.

## Flow

| Step | Skill | Lane | Linear state |
|---|---|---|---|
| Plan, once per project or increment, with a fresh-agent review | `sous:plan` | — | Plan ticket: Specifying |
| 🚦 The pass: plan | — | — | Plan ticket: Specifying |
| Pick the next ticket for each lane | `sous:next` | — | Todo, or Ready to build |
| Spec, with `sous:grill-with-docs` | `sous:spec` | spec | Specifying |
| Design, for tickets with the `ui` label | `sous:design` | spec | Specifying |
| 🚦 The pass: spec, with the replan check | — | spec | Specifying, then Ready to build |
| Build + test | `sous:build` | build | Building |
| Review | `sous:review` | build | In Review |
| 🚦 The pass: merge | — | build | In Review |
| Merge, with the replan check | `sous:merge` | build | Done |

Sous works in two lanes, in parallel. The spec lane needs chef and runs up to four tickets ahead. The build lane runs on its own, up to the merge pass. `sous:next` picks the ticket for each lane and holds the lane rules, the replan check, and the milestone checkpoint.

When asked to "work on" a ticket or a feature, run the steps in order from wherever the ticket is. Stop at each pass. Start at `sous:plan` for a project spec, or for new work that spans more than one or two tickets or adds a new user flow. Otherwise start at `sous:spec`. `sous:spec` runs `sous:design` itself. When asked to "work on the plan" or to "pick up the next ticket", run `sous:next`.

## Rules for every step

- **Linear is the source of truth.** Read the ticket's current state and comments before acting. Do not rely on memory of earlier sessions.
- **Sous comments.** Every comment sous writes in Linear starts with `🤖`. Comments without it are from chef. Each step adds one comment when it ends: `🤖 <step>: <success|failed|escalated> — <one line>`.
- **Dependencies.** A ticket with a Linear "blocked by" relation is not built until each ticket that blocks it is Done. `sous:next` and `sous:build` check this.
- **Steering.** `sous:plan` and `sous:spec` take optional arguments after their input, as `key=value`. Scope is not an argument: `sous:plan` decides from the repo whether the work is a new project or an increment.

  | Argument | Default | Effect |
  |---|---|---|
  | `design-variants=<n>` | `1` | `sous:design` draws `n` distinct prototypes of each new screen, side by side, and chef picks one. |
  | `platforms=<list>` | derived | The platforms the gallery covers, primary first, from `desktop`, `mobile`, `ios`, `android`; for example `platforms=ios,android`. By default `sous:design` derives them from the project, as `gallery.md` describes. |
  | `note=<text, file, or link>` | none | A ticket note: guidance for any step, such as a document on the local or cloud deployment setup. Repeat it for more notes. |

  The step writes the arguments under `## Steering` in the ticket description, with the default for each one not given. A ticket that `sous:plan` creates gets a copy of the plan ticket's `## Steering`. Arguments given to `sous:spec` replace those values on that ticket. Every step reads `## Steering` on its ticket, and the standing notes in `.claude/kitchen.md`, before it starts, and follows the notes that concern it. It reads a file or link in a note when the note concerns its work.
- **The pass.** At a pass, post `🤖 Pass: plan`, `🤖 Pass: spec`, or `🤖 Pass: merge` with a short summary and the question, then stop and ask chef in chat too. The pass is approved when either:
  - chef says "approve" in this chat. Then post `🤖 Approved: <pass> (in chat)` on the ticket, or
  - chef reacts with 👍 to the pass message in this chat. Then post `🤖 Approved: <pass> (👍 in chat)` on the ticket. Only a 👍 on the pass message counts, and only if the chat delivers reactions to the agent. A 👍 that chef removes again does not count, or
  - a comment from chef on the ticket after the latest pass comment says "approve".

  A reaction on a Linear comment does not count: sous cannot read reactions in Linear. Tickets from before sous have `🤖 Gate: <pass>` comments. Read them as `🤖 Pass: <pass>`.

  Any other reply from chef is feedback: go back to the step before the pass and use it.
- **UI feedback at the merge pass.** For a ticket with the `ui` label, the merge pass is one polish pass against the gallery. A polish fix goes back to `sous:build`, which changes the code and the gallery page in the same PR. Feedback that changes the design goes back to `sous:design` in ticket mode, then through the spec pass again.
- **Writing for humans.** Write every chat message, Linear comment, spec, PR body, review comment, and doc with the `sous:clear-technical-prose` skill. The fixed formats in these rules keep their shape. The prose inside them follows the skill.
- **Chat.** Send a chat message only at the end of a step, at a pass, when blocked, or for a grill or design round in `sous:plan`, `sous:spec`, or `sous:design`. The message gives the result, what you need from chef, and a link. The details go to the Linear ticket and the PR. Do not describe tool calls or progress in chat.
- **Models.** Each step runs on the model in its `model:` header, and each subagent on the model in `models.md`. Read `models.md` now.
- **Subagents.** Run verify, CI polling, and log reading in a subagent, on the model from `models.md`. The subagent returns pass or fail. For a fail it returns the error and the file. Do not paste tool output into chat.
- **Refires.** A step gets at most 3 failed attempts. Each new try after a failure is a refire, and its comment says which one, such as `🤖 build: refire 1 of 2 — the pass failed on lint`. After the third failure, move the ticket to **Needs human**, comment what was tried and what blocks, and tell chef.
- **GitHub.** Use the session's built-in GitHub connection; no extra token is needed. Use `gh api` with REST endpoints only. The cloud sandbox blocks GitHub's GraphQL API, so `gh pr ...` commands fail there.
- **Git.** Branch `<team lowercase>-<num>/<slug>`, e.g. `abc-12/version-endpoint`. PR title `[<TEAM>-<num>] <title>`. Every commit ends with the trailer `Factory-Issue: <TEAM>-<num>`. Never push to the base branch. Never commit secrets.
