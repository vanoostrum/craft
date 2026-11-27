---
name: rules
description: The rules of craft for every step. Load it first in every craft step. It holds the project config, the flow, the gates, Linear comments, notes, retries, models, and git naming.
---

# craft:rules

Craft takes a Linear ticket through **spec → build → test → review → merge** for the owner. The owner approves at two gates: the spec, and the merge. In one-shot mode, the owner approves only the plan and answers the grills, and craft builds and merges the rest on its own. The `craft:*` skills hold the steps. They are generic, and they read the project's values from `.claude/craft.md`.

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
| Linear team | The Linear team key, such as `CRAFT`. One team holds the tickets of all of the owner's projects. |
| Linear project | The Linear project of this project, such as `LibRag`. Its documents hold the briefs and plans, and its tickets are the project's backlog. |
| GitHub repo | `<owner>/<repo>`. |
| Base branch | The branch that PRs target. |
| Required CI checks | The checks that must be green before a merge. |
| Verify skill | The project skill that installs, lints, type-checks, and tests, as the required checks do. |
| App driver skill | The project skill that launches the app, drives each entry point, and saves evidence and screenshots. |
| Stacks | The stack profile of each path of the repo, as **Engineering rules** says. Optional. |

A project new to craft has no `.claude/craft.md` yet. `craft:setup` asks the owner for the Linear team, the Linear project, and the GitHub repo, and `craft:plan` takes all values from the **Craft wiring** of the `Brief: Dev environment` and writes the file in its PR.

A project set up before craft 2.3 has no `Linear project` key. Before any step reads the project's tickets, ask the owner which Linear project holds this project, or offer to create one named after it with `linear_team.py` from `craft:setup`. Write the key into `.claude/craft.md` on the step's branch, or, for a step without a branch, in a small PR of its own. Until then, use every open ticket of the Linear team. Tickets of this project that sit in other Linear projects of the team move into it when the owner agrees.

A key with the value `none yet` waits for the ticket that creates it, such as the walking skeleton from a `Brief: Dev environment`. That ticket reads the new values from its own branch, and its own build, review, and merge use them: it proves its verify skill, its app driver skill, and its checks on its own PR. Any other step that needs a `none yet` value skips that work and says so in its step comment.

Its `## Standing notes` section holds notes for every ticket. Follow them as if each ticket had them under `## Steering`.

These paths and names are fixed in every project:

| What | Where |
|---|---|
| Glossary | `GLOSSARY.md` |
| ADRs | `docs/adr/` |
| Design gallery | `design/`: `design/README.md` holds `Current stage` and `Platforms`; `design/gallery.css` and `design/pages/` hold the pages. |
| UI label | The Linear label `ui`, on tickets that add or change a screen. |
| Engineering rules | Three layers, as **Engineering rules** below says: `<rules>/engineering.md`, `<rules>/profiles/<stack>.md` for each profile that `Stacks` names, and `docs/engineering.md`. `CLAUDE.md` keeps the commands and the test seam rule: where tests connect to the code. |

Craft's own files sit next to this skill, in its base directory. The steps write that directory as `<rules>`:

| File | What |
|---|---|
| `models.md` | The model for each step, each subagent, and each pstack role. |
| `spec-review.md` | The fresh-agent review of specs, before the spec gate, or in one-shot mode before a ticket builds and after the last spec. |
| `findings.md` | The rules of every fresh review and every fix: the full review, blocking and non-blocking findings, the follow-up review, and the ripple check. |
| `gallery.md` | The gallery rules: platforms, page rules, who changes the gallery, and the rollout stages. |
| `scripts/gallery-shot` | Takes a screenshot of a gallery page for one platform. |
| `engineering.md` | The shared rules: the engineering rules for every project. |
| `profiles/` | The stack profiles, one `<stack>.md` per stack, and the template `_template.md`. |

A project skill is a skill in the project's `.claude/skills/`, such as the verify skill. If the Skill tool does not know it, read `.claude/skills/<name>/SKILL.md` and follow it.

## pstack

Load `craft:bstack` with the Skill tool before any `pstack:` skill. A hook blocks pstack skills until it is loaded. Where bstack differs from pstack, including pstack's session-start instruction to use `pstack:poteto-mode`, bstack wins. If no `pstack:` skill is available, stop and tell the owner to enable `pstack@craft`.

## Engineering rules

The engineering rules are the written rules that a project's code must follow. They come in three layers. The project rules win over the profile, and the profile wins over the shared rules (`docs/adr/0011`).

| Layer | File |
|---|---|
| Shared rules | `<rules>/engineering.md`, for every project. |
| Stack profile | `<rules>/profiles/<stack>.md`, for each profile that `Stacks` names. |
| Project rules | `docs/engineering.md` in the project. |

- **Stacks.** The key `Stacks` in `.claude/craft.md` names the profile of each path of the repo, as one table row `| Stacks | <list> |`. `<list>` is `none`, or comma-separated pairs `` `<path>` → `<profile>` ``, such as `` `/` → `python-fastapi`, `web/` → `nextjs` ``. A path is relative to the repo root and ends with `/`, and `/` is the whole repo. A missing key reads as `none`. A step reads every profile that `Stacks` names. A file follows the profile of the longest path that holds it. A file in `profiles/` whose name starts with `_` is a template, and `Stacks` never names it.
- **Rule format.** Each rule in every layer is one bullet that starts with a bold name, such as `**Catch narrowly.**`. A finding names a rule by its file and its bold name, such as `engineering.md` **Catch narrowly.**
- **`docs/engineering.md` format.** The file has, in this order:
  - a `# Engineering rules` title;
  - one line that says the project rules win over the profile and the shared rules;
  - `## <topic>` sections of rule bullets. Each bullet ends with `Source:` and the ADR, the `CLAUDE.md` line, or the code path behind it. A rule that overrides a rule of another layer ends with `Replaces: <file> **<name>**`;
  - last, a section `## In CLAUDE.md`: one bullet per rule that `CLAUDE.md` holds, such as the test seam rule, with its bold name and a link to its line in `CLAUDE.md`, and no copy of its text.
- **Read the rules.** `craft:spec` and `craft:build` read the rules right after they load `craft:bstack`, before their first numbered step. Read `Stacks` in `.claude/craft.md`, then read each rule file with the Read tool, in full: `<rules>/engineering.md`, each profile that `Stacks` names, and `docs/engineering.md`. `craft:review` gives the fresh reviewer the absolute path of each of these files, with `<rules>` written out as the base directory of `craft:rules`, because the subagent does not know `<rules>`. A subagent of `craft:spec` gets the absolute paths in the same way.
- **Skips.** Do not ask the owner about a missing rule file. Skip it, go on, and name each skip in the step comment:
  - no `Stacks` key, or `none`: `Stacks: none`;
  - a profile that `Stacks` names, without a file: `profile <stack> missing`;
  - no `docs/engineering.md`: `no docs/engineering.md`.
- **Rule exception.** A spec can let its ticket break one rule, with the decision `(exception: <rule name>)` under **Decisions**. The owner picks it in the grill of `craft:spec`. In a review, a break of that rule is not a blocking finding.

## Flow

| Step | Skill | Lane | Linear state |
|---|---|---|---|
| Brainstorm an idea into a brief, with a fresh-agent check | `craft:brainstorm` | — | — |
| Describe the environments into a brief: dev at the start, deploy after v1 | `craft:setup` | — | — |
| Plan, once per project or increment, with a fresh-agent review | `craft:plan` | — | Plan ticket: Specifying |
| 🚦 The gate: plan | — | — | Plan ticket: Specifying |
| Pick the next ticket for each lane | `craft:next` | — | Todo, or Ready to build |
| Spec, with `craft:grill-with-docs` and a fresh-agent spec review | `craft:spec` | spec | Specifying |
| Design, for tickets with the `ui` label | `craft:design` | spec | Specifying |
| 🚦 The gate: spec, with the replan check | — | spec | Specifying, then Ready to build |
| Build + test | `craft:build` | build | Building |
| Review | `craft:review` | build | In Review |
| 🚦 The gate: merge | — | build | In Review |
| Merge, with the replan check | `craft:merge` | build | Done |
| Audit how well craft's phases did their job, weekly | `craft:audit` | — | — |

`craft:audit` runs outside the ticket flow, weekly or when the owner says "Run craft:audit". It judges the craft process against rubrics, and may read code as evidence, but proposes fixes only to craft, never to the code (`docs/adr/0010`). It has no ticket, no gate, and no step comment, makes no branch and no commit, and keeps its scores and findings in Linear only (`docs/adr/0009`). The rules below about tickets, gates, step comments, Steering, and git do not apply to it.

Craft works in two lanes, in parallel. The spec lane needs the owner and runs up to four tickets ahead. The build lane runs on its own, up to the merge gate. `craft:next` picks the ticket for each lane and holds the lane rules, the replan check, and the milestone checkpoint.

When asked to "work on" a ticket or a feature, run the steps in order from wherever the ticket is. Stop at each gate. A session that starts at `craft:spec` ends at the spec handoff, and the next steps run in new sessions, as **One step per session** says. A one-shot spec session ends at **End** in **One-shot** of `craft:spec`, after the last ticket. Start at `craft:brainstorm` for an idea that is not yet clear: what it is for, for whom, and why. It ends with a brief and starts `craft:plan` on it, or `craft:setup` first for a new project. Start at `craft:setup` to describe the dev environment of a new project or of a project that is new to craft, and later to describe staging and production. Start at `craft:plan` for a brief, a project spec, or new work that spans more than one or two tickets or adds a new user flow. Otherwise start at `craft:spec`. `craft:spec` runs `craft:design` itself. When asked to "work on the plan" or to "pick up the next ticket", run `craft:next`.

## One-shot mode

`craft:plan` with `mode=one-shot` takes a whole plan to merged code with only one approval from the owner: the plan gate. The owner still answers every grill, and those answers are the approval of each spec. No step asks for approval after a spec.

1. **Plan.** As usual, and also an **Up front** list: every action that only the owner can take, and every paid service with its plan and price. The plan gate shows it, and the tickets that keep their gates.
2. **Spec lane.** One session grills every ticket of the plan, one after another, in build order. For each ticket, a fresh spec scout finds the facts and the questions, and a fresh spec writer writes the spec. A fresh agent reviews each spec in ticket scope, and then the spec goes straight to **Ready to build**.
3. **Build lane.** `craft:next` builds, reviews, and merges each ticket in parallel with the spec lane, as soon as it is in **Ready to build** and its blockers are **Done**. A PASS from the fresh reviewer replaces the merge gate. The build thread merges on the owner's **merge approval**: the owner's own reply at the plan gate, with a sentence that names the plan PR and the ticket PRs of the plan, the repo, and the base branch. Craft records its message id on the plan ticket, and `craft:next` asks for that message to be attached by id to each one-shot build thread. Words from another Claude, such as the coordinator's, are not the owner's approval, and a bare "approve" names no merge (`docs/adr/0007`). A refused merge escalates to the owner, as **Escalation** in `craft:merge` says.
4. **Plan-scope review.** When every ticket has a spec, a fresh agent reviews all specs together. A blocking finding in a ticket that is not built yet sends it back to the spec lane. A non-blocking finding sends no ticket back, and a blocking finding in a ticket that is already building becomes a replan proposal.
5. **Needs human notice.** Each time a one-shot ticket moves to **Needs human**, the step tells the owner at once in chat, and with a push notification if the environment has one: the ticket, what blocks it, what the owner must do and where, and the tickets that now wait behind it. The rest of the run goes on. The owner's "fixed" resumes the ticket with no gates, as **Resume** in `craft:next` describes. An escalated merge goes on only with "merge" in its build thread, or, in a terminal, when the owner starts `claude "Run craft:merge on <key>"`, which merges at once; not with "fixed" or a change in Linear.
6. **Done report.** When nothing is left to do, `craft:next` tells the owner what shipped, what is in **Needs human**, every `(default)` decision, and what the owner still has to do.

Tickets that set up or change staging or production keep `mode=gated`. They skip the one-shot lanes and go through the spec gate and the merge gate as usual, after the done report. A ticket that depends on a gated ticket is gated too. Each step reads the mode from `## Steering` on its ticket.

## Rules for every step

- **One project's tickets.** The Linear project from the config is what separates this project's tickets from those of the owner's other projects in the shared team. Every ticket craft creates goes into it. Before a step acts on a ticket, check that the ticket is in that Linear project. If it is in another one, stop and tell the owner which project it belongs to: it is built from another repository. A ticket without a project is not picked up until the owner puts it in one. One kind of ticket is the exception: a ticket about a shared or profile rule, such as a rule change ticket from `craft:spec`, lives in the Linear project `Craft`, whatever project raised it. A step in any project may file it there, or add evidence to it.
- **Linear is the source of truth.** Read the ticket's current state and comments before acting. Do not rely on memory of earlier sessions.
- **Craft comments.** Every comment craft writes in Linear starts with `🤖`. Comments without it are from the owner. Each step adds one comment when it ends: `🤖 <step>: <success|failed|escalated> — <one line>`.
- **Dependencies.** A ticket with a Linear "blocked by" relation is not built until each ticket that blocks it is Done. `craft:next` and `craft:build` check this.
- **One step per session.** Each step runs in its own session, so it has a clean context and its own transcript. A spec session ends at the spec handoff: after **After approval** in `craft:spec`, or in one-shot mode at **End** in **One-shot**, after the last ticket. Until then, a one-shot spec session goes on to the next ticket after each `craft:next` call. A spec session never loads `craft:build`, `craft:review`, or `craft:merge`, even when the request that started it asked for the build too: `craft:next` starts the build in a new session. A build session runs `craft:build`, `craft:review`, and `craft:merge`: the merge after the merge gate, or in one-shot mode at once. A hook in craft denies `craft:build`, `craft:review`, and `craft:merge` in a session that started with `craft:spec`.
- **Steering.** `craft:plan` and `craft:spec` take optional arguments after their input, as `key=value`. `craft:brainstorm` and `craft:setup` take `note=` as input, and write it into the brief for `craft:plan`. At the brief approval, `craft:brainstorm` asks the owner for the plan's arguments, and `craft:setup` only for a `note=`. A brief's **Steering** holds only the arguments the owner gave, with no defaults filled in: `craft:plan` fills them in on the plan ticket. Scope is not an argument: `craft:plan` decides from the repo whether the work is a new project or an increment.

  | Argument | Default | Effect |
  |---|---|---|
  | `design-variants=<n>` | `1` | `craft:design` draws `n` distinct prototypes of each new screen, side by side, and the owner picks one. After a brainstorm, a new screen is one that is not in the brief's **Look**. |
  | `platforms=<list>` | derived | The platforms the gallery covers, primary first, from `desktop`, `mobile`, `ios`, `android`; for example `platforms=ios,android`. By default `craft:design` derives them from the project, as `gallery.md` describes. |
  | `mode=<gated|one-shot>` | `gated` | Only for `craft:plan`, and not for an environment brief: its plan always runs gated. `one-shot` runs the plan as **One-shot mode** below describes. `craft:plan` writes `mode=gated` on each staging or production ticket of a one-shot plan. |
  | `note=<text, file, or link>` | none | A note: guidance for any step, such as a document on the local or cloud deployment setup. Repeat it for more notes. |

  The step writes the arguments under `## Steering` in the ticket description, with the default for each one not given. A ticket that `craft:plan` creates gets a copy of the plan ticket's `## Steering`. Arguments given to `craft:spec` replace those values on that ticket. Every step reads `## Steering` on its ticket, and the standing notes in `.claude/craft.md`, before it starts, and follows the notes that concern it. It reads a file or link in a note when the note concerns its work.
- **The gate.** At a gate, post `🤖 Gate: plan`, `🤖 Gate: spec`, or `🤖 Gate: merge` with a short summary and the question, then stop and ask the owner in chat too. The gate is approved when either:
  - the owner says "approve" in this chat. Then post `🤖 Approved: <gate> (in chat)` on the ticket, or
  - the owner reacts with 👍 to the gate message in this chat. Then post `🤖 Approved: <gate> (👍 in chat)` on the ticket. Only a 👍 on the gate message counts, and only if the chat delivers reactions to the agent. A 👍 that the owner removes again does not count, or
  - a comment from the owner on the ticket after the latest gate comment says "approve".

  At a one-shot plan gate, the owner's reply with the merge approval sentence approves the gate too. Then post `🤖 Approved: plan (merge approval in chat, message <message id>)` on the plan ticket, as **Merge approval** in `craft:plan` says.

  A reaction on a Linear comment does not count: craft cannot read reactions in Linear. Tickets from before craft 2.0 have `🤖 Pass: <gate>` comments. Read them as `🤖 Gate: <gate>`. One-shot plans from before craft 2.8 can have a `🤖 Gate: launch` comment. It is an old marker: it is approved by the same rules, and `craft:next`, `craft:build`, and `craft:merge` read it.

  Any other reply from the owner is feedback. At the plan gate and the spec gate, go back to the step before the gate and use it. At the merge gate, load `craft:build` again with the Skill tool, with the ticket key in the arguments, and run its **Fix**, except as **UI feedback at the merge gate** says. The fix follows **Ripple check** in `findings.md`: each item of feedback counts as a blocking finding, and the next review is a follow-up review. The owner can turn a non-blocking finding from the gate into feedback.
- **UI feedback at the merge gate.** For a ticket with the `ui` label, the merge gate is one polish pass against the gallery. A polish fix goes back to `craft:build`, loaded again with the Skill tool, with the ticket key in the arguments, which changes the code and the gallery page in the same PR. Feedback that changes the design goes back to `craft:design` in ticket mode, then through the spec gate again.
- **Writing for humans.** Write every chat message, Linear comment, spec, PR body, review comment, and doc with the `craft:clear-technical-prose` skill. The fixed formats in these rules keep their shape. The prose inside them follows the skill.
- **Chat.** Send a chat message only at the end of a step, at a gate, when blocked, or for a grill or design round in `craft:plan`, `craft:spec`, or `craft:design`, or for a question in `craft:brainstorm`. The message gives the result, what you need from the owner, and a link. The details go to the Linear ticket and the PR. Do not describe tool calls or progress in chat. In the one-shot build lane, the ticket steps write only to Linear and GitHub. Their only chat message is the Needs human notice from **One-shot mode**. It also carries the ask of an escalated merge, and the one ask for a missing merge approval. The done report tells the owner the rest.
- **Models.** Each step runs on the model in its `model:` header, and each subagent on the model in `models.md`. Read `models.md` now.
- **Subagents.** Run verify, CI polling, and log reading in a subagent, on the model from `models.md`. The subagent returns pass or fail. For a fail it returns the error and the file. Do not paste tool output into chat.
- **Retries.** A step gets at most 5 failed attempts. A failed attempt is a check that fails after the step thinks its work is done: the app driver or CI in `craft:build`, a FAIL from the fresh reviewer in `craft:plan` or `craft:review`, or a failed merge. A red test or verify while the step is still working is not a failed attempt. A refused merge is not a failed attempt either: it escalates, as **Escalation** in `craft:merge` says. `craft:build` and `craft:review` share one count per ticket, because a review FAIL sends the ticket back to `craft:build`. Each new try after a failure is a retry, and its comment says which one, such as `🤖 build: retry 1 of 4 — CI failed on lint`. After the fifth failure, move the ticket to **Needs human**, comment what was tried and what blocks, and tell the owner. In one-shot mode, then run `craft:next`, so the run goes on with the tickets that do not depend on it.
- **GitHub.** Use the session's built-in GitHub connection; no extra token is needed. Use `gh api` with REST endpoints only. The cloud sandbox blocks GitHub's GraphQL API, so `gh pr ...` commands fail there. To merge, use the GitHub `merge_pull_request` tool where the session has the GitHub MCP tools, as step 3 of `craft:merge` says.
- **Git.** Branch `<team lowercase>-<num>/<slug>`, e.g. `abc-12/version-endpoint`. PR title `[<TEAM>-<num>] <title>`. Every commit ends with the trailer `Craft-Issue: <TEAM>-<num>`. Never push to the base branch. Never commit secrets.
