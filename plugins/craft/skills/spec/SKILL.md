---
name: spec
description: Craft step 1. Turn a feature description or a Linear ticket into a spec with testable acceptance criteria, then stop at the spec gate. Use when the owner asks to work on a ticket or describes a new feature.
model: opus
argument-hint: "<ticket key or feature> [design-variants=<n>] [platforms=<list>] [note=<text, file, or link>]..."
---

# craft:spec

Load the `craft:rules` skill first, and follow it. Then load `craft:bstack` with the Skill tool, before any pstack skill.

## Input

One of:
- a ticket key, e.g. `ABC-12`;
- a feature description typed by the owner.

Optional steering arguments follow it, as Steering in `craft:rules` describes.

When `craft:next` starts this step, the prompt also has a `Brief:`, the blocker brief. It sums up the tickets that block this ticket: their goals, what they produce for this ticket, and the decisions and domain docs that this ticket builds on. This session starts fresh for each ticket, so the blocker brief, `GLOSSARY.md`, and `docs/adr/` are what it knows of the other tickets.

## Steps

1. **Get the ticket.**
   - Ticket key: read it, with all comments.
   - Description: create a ticket in the Linear team from the config, with a short title and the description. Tell the owner the key.
   - Steering arguments: write them under `## Steering` in the ticket description. They replace the values that are already there.
2. Move the ticket to **Specifying**.
3. **Grill.** Run the `craft:grill-with-docs` skill on the ticket. It asks the owner questions in rounds and reads the code to find facts. Follow it, with these rules:
   - Read `GLOSSARY.md` and `docs/adr/` first, if they exist. Then read the blocker brief. Read a blocking ticket's full spec only when the blocker brief leaves a question about it open.
   - If the ticket came from a plan, read the plan ticket's `## Plan` first. Ask only what the plan left open. Keep the ticket's Consumes, Produces, and Constraints: use the names and values exactly as they are written. A change to one of them is a replan proposal, not a spec decision.
   - Ask the rounds in chat. This is an exception to the Chat rule in `craft:rules`.
   - If the ticket is already clear, the first frontier can be empty. Then skip to the next step.
   - Do not write `GLOSSARY.md` or ADR files in the repo now. Write the new and changed glossary terms and ADRs into the spec, under **Domain docs**. `craft:build` commits them.
   - If the owner gave spec feedback, grill only the decisions that the feedback opens again. A `🤖 spec review:` comment from the one-shot spec review counts as spec feedback. Fix what you can decide yourself, and ask the owner only what **What to ask** names.
   - Read the ticket's `🤖 replan` comments. They name the decisions of other tickets that changed this one.
   - If `craft:build` sent the ticket back with a stale spec, grill only the decisions that the merged code changed.
   - **What to ask.** Ask the owner only about:
     - what the feature does for its users: behavior, rules, and scope;
     - UX: screens, flows, states, and copy;
     - an architecture choice that goes against `docs/adr/`, the existing code, or the plan or spec.
   - **How sure you are.** For each question in that scope, judge how likely the owner is to accept your recommended answer. Ask it only when your certainty is medium or low. When your certainty is high, because the ticket, the plan, the ADRs, the existing screens, or the owner's earlier answers already point to it, do not ask. Take your recommended answer and write it under **Decisions** in step 5, marked `(default)`, so the owner can override it at the gate. When in doubt, ask.
   - **What to decide yourself.** Do not ask about a technical choice where your recommended answer follows the code, the ADRs, or common practice. Do not ask how to handle an error case when the right handling is clear. Do not ask about the test seam or how to test: use the test seam rule in `CLAUDE.md`, and write it under **Testing decisions** in step 5. Write each decision you take yourself under **Decisions** in step 5, marked `(agent)`, so the owner sees it at the gate.
4. **Design.** If the ticket has the `ui` label, run the `craft:design` skill in ticket mode. It returns the gallery pages for this ticket. If the grill shows that a ticket without the label changes a screen, add the label and run it too.
5. **Write the spec** into the ticket description, below the original text, under `## Spec`. Use the `craft:clear-technical-prose` skill for its text. Base it on the decisions and the code from the grill. Read more code if a plan task needs it.
   - **Goal:** one or two sentences.
   - **Scope:** what changes.
   - **Out of scope:** what does not.
   - **Decisions:** the decisions from the grill, one line each. Mark the technical ones you took without asking with `(agent)`, and the high-certainty ones on behavior, UX, or architecture with `(default)`.
   - **Review focus:** up to five inputs or conditions that the criteria imply but do not name, and that are most likely to hurt a user, such as an empty list, a duplicate, a very long name, or a lost connection. One line each: the input, and what a user would expect to happen. Most likely first. Each one gets a test in **Plan**. If there are none, write `none`, after you checked.
   - **Acceptance criteria:** a numbered list. Each one is testable and observable, e.g. "Asking for the version returns the version from the package metadata". For a `ui` ticket, each screen state cites its gallery page, e.g. "The search screen with no results matches `design/pages/search/empty.html`".
   - **Gallery pages:** for a `ui` ticket only. Each page from `craft:design`, with one line on what it shows.
   - **Testing decisions:**
     - **Test seam:** where the tests connect to the code, as the test seam rule in `CLAUDE.md` names it. Name any unit test and the reason for it.
     - **What the tests check:** the behavior a user or client sees at the seam. Not the internals, so the tests stay valid when the code behind the seam changes.
     - **Prior art:** the existing tests to copy, named by test and file.
   - **Plan:** a few ordered tasks, each small enough to test on its own.
   - **Domain docs:** only if there are any. The exact `GLOSSARY.md` entries and ADR files to add or change, in the formats of the `craft:domain-modeling` skill.
   - **Risks:** only if there are any.
   If a spec already exists and the owner gave feedback, update it instead and note what changed.
6. **Spec review.** For a ticket with `mode=one-shot`, skip this step: the spec review in plan scope runs before the launch gate. Otherwise, run the spec review in ticket scope, as `spec-review.md` from `craft:rules` describes. Give the subagent the ticket key. Post the review on the ticket as `🤖 spec review: <PASS or FAIL> — <one line>`, with the review below it. If it ends in FAIL, fix the spec. For a problem that needs the owner, ask in chat, as a grill round. For a problem in another ticket's spec, propose the change in the replan check. Then review again. That counts as a failed attempt.
7. **Replan check.** Run the replan check from `craft:next` with this spec's decisions and domain docs.
8. **Gate.** Post `🤖 Gate: spec` with the spec review link, the acceptance criteria, the `(default)` decisions, the replan proposals, and "Reply approve, or give feedback." For a `ui` ticket, the gate also approves the gallery pages: list them, and point to their screenshots on the ticket. In chat, ask for approval, by 👍 on the message or a reply "approve", with the ticket link, the number of criteria, and the `(default)` decisions, one line each, so the owner can override any of them before approving. If there are none, leave the list out. Stop.

## One-shot

**One-shot.** A ticket with `mode=one-shot` in `## Steering` has no spec gate. The grill and the owner's answers are its approval, and the launch gate shows its `(default)` decisions. So, instead of steps 6 and 8 and **After approval**:

1. Post the replan proposals as **Replan check** in `craft:next` says for one-shot. Do not post `🤖 Gate: spec`.
2. Move the ticket to **Ready to build**. Comment `🤖 spec: success — <n> criteria (one-shot)`.
3. Tell the owner in chat, in one line, that the spec is done. Run `craft:next`, which starts the next grill or posts the launch gate.

## Done when

The ticket has a `## Spec` section and a `🤖 Gate: spec` comment, and the owner has been asked. For `mode=one-shot`, the ticket is in **Ready to build** instead. A `ui` ticket also has its gallery pages committed on its branch.

## After approval

See The gate in `craft:rules`. One approval covers the spec and the replan proposals.

1. Apply the replan proposals, as the replan check in `craft:next` describes.
2. Move the ticket to **Ready to build**. Comment `🤖 spec: success — <n> criteria`.
3. Run `craft:next`. It starts the build lane if this ticket or another one is ready, and starts the next grill in a new session. This session's work ends here.
