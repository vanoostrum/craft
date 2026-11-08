---
name: setup
description: Craft step that describes a project's environments with the owner, and writes them into a brief for craft:plan. Mode dev covers running locally, cloud agents, and CI, and connects the project to craft. Mode deploy covers staging and production, after v1. Use at the start of a new project, to bring an existing project into craft, or when the owner wants staging and production.
model: opus
argument-hint: "[dev|deploy] [<product brief or link>] [note=<text, file, or link>]..."
---

# craft:setup

Load the `craft:rules` skill first, and follow it. Then load `craft:bstack` with the Skill tool, before any pstack skill.

This step works out with the owner where the project runs, and writes it into a brief. `craft:plan` turns the brief into tickets, and the tickets go through spec, build, review, and merge like any other. This step does not build the environment itself.

It has two modes:

| Mode | When | Covers | Brief |
|---|---|---|---|
| `dev` (default) | At the start of a new project, after `craft:brainstorm`, or to bring an existing project into craft. | Running locally, on cloud agents, and in CI, and the craft wiring: `.claude/craft.md`, the required checks, the verify skill, and the app driver skill. | `Brief: Dev environment` |
| `deploy` | After v1 works, when the owner wants it to run for real users. | Staging and production. | `Brief: Staging and production` |

The brief is a snapshot, as in `craft:brainstorm`. After the plan gate, the ADRs, the code, and the tickets are the truth.

## Input

The mode, and optionally the link to the product brief from `craft:brainstorm`. Optional `note=` arguments follow, as Steering in `craft:rules` describes.

Next to this skill, in its base directory:

| File | What |
|---|---|
| `parts.md` | A checklist per part of a project: what to settle for local, cloud agent, CI, and deploy. |
| `preferences.md` | The owner's standing preferences, such as the hosting provider. Follow them unless a part cannot use them, and say so when you depart from one. |

## Steps

1. **Read what exists.** Read the product brief, the repo (code, `CLAUDE.md`, `.claude/`, CI workflows, lock files, Docker or compose files), `docs/adr/`, `GLOSSARY.md`, and the notes. Read `parts.md` and `preferences.md`. For `deploy`, also read the `Brief: Dev environment` document and the ADRs it led to. In a cloud session, read the environment documentation about setup scripts, network access, and secrets, so the cloud agent answers are what the platform offers today. Do not ask the owner what these already answer.
2. **Name the parts.** A project is a set of parts, not one type: web frontend, mobile app, backend API, storage, background jobs, external services. Say back which parts you see, from the brief and the repo, and what each part is for. Ask the owner what is wrong or missing. A part that is not in `parts.md` gets the same three questions as the others: how does it run locally, on a cloud agent, and in CI (or, for `deploy`, in staging and production)?
3. **The conversation.** Go through the checklist of each part in `parts.md`, for this mode. Ask one question at a time, in chat.
   - This step is about technical matters, unlike `craft:brainstorm`. Still, decide what is cheap to change later yourself, and say so in one line. Ask the owner only about what is costly to undo, such as the stack, the database, the hosting provider, or a mobile build service, and about what only the owner knows: accounts, plans, budgets, and services they already use.
   - Give each question a recommended answer, with its trade-off, and follow `preferences.md` in it.
   - Check each choice against all three places at once. A database that runs locally but not on a cloud agent, or a check that needs a secret CI does not have, is a wrong answer.
   - For `dev`, keep the later deploy in mind. If a dev choice limits the deploy, such as a database the preferred host does not offer, say so now.
4. **Owner checklist.** List what only the owner can do, because no agent has the access: cloud environment settings, network access, secrets, accounts and plans, the Linear team states and labels, branch protection and required checks on GitHub, and app store or signing accounts. For each, say where the owner does it and what value to use.
5. **Write the brief.** Create a Linear project named `Dev environment`, or `Staging and production` for `deploy`. Write the brief as a Linear document in it, titled `Brief: Dev environment` or `Brief: Staging and production`, with the `craft:clear-technical-prose` skill:
   - **Intent:** who uses this environment and what for. For `dev`, the users are the owner and the agents that build the project.
   - **Parts:** each part and what it is for.
   - **Places:** for `dev`, a section each for **Local**, **Cloud agents**, and **CI**. For `deploy`, a section each for **Staging** and **Production**, and **Promotion**: how a change moves from one to the other. In each, how every part runs there, and how you know it works.
   - **Craft wiring:** only for `dev`. The values for `.claude/craft.md`, the required checks, and what the verify skill and the app driver skill must do for each part.
   - **Constraints:** hard values, word for word as the owner gave them, such as versions, regions, plan limits, and budgets.
   - **Decisions:** each decision from the conversation, one line each. Mark the ones you took yourself `(agent)`. Mark the lasting ones `(ADR)`: `craft:plan` writes them to `docs/adr/`.
   - **Owner checklist:** from step 4.
   - **Later:** for `dev`, what the deploy will need that the dev setup must not block. For `deploy`, what waits for more users or a bigger plan.
   - **Open for the plan:** what the plan must still settle.
   - **Steering:** the `note=` arguments, if any.
6. **Builder check.** Start a subagent on the `brief reviewer` model from `models.md` from `craft:rules`. Give it only the link to the brief, and this task:

   > Load the `craft:bstack` skill first. You will plan this environment into tickets and build them as an agent in a fresh cloud session, and you cannot talk to the person who wrote the brief. Read it. List only the questions you would still need answered: places where you would have to guess, and a wrong guess would matter, such as a part with no way to run in one of the places, a secret or account nobody named, or a check that cannot pass in CI. For each, give the question and why the answer changes the plan. Rank them by importance. If nothing important is left, say "nothing important left".

   Sort its questions as `craft:brainstorm` does: answered already, minor (decide it yourself and mark it `(agent)`), or the owner's. Ask the owner's questions in one message, most important first, and update the brief.
7. **Connect the project to craft.** Only for `dev`, and only if the repo has no `.claude/craft.md`. On a branch named `setup/connect-craft`, write `.claude/craft.md` with the values the brief settles. Write `none yet` for the required checks, the verify skill, and the app driver skill: the walking skeleton ticket fills them in. Add the `@.claude/craft.md` import and the unknown-skill line from the craft README to `CLAUDE.md`. Open a PR with the `gh api` calls from **Open the PR** in `craft:build`, with a one-line summary and the brief link.

## Approval

Ask the owner in chat to approve the brief, with its link and the PR link if step 7 ran, by 👍 on the message or a reply "approve". Any other reply is feedback: go back to the step it belongs to. There is no gate and no Linear comment here, because there is no ticket yet. The approval is also the merge approval for the PR from step 7: merge it with **Merge** and **Check the branch is gone** in `craft:merge`. It has no required checks to wait for yet.

## After approval

Start `craft:plan` in a new session on the brief, as **After approval** in `craft:brainstorm` describes, with this prompt: `Run craft:plan on <brief link>.` For `dev`, tell the owner that the product brief, if there is one, waits for its own `craft:plan` until the walking skeleton ticket is Done. Tell the owner in chat in one line, and list the owner checklist items that the first ticket needs.

## Done when

The brief is a Linear document in its own Linear project, the owner has approved it, the PR from step 7 is merged if it ran, and `craft:plan` is started on the brief.
