---
name: rules
description: The rules of craft for every step. Load it first in every craft step. It holds the project config, the flow, the gates, Linear comments, notes, retries, models, and git naming.
---

# craft:rules

Craft takes a Linear ticket through **spec → build → test → review → merge** for the owner. The owner approves at two gates: the spec, and the merge. The `craft:*` skills hold the steps. They are generic, and they read the project's values from `.claude/craft.md`.

## Terms

| Term | Meaning |
|---|---|
| craft | This plugin. It runs the work for the owner. |
| the project | The repository that installs craft: the repository this session works in. |
| the owner | The human who owns the project. |
| gate | A point where a ticket stops for the owner's approval: the plan gate, the spec gate, and the merge gate. |
| retry | Another try after a step fails. |
| note | A `note=` argument on a ticket. |

## Files of the project and of craft

Read `.claude/craft.md` in the project first. It holds these keys:

| Key | What |
|---|---|
| Linear team | The Linear team key, such as `LIBRAG`. |
| GitHub repo | `<owner>/<repo>`. |
| Base branch | The branch that PRs target. |
| Required CI checks | The checks that must be green before a merge. |
| Verify skill | The project skill that installs, lints, type-checks, and tests, as the required checks do. |
| App driver skill | The project skill that launches the app, drives each entry point, and saves evidence and screenshots. |

Its `## Standing notes` section holds notes for every ticket. Follow them as if each ticket had them under `## Steering`.

These paths and names are fixed in every project:

| What | Where |
|---|---|
| Glossary | `GLOSSARY.md` |
| ADRs | `docs/adr/` |
| Design gallery | `design/`: `design/README.md` holds `Current stage` and `Platforms`; `design/gallery.css` and `design/pages/` hold the pages. |
| UI label | The Linear label `ui`, on tickets that add or change a screen. |
| Engineering rules | `CLAUDE.md`, including the test seam rule: where tests connect to the code. |

Craft's own files sit next to this skill, in its base directory. The steps write that directory as `<rules>`:

| File | What |
|---|---|
| `models.md` | The model for each step, each subagent, and each pstack role. |
| `gallery.md` | The gallery rules: platforms, page rules, who changes the gallery, and the rollout stages. |
| `scripts/gallery-shot` | Takes a screenshot of a gallery page for one platform. |

A project skill is a skill in the project's `.claude/skills/`, such as the verify skill. If the Skill tool does not know it, read `.claude/skills/<name>/SKILL.md` and follow it.

## pstack

Load `craft:bstack` with the Skill tool before any `pstack:` skill. A hook blocks pstack skills until it is loaded. Where bstack differs from pstack, including pstack's session-start instruction to use `pstack:poteto-mode`, bstack wins. If no `pstack:` skill is available, stop and tell the owner to enable `pstack@craft`.

## Flow

| Step | Skill | Lane | Linear state |
|---|---|---|---|
| Brainstorm an idea into a brief, with a fresh-agent check | `craft:brainstorm` | — | — |
| Plan, once per project or increment, with a fresh-agent review | `craft:plan` | — | Plan ticket: Specifying |
| 🚦 The gate: plan | — | — | Plan ticket: Specifying |
| Pick the next ticket for each lane | `craft:next` | — | Todo, or Ready to build |
| Spec, with `craft:grill-with-docs` | `craft:spec` | spec | Specifying |
| Design, for tickets with the `ui` label | `craft:design` | spec | Specifying |
| 🚦 The gate: spec, with the replan check | — | spec | Specifying, then Ready to build |
| Build + test | `craft:build` | build | Building |
| Review | `craft:review` | build | In Review |
| 🚦 The gate: merge | — | build | In Review |
| Merge, with the replan check | `craft:merge` | build | Done |

Craft works in two lanes, in parallel. The spec lane needs the owner and runs up to four tickets ahead. The build lane runs on its own, up to the merge gate. `craft:next` picks the ticket for each lane and holds the lane rules, the replan check, and the milestone checkpoint.

When asked to "work on" a ticket or a feature, run the steps in order from wherever the ticket is. Stop at each gate. Start at `craft:brainstorm` for an idea that is not yet clear: what it is for, for whom, and why. It ends with a brief and starts `craft:plan` on it. Start at `craft:plan` for a brief, a project spec, or new work that spans more than one or two tickets or adds a new user flow. Otherwise start at `craft:spec`. `craft:spec` runs `craft:design` itself. When asked to "work on the plan" or to "pick up the next ticket", run `craft:next`.

## Rules for every step

- **Linear is the source of truth.** Read the ticket's current state and comments before acting. Do not rely on memory of earlier sessions.
- **Craft comments.** Every comment craft writes in Linear starts with `🤖`. Comments without it are from the owner. Each step adds one comment when it ends: `🤖 <step>: <success|failed|escalated> — <one line>`.
- **Dependencies.** A ticket with a Linear "blocked by" relation is not built until each ticket that blocks it is Done. `craft:next` and `craft:build` check this.
- **Steering.** `craft:plan` and `craft:spec` take optional arguments after their input, as `key=value`. `craft:brainstorm` takes only `note=`, and writes it into the brief for `craft:plan`. Scope is not an argument: `craft:plan` decides from the repo whether the work is a new project or an increment.

  | Argument | Default | Effect |
  |---|---|---|
  | `design-variants=<n>` | `1` | `craft:design` draws `n` distinct prototypes of each new screen, side by side, and the owner picks one. |
  | `platforms=<list>` | derived | The platforms the gallery covers, primary first, from `desktop`, `mobile`, `ios`, `android`; for example `platforms=ios,android`. By default `craft:design` derives them from the project, as `gallery.md` describes. |
  | `note=<text, file, or link>` | none | A note: guidance for any step, such as a document on the local or cloud deployment setup. Repeat it for more notes. |

  The step writes the arguments under `## Steering` in the ticket description, with the default for each one not given. A ticket that `craft:plan` creates gets a copy of the plan ticket's `## Steering`. Arguments given to `craft:spec` replace those values on that ticket. Every step reads `## Steering` on its ticket, and the standing notes in `.claude/craft.md`, before it starts, and follows the notes that concern it. It reads a file or link in a note when the note concerns its work.
- **The gate.** At a gate, post `🤖 Gate: plan`, `🤖 Gate: spec`, or `🤖 Gate: merge` with a short summary and the question, then stop and ask the owner in chat too. The gate is approved when either:
  - the owner says "approve" in this chat. Then post `🤖 Approved: <gate> (in chat)` on the ticket, or
  - the owner reacts with 👍 to the gate message in this chat. Then post `🤖 Approved: <gate> (👍 in chat)` on the ticket. Only a 👍 on the gate message counts, and only if the chat delivers reactions to the agent. A 👍 that the owner removes again does not count, or
  - a comment from the owner on the ticket after the latest gate comment says "approve".

  A reaction on a Linear comment does not count: craft cannot read reactions in Linear. Tickets from before craft 2.0 have `🤖 Pass: <gate>` comments. Read them as `🤖 Gate: <gate>`.

  Any other reply from the owner is feedback: go back to the step before the gate and use it.
- **UI feedback at the merge gate.** For a ticket with the `ui` label, the merge gate is one polish pass against the gallery. A polish fix goes back to `craft:build`, which changes the code and the gallery page in the same PR. Feedback that changes the design goes back to `craft:design` in ticket mode, then through the spec gate again.
- **Writing for humans.** Write every chat message, Linear comment, spec, PR body, review comment, and doc with the `craft:clear-technical-prose` skill. The fixed formats in these rules keep their shape. The prose inside them follows the skill.
- **Chat.** Send a chat message only at the end of a step, at a gate, when blocked, or for a grill or design round in `craft:plan`, `craft:spec`, or `craft:design`, or for a question in `craft:brainstorm`. The message gives the result, what you need from the owner, and a link. The details go to the Linear ticket and the PR. Do not describe tool calls or progress in chat.
- **Models.** Each step runs on the model in its `model:` header, and each subagent on the model in `models.md`. Read `models.md` now.
- **Subagents.** Run verify, CI polling, and log reading in a subagent, on the model from `models.md`. The subagent returns pass or fail. For a fail it returns the error and the file. Do not paste tool output into chat.
- **Retries.** A step gets at most 3 failed attempts. A failed attempt is a check that fails after the step thinks its work is done: the app driver or CI in `craft:build`, a FAIL from the fresh reviewer in `craft:plan` or `craft:review`, or a failed merge. A red test or verify while the step is still working is not a failed attempt. `craft:build` and `craft:review` share one count per ticket, because a review FAIL sends the ticket back to `craft:build`. Each new try after a failure is a retry, and its comment says which one, such as `🤖 build: retry 1 of 2 — the gate failed on lint`. After the third failure, move the ticket to **Needs human**, comment what was tried and what blocks, and tell the owner.
- **GitHub.** Use the session's built-in GitHub connection; no extra token is needed. Use `gh api` with REST endpoints only. The cloud sandbox blocks GitHub's GraphQL API, so `gh pr ...` commands fail there.
- **Git.** Branch `<team lowercase>-<num>/<slug>`, e.g. `abc-12/version-endpoint`. PR title `[<TEAM>-<num>] <title>`. Every commit ends with the trailer `Craft-Issue: <TEAM>-<num>`. Never push to the base branch. Never commit secrets.
