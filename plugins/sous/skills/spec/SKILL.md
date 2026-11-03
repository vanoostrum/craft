---
name: spec
description: Sous step 1. Turn a feature description or a Linear ticket into a spec with testable acceptance criteria, then stop at the spec pass. Use when chef asks to work on a ticket or describes a new feature.
model: opus
argument-hint: "<ticket key or feature> [design-variants=<n>] [platforms=<list>] [note=<text, file, or link>]..."
---

# sous:spec

Load the `sous:rules` skill first, and follow it. Then load `sous:bstack` with the Skill tool, before any pstack skill.

## Input

One of:
- a ticket key, e.g. `ABC-12`;
- a feature description typed by chef.

Optional steering arguments follow it, as Steering in `sous:rules` describes.

When `sous:next` starts this step, the prompt also has a `Brief:`. It sums up the tickets that block this ticket: their goals, and the decisions and domain docs that this ticket builds on. This session starts fresh for each ticket, so the brief, `GLOSSARY.md`, and `docs/adr/` are what it knows of the other tickets.

## Steps

1. **Get the ticket.**
   - Ticket key: read it, with all comments.
   - Description: create a ticket in the Linear team from the config, with a short title and the description. Tell chef the key.
   - Steering arguments: write them under `## Steering` in the ticket description. They replace the values that are already there.
2. Move the ticket to **Specifying**.
3. **Grill.** Run the `sous:grill-with-docs` skill on the ticket. It asks chef questions in rounds and reads the code to find facts. Follow it, with these rules:
   - Read `GLOSSARY.md` and `docs/adr/` first, if they exist. Then read the brief. Read a blocking ticket's full spec only when the brief leaves a question about it open.
   - If the ticket came from a plan, read the plan ticket's `## Plan` first. Ask only what the plan left open.
   - Ask the rounds in chat. This is an exception to the Chat rule in `sous:rules`.
   - If the ticket is already clear, the first frontier can be empty. Then skip to the next step.
   - Do not write `GLOSSARY.md` or ADR files in the repo now. Write the new and changed glossary terms and ADRs into the spec, under **Domain docs**. `sous:build` commits them.
   - If chef gave spec feedback, grill only the decisions that the feedback opens again.
   - Read the ticket's `🤖 replan` comments. They name the decisions of other tickets that changed this one.
   - If `sous:build` sent the ticket back with a stale spec, grill only the decisions that the merged code changed.
   - **What to ask.** Ask chef only about:
     - what the feature does for its users: behavior, rules, and scope;
     - UX: screens, flows, states, and copy;
     - an architecture choice that goes against `docs/adr/`, the existing code, or the plan or spec.
   - **How sure you are.** For each question in that scope, judge how likely chef is to accept your recommended answer. Ask it only when your certainty is medium or low. When your certainty is high, because the ticket, the plan, the ADRs, the existing screens, or chef's earlier answers already point to it, do not ask. Take your recommended answer and write it under **Decisions** in step 5, marked `(default)`, so chef can override it at the pass. When in doubt, ask.
   - **What to decide yourself.** Do not ask about a technical choice where your recommended answer follows the code, the ADRs, or common practice. Do not ask how to handle an error case when the right handling is clear. Do not ask about the test seam or how to test: use the test seam rule in `CLAUDE.md`, and write it under **Testing decisions** in step 5. Write each decision you take yourself under **Decisions** in step 5, marked `(agent)`, so chef sees it at the pass.
4. **Design.** If the ticket has the `ui` label, run the `sous:design` skill in ticket mode. It returns the gallery pages for this ticket. If the grill shows that a ticket without the label changes a screen, add the label and run it too.
5. **Write the spec** into the ticket description, below the original text, under `## Spec`. Use the `sous:clear-technical-prose` skill for its text. Base it on the decisions and the code from the grill. Read more code if a plan task needs it.
   - **Goal:** one or two sentences.
   - **Scope:** what changes.
   - **Out of scope:** what does not.
   - **Decisions:** the decisions from the grill, one line each. Mark the technical ones you took without asking with `(agent)`, and the high-certainty ones on behavior, UX, or architecture with `(default)`.
   - **Acceptance criteria:** a numbered list. Each one is testable and observable, e.g. "Asking for the version returns the version from the package metadata". For a `ui` ticket, each screen state cites its gallery page, e.g. "The search screen with no results matches `design/pages/search/empty.html`".
   - **Gallery pages:** for a `ui` ticket only. Each page from `sous:design`, with one line on what it shows.
   - **Testing decisions:**
     - **Test seam:** where the tests connect to the code, as the test seam rule in `CLAUDE.md` names it. Name any unit test and the reason for it.
     - **What the tests check:** the behavior a user or client sees at the seam. Not the internals, so the tests stay valid when the code behind the seam changes.
     - **Prior art:** the existing tests to copy, named by test and file.
   - **Plan:** a few ordered tasks, each small enough to test on its own.
   - **Domain docs:** only if there are any. The exact `GLOSSARY.md` entries and ADR files to add or change, in the formats of the `sous:domain-modeling` skill.
   - **Risks:** only if there are any.
   If a spec already exists and chef gave feedback, update it instead and note what changed.
6. **Replan check.** Run the replan check from `sous:next` with this spec's decisions and domain docs.
7. **Pass.** Post `🤖 Pass: spec` with the acceptance criteria, the `(default)` decisions, the replan proposals, and "Reply approve, or give feedback." For a `ui` ticket, the pass also approves the gallery pages: list them, and point to their screenshots on the ticket. In chat, ask for approval, by 👍 on the message or a reply "approve", with the ticket link, the number of criteria, and the `(default)` decisions, one line each, so chef can override any of them before approving. If there are none, leave the list out. Stop.

## Done when

The ticket has a `## Spec` section and a `🤖 Pass: spec` comment, and chef has been asked. A `ui` ticket also has its gallery pages committed on its branch.

## After approval

See The pass in `sous:rules`. One approval covers the spec and the replan proposals.

1. Apply the replan proposals, as the replan check in `sous:next` describes.
2. Move the ticket to **Ready to build**. Comment `🤖 spec: success — <n> criteria`.
3. Run `sous:next`. It starts the build lane if this ticket or another one is ready, and starts the next grill in a new session. This session's work ends here.
