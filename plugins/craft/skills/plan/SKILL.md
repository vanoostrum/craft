---
name: plan
description: Craft step 0. Turn a brief from craft:brainstorm or craft:setup, a project spec, or a set of features for a working app, into an approved plan of Linear tickets and a rough gallery, then stop at the plan gate. Use for new work that spans more than one or two tickets or adds a new user flow.
model: opus
argument-hint: "<brief, spec, file, or link> [design-variants=<n>] [platforms=<list>] [mode=<gated|one-shot>] [note=<text, file, or link>]..."
---

# craft:plan

Load the `craft:rules` skill first, and follow it. Then load `craft:bstack` with the Skill tool, before any pstack skill.

This step works at a helicopter view. It decides how the work is broken up and what the main screens look like. The details of each ticket wait for `craft:spec` and `craft:design` in ticket mode.

## When to use it

- A new project starts from a spec.
- A working app gets a set of new features, for example after the MVP.

A feature that fits in one or two tickets skips this step and starts at `craft:spec`.

## Input

One of:

- a brief from `craft:brainstorm`: a link to a Linear document titled `Brief: <name>`;
- an environment brief from `craft:setup`: a link to `Brief: Dev environment` or `Brief: Staging and production`;
- a project spec or a feature description from the owner, as text, a file, or a link.

Optional steering arguments follow it, as Steering in `craft:rules` describes. A brief's `Steering` section counts as arguments; arguments given here replace its values. An environment brief always plans with `mode=gated`, whatever the arguments say: write `mode=gated` in the plan ticket's `## Steering`, so its tickets and `craft:next` read it too. If you ignored `mode=one-shot`, tell the owner in one line.

An idea that is not yet clear, with no answer yet to what it is for and why, starts at `craft:brainstorm` instead.

## Steps

1. **Plan ticket.** Use the Linear project from the config; for a brief of a project with no `.claude/craft.md` yet, use the Linear project that holds the brief. For other input in a project with no `.claude/craft.md`, start at `craft:setup dev` instead. Create a plan ticket in it, titled `Plan: <name>`, with the input in its description (for a brief, its link) and the steering arguments under `## Steering`. Move it to **Specifying**. Tell the owner the key. Gate comments go on this ticket, and the tickets of the plan become its sub-issues.
2. **Read what exists.** For an increment, read the code, `GLOSSARY.md`, `docs/adr/`, `design/`, and the open tickets in the Linear project first. For a new project, read whatever the repo already has. Read the files and links in the notes under `## Steering`.
3. **Helicopter grill.** Run the `craft:grill-with-docs` skill with craft rules from `craft:spec`, with these changes:
   - For a brief, read it first. Ask only what it left open, as `craft:spec` does with the plan. Do not reopen its Intent, Goals, Directions, or Decisions. If the code or the slicing conflicts with one of them, ask the owner, and name the brief section.
   - Keep the frontier coarse: users, main flows, boundaries, out of scope, big risks, and constraints. Leave exact states, edge cases, and copy to the grill of each ticket.
   - For an increment, ask only about the new scope and its effect on the existing app: migrations, flows that change, and what must keep working.
   - For an environment brief, the questions are technical, and the brief already settles most of them. Ask only what its **Open for the plan** lists, and what the builder check could not settle.
   - Write the glossary terms and ADRs directly to `GLOSSARY.md` and `docs/adr/` in step 6. They are the decisions every ticket of the plan shares.
4. **Slice the work** into vertical tickets. Each ticket delivers something a client can see and test on its own.
   - **Size.** Split a slice only where the owner could reject one part at the gate and approve the other. If the owner would only judge two parts together, they are one ticket. Fold setup, configuration, and docs into the ticket that needs them; they are never a ticket of their own. An environment brief is the exception, as **Environment tickets** says.
   - **Environment tickets.** For an environment brief, the client of each ticket is the owner and the agents that build the project, and the setup is the deliverable. A ticket is done when someone can see it work in the places the brief names, such as "a fresh cloud agent runs the tests and they pass". Every other ticket of the plan depends on the first one:
     - For `Brief: Dev environment`, the first ticket is a **walking skeleton**: the smallest app with every part, running locally, on a cloud agent, and in CI. It adds the required checks, the verify skill, and the app driver skill, and replaces their `none yet` values in `.claude/craft.md`.
     - For `Brief: Staging and production`, the first ticket is a **deploy skeleton**: one small change that reaches staging and production along the brief's **Promotion**, and is rolled back along its **Rollback**.
     - Items under **Owner first** in the brief's **Owner checklist** are not tickets: copy each one into the description of the first ticket that needs it, under **Owner first**. Copy each **Owner after** item to the ticket after whose merge it is done, under **Owner after**.
     - Write each `(ADR)` decision of the brief to `docs/adr/` in step 6.
   - **Interfaces.** For each ticket, name what it **Consumes** from the tickets it depends on, and what it **Produces** for later tickets: the routes, models, events, glossary terms, or screens that another ticket builds on, by their exact names.
   - **Gated tickets.** With `mode=one-shot`, give `mode=gated` to each ticket that sets up or changes staging or production, such as a deploy, a production database, a domain, or a paid production resource, and to each ticket that depends on one. Put them at the end of the build order. They keep the spec gate and the merge gate.
   - **Fields.** Give each one a title, a goal of one or two sentences, its dependencies, a Linear priority, and a milestone. A milestone is a set of tickets that gives the owner something to try in the app. Give the `ui` label to each ticket that adds or changes a screen. Put the tickets in build order.
5. **Design pass.** If any ticket has the `ui` label, run `craft:design` in project mode with the main flows, the plan ticket key, and the brief's **Look** section, if there is one. It reads `design-variants`, `platforms`, and the notes from the plan ticket's `## Steering`, and settles the platforms. With a **Look**, it freezes the look that the brainstorm settled, and draws only the main-flow screens that the Look does not cover. Without one, it sets the visual identity if there is none, and draws one rough page per main flow. For an increment, it extends the existing gallery and lists each existing page that changes. Add a ticket for each missing screen that it finds, and repeat this step for the new flows.
6. **Commit** the domain docs to the plan ticket's branch. For a `Brief: Dev environment` in a repo without `.claude/craft.md`, also write `.claude/craft.md` from the brief's **Craft wiring**, with `none yet` for the required checks, the verify skill, and the app driver skill, and add the `CLAUDE.md` lines from the brief's **Craft wiring**: the `@.claude/craft.md` import, the unknown-skill line, and the craft-only rule. Commit them next to the gallery commits from step 5, with the `Craft-Issue` trailer. Open a PR against the base branch, with the `gh api` calls from **Open the PR** in `craft:build`. Its body has a one-line summary, the plan ticket link, and the plan. It has no acceptance criteria or app evidence.
7. **Write the plan** as a Linear document in the Linear project, titled `Plan: <name>`, and link it from the plan ticket description. Use the `craft:clear-technical-prose` skill:
   - **Goal:** one or two sentences.
   - **Scope** and **Out of scope.**
   - **Constraints:** hard values that every ticket must keep, such as version floors, limits, platforms, and naming or copy rules. Copy them word for word from the input, the brief, or the grill. Do not paraphrase them.
   - **Decisions:** the decisions from the grill, one line each. Include the platforms from `design/README.md`, if the design pass ran.
   - **Tickets:** a table in build order, with title, goal, priority, milestone, `ui` yes or no, depends on, consumes, produces, and gallery pages.
   - **Changed pages:** for an increment, each existing gallery page that changes, and how.
   - **Risks:** only if there are any.
   - **Up front:** only with `mode=one-shot`, from step 8.
8. **Up front.** Only with `mode=one-shot`. In the one-shot build phase nobody waits for the owner, so find now what only the owner can do, and what costs money. Write it under **Up front** in the plan document:
   - **Owner checklist:** every **Before the plan**, **Owner first**, and **Owner after** item of the brief, and every other action that a ticket needs from the owner, such as an account, an API key, a secret in the cloud environment, a network host, a Linear state, or a repository setting. For each item: the ticket, where the owner does it, and the value to use. Check each one you can, and mark it done or open.
   - **Paid services:** every external service that a ticket uses and that costs money, or can start to cost money, such as a host past its free plan, a database, an email or SMS service, or an AI API. For each one: the ticket, the plan, the price, the free limits, and what makes the cost grow. Read the current price on the provider's pricing page, and write the date you read it. Follow `preferences.md` from `craft:setup`. Say if a choice leaves the plan the owner is on, such as a commercial use on a Hobby plan. If no service costs money, write `none`.
   - **Gated tickets:** the tickets with `mode=gated`, and why.
9. **Review in a fresh agent.** Start a subagent on the `plan reviewer` model from `models.md` from `craft:rules`, so the review is not biased by having written the plan. Give it only the plan ticket key and the PR number, and this task:

   > Load the `craft:bstack` skill first. Read the input, the plan document that the Linear ticket links, and the PR diff. Check that:
   > - every flow and requirement in the input is covered by a ticket, and nothing out of scope is in a ticket;
   > - each ticket is a vertical slice that a client can see and test on its own;
   > - each ticket is split only where the owner could reject one part and approve the other, and no ticket is only setup, configuration, or docs, unless the input is an environment brief;
   > - for a `Brief: Dev environment`, the first ticket is a walking skeleton that every other ticket depends on, each ticket says how an agent in a fresh cloud session sees it work, and the PR writes `.claude/craft.md` if the repo had none;
   > - for a `Brief: Staging and production`, the first ticket is a deploy skeleton that reaches production and is rolled back, and every other ticket depends on it;
   > - each item of the brief's **Owner checklist** under **Owner first** or **Owner after** is on a ticket;
   > - the dependencies have no cycles, and the build order respects them;
   > - each name in a ticket's Consumes is in the Produces of a ticket it depends on, spelled the same, and each name in a Produces is consumed by a later ticket or is visible to a client;
   > - the Constraints are word for word as in the input or the brief;
   > - each ticket that adds or changes a screen has the `ui` label and a gallery page, and no main flow is missing a screen;
   > - the gallery pages follow the gallery rules in `gallery.md` from `craft:rules`. Open their screenshots on the Linear ticket;
   > - the decisions agree with `GLOSSARY.md` and `docs/adr/`;
   > - the plan follows the notes under `## Steering` on the plan ticket;
   > - with `mode=one-shot`: **Up front** names every owner action and every paid service that a ticket needs, with a price and the date it was read, and each ticket that sets up or changes staging or production, or depends on one, has `mode=gated`;
   > - for an increment, every existing page and flow that changes is listed.
   >
   > List real problems only, each with the ticket or file it concerns. Write the review with the `craft:clear-technical-prose` skill. End with PASS or FAIL.

   Post the review as a PR comment. If it ends in FAIL, fix the plan, the tickets, or the gallery, go back to the step that the problem belongs to, and review again. That counts as a failed attempt.
10. **Gate.** Post `🤖 Gate: plan` with the ticket table, the gallery screenshots, the PR link, and the review link, and "Reply approve, or give feedback." With `mode=one-shot`, add **Up front**, and say that this approval starts the grills of every ticket, and that only the launch gate comes before the builds. In chat, ask for approval, by 👍 on the message or a reply "approve", with the ticket link, the number of tickets, and the review link. With `mode=one-shot`, add the paid services and the open owner actions, one line each. Stop.

## Escalation

After 3 failed attempts (review or CI), follow Retries in `craft:rules`.

## After approval

1. Wait for the required checks on the PR to be green, as **Wait for CI** in `craft:build` describes. The plan gate approval is also the merge approval for this PR. Merge it with **Check CI**, **Merge**, and **Check the branch is gone** in `craft:merge`. No commits may have been pushed after the `🤖 Gate: plan` comment; if there were, ask for approval again.
2. Create the milestones in the Linear project, each named `<plan name>: <milestone>`, because the project holds the milestones of every plan. Create each ticket from the table in **Todo**, in the Linear project, as a sub-issue of the plan ticket. Each ticket gets its goal, its Consumes and Produces, the Constraints word for word, the decisions it depends on, links to its gallery pages, its priority and milestone, the `ui` label where set, its **Owner first** items, a copy of the plan ticket's `## Steering`, with `mode=gated` where step 4 set it, and blocking relations for its dependencies. Create the `ui` label in the team if it does not exist.
3. Move the plan ticket to **Done**. For `mode=one-shot`, leave it open instead: the launch gate and the done report go on it, and the done report closes it. Comment `🤖 plan: success — <n> tickets under <plan document link>`. Tell the owner in chat in one line.
4. Run `craft:next`. Do not stop after step 3. `craft:next` picks the tickets in priority and build order, and runs the spec lane and the build lane in parallel. Each ticket's grill reads the plan's decisions first and asks only what the plan left open. With `mode=one-shot`, `craft:next` runs the one-shot phases instead.
