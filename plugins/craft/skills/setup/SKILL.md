---
name: setup
description: Craft step that describes a project's environments with the owner, and writes them into a brief for craft:plan. Mode dev covers running locally, cloud agents, and CI, and connects the project to craft. Mode deploy covers staging and production, once v1 works. Use at the start of a new project, to bring an existing project into craft, or when the owner wants staging and production.
model: opus
argument-hint: "[dev|deploy] [<product brief or link>] [note=<text, file, or link>]..."
---

# craft:setup

Load the `craft:rules` skill first, and follow it. Then load `craft:bstack` with the Skill tool, before any pstack skill.

This step works out with the owner where the project runs, and writes it into a brief. `craft:plan` turns the brief into tickets, and the tickets go through spec, build, review, and merge like any other. This step does not build the environment, and it does not commit to the repo.

It has two modes:

| Mode | When | Covers | Brief |
|---|---|---|---|
| `dev` (default) | At the start of a new project, after `craft:brainstorm`, or to bring an existing project into craft. | Running locally, on cloud agents, and in CI, and the craft wiring: the values of `.claude/craft.md`, the required checks, the verify skill, and the app driver skill. | `Brief: Dev environment` |
| `deploy` | When the owner wants real users on the app: by default when the milestone checkpoint in `craft:next` finishes the milestone that the owner calls v1. | Staging, production, and how a change gets from one to the other. | `Brief: Staging and production` |

The brief is a snapshot, as in `craft:brainstorm`. After the plan gate, the ADRs, the code, `.claude/craft.md`, and the tickets are the truth.

## Input

The mode, and optionally the link to the product brief from `craft:brainstorm`. Optional `note=` arguments follow, as Steering in `craft:rules` describes.

Next to this skill, in its base directory:

| File | What |
|---|---|
| `parts.md` | A checklist per part of a project: what to settle for local, cloud agent, CI, and deploy. |
| `preferences.md` | The owner's standing preferences, such as the hosting provider. Follow them unless a part cannot use them, and say so when you depart from one. |

## Steps

1. **Read what exists.** Read the product brief, the repo (code, `CLAUDE.md`, `.claude/`, CI workflows, lock files, Docker or compose files), `docs/adr/`, `GLOSSARY.md`, and the notes. Read `parts.md` and `preferences.md`. For `deploy`, also read the `Brief: Dev environment` document and the ADRs it led to. In a cloud session, read the environment documentation about setup scripts, network access, and secrets, so the cloud agent answers are what the platform offers today. Do not ask the owner what these already answer.
2. **Where craft works.** Only for `dev` in a repo without `.claude/craft.md`. That file is missing here by design: `craft:plan` writes it from this brief. Ask the owner for the GitHub repo and the Linear team key first, and use them in place of `.claude/craft.md` for the rest of this step.
3. **Name the parts.** A project is a set of parts, not one type: web frontend, mobile app, backend API, storage, background jobs, external services. Say back which parts you see, from the brief and the repo, and what each part is for. Ask the owner what is wrong or missing. A part that is not in `parts.md` gets the same questions as the others: how does it run locally, on a cloud agent, and in CI, or, for `deploy`, in staging and production?
4. **The conversation.** Go through the checklist of each part in `parts.md`, for this mode. Ask one question at a time, in chat.
   - This step is about technical matters, unlike `craft:brainstorm`. Still, decide what is cheap to change later yourself, and say so in one line. Ask the owner only about what is costly to undo, such as the stack, the database, the hosting provider, or a mobile build service, and about what only the owner knows: accounts, plans, budgets, and services they already use.
   - Give each question a recommended answer, with its trade-off, and follow `preferences.md` in it.
   - Check each choice against every place at once. A database that runs locally but not on a cloud agent, or a check that needs a secret CI does not have, is a wrong answer.
   - For `dev`, keep the later deploy in mind. If a dev choice limits the deploy, such as a database the preferred host does not offer, say so now.
   - For `deploy`, settle how a merge to the base branch reaches production. Craft merges every ticket to the base branch, so either each merge deploys to production, or a merge deploys to staging and a separate, owner-approved step promotes it. Settle the rollback too.
5. **Owner checklist.** List what only the owner can do, because no agent has the access. For each item, say where the owner does it and what value to use. Sort the items by when they are needed:
   - **Before the plan:** the GitHub repo with at least one commit on the base branch, the Linear team with the craft states and the `ui` label (see the craft README), the cloud environment's network access and secrets, and the accounts and plans the first ticket uses.
   - **Owner first:** items that one ticket needs before it is built, such as a secret for an external service. `craft:plan` copies each to that ticket.
   - **Owner after:** items that can only be done after a ticket is merged, such as making the walking skeleton's checks required on the base branch.
6. **Write the brief.** Create a Linear project named `Dev environment`, or `Staging and production` for `deploy`. Write the brief as a Linear document in it, titled `Brief: Dev environment` or `Brief: Staging and production`, with the `craft:clear-technical-prose` skill:
   - **Intent:** who uses this environment and what for. For `dev`, the users are the owner and the agents that build the project.
   - **Parts:** each part and what it is for.
   - **Places:** for `dev`, a section each for **Local**, **Cloud agents**, and **CI**. For `deploy`, a section each for **Staging**, **Production**, **Promotion** (how a merge reaches each one, and who approves it), and **Rollback**. In each, how every part runs there, and how you know it works.
   - **Craft wiring:** for `dev`, every value for `.claude/craft.md`: the Linear team, the GitHub repo, the base branch, and the required checks, verify skill, and app driver skill that the walking skeleton adds. Also what the verify skill and the app driver skill must do for each part. For `deploy`, the checks the deploy adds, where the app driver runs against staging, and the changes to `.claude/craft.md`.
   - **Constraints:** hard values, word for word as the owner gave them, such as versions, regions, plan limits, and budgets.
   - **Decisions:** each decision from the conversation, one line each. Mark the ones you took yourself `(agent)`. Mark the lasting ones `(ADR)`: `craft:plan` writes them to `docs/adr/`.
   - **Owner checklist:** from step 5, under its three headings.
   - **Product brief:** only for `dev`. The link to the product brief, if there is one. `craft:merge` starts its plan when the walking skeleton is merged.
   - **Later:** for `dev`, what the deploy will need that the dev setup must not block. For `deploy`, what waits for more users or a bigger plan.
   - **Open for the plan:** what the plan must still settle.
   - **Steering:** the `note=` arguments, if any.
7. **Builder check.** Start a subagent on the `brief reviewer` model from `models.md` from `craft:rules`. Give it only the link to the brief, and this task:

   > Load the `craft:bstack` skill first. You will plan this environment into tickets and build them as an agent in a fresh cloud session, and you cannot talk to the person who wrote the brief. Read it. List only the questions you would still need answered: places where you would have to guess, and a wrong guess would matter, such as a part with no way to run in one of the places, a secret or account nobody named, or a check that cannot pass in CI. For each, give the question and why the answer changes the plan. Rank them by importance. If nothing important is left, say "nothing important left".

   Sort its questions as `craft:brainstorm` does: answered already, minor (decide it yourself and mark it `(agent)`), or the owner's. Ask the owner's questions in one message, most important first, and update the brief.
8. **Check the owner's first items.** Check each **Before the plan** item that you can, such as `gh api repos/<repo>/branches/<base>` for the base branch, and the team's states and labels in Linear. Mark each one done or still open in the brief.

## Approval

Ask the owner in chat to approve the brief, with its link, by 👍 on the message or a reply "approve". List the **Before the plan** items that are still open: the owner does them before the plan starts. Any other reply is feedback: go back to the step it belongs to. There is no gate and no Linear comment here, because there is no ticket yet. The plan gate is the first formal gate.

## After approval

When the **Before the plan** items are done, start `craft:plan` in a new session on the brief, as **After approval** in `craft:brainstorm` describes, with this prompt: `Run craft:plan on <brief link>.` For `dev`, tell the owner that the product brief, if there is one, gets its own plan when the walking skeleton is merged. Tell the owner in chat in one line.

## Done when

The brief is a Linear document in its own Linear project, the owner has approved it, and `craft:plan` is started on it.
