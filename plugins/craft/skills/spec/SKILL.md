---
name: spec
description: Craft step 1. Turn a feature description or a Linear ticket into a spec with testable acceptance criteria, then stop at the spec gate. In one-shot mode, grill every ticket of the plan in one session, with no gate. Use when the owner asks to work on a ticket or describes a new feature.
model: opus
argument-hint: "<ticket key, one-shot plan key, or feature> [design-variants=<n>] [platforms=<list>] [note=<text, file, or link>]..."
---

# craft:spec

Load the `craft:rules` skill first, and follow it. Then load `craft:bstack` with the Skill tool, before any pstack skill.

## Input

One of:
- a ticket key, e.g. `ABC-12`;
- a feature description typed by the owner;
- a one-shot plan ticket, from the prompt `Run craft:spec on the one-shot plan <plan key>.`, which `craft:next` sends. Run **One-shot** below. A ticket key of a one-shot ticket runs **One-shot** too, starting with that ticket.

Optional steering arguments follow it, as Steering in `craft:rules` describes.

When `craft:next` starts this step, the prompt also has a `Brief:`, the blocker brief. It sums up the tickets that block this ticket: their goals, what they produce for this ticket, and the decisions and domain docs that this ticket builds on. This session starts fresh for each ticket, so the blocker brief, `GLOSSARY.md`, and `docs/adr/` are what it knows of the other tickets.

## Steps

1. **Get the ticket.**
   - Ticket key: read it, with all comments.
   - Description: create a ticket in the Linear team and the Linear project from the config, with a short title and the description. Tell the owner the key.
   - Steering arguments: write them under `## Steering` in the ticket description. They replace the values that are already there.
2. Move the ticket to **Specifying**.
3. **Grill.** Run the `craft:grill-with-docs` skill on the ticket. It asks the owner questions in rounds and reads the code to find facts. Follow it, with these rules:
   - Read `GLOSSARY.md` and `docs/adr/` first, if they exist. Then read the blocker brief. Read a blocking ticket's full spec only when the blocker brief leaves a question about it open.
   - If the ticket came from a plan, read the plan document first: the `Plan: <name>` document that the plan ticket links. Ask only what the plan left open. Keep the ticket's Consumes, Produces, and Constraints: use the names and values exactly as they are written. A change to one of them is a replan proposal, not a spec decision.
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
6. **Spec review.** For a ticket with `mode=one-shot`, **One-shot** below runs it instead. Otherwise, run the spec review in ticket scope, as `spec-review.md` from `craft:rules` describes. Give the subagent the ticket key. Post the review on the ticket as `🤖 spec review: <PASS or FAIL> — <one line>`, with the review below it. If it ends in FAIL, fix the spec. For a problem that needs the owner, ask in chat, as a grill round. For a problem in another ticket's spec, propose the change in the replan check. Then review again. That counts as a failed attempt.
7. **Replan check.** Run the replan check from `craft:next` with this spec's decisions and domain docs.
8. **Gate.** Post `🤖 Gate: spec` with the spec review link, the acceptance criteria, the `(default)` decisions, the replan proposals, and "Reply approve, or give feedback." For a `ui` ticket, the gate also approves the gallery pages: list them, and point to their screenshots on the ticket. In chat, ask for approval, by 👍 on the message or a reply "approve", with the ticket link, the number of criteria, and the `(default)` decisions, one line each, so the owner can override any of them before approving. If there are none, leave the list out. Stop.

## One-shot

**One-shot.** A ticket with `mode=one-shot` in `## Steering` has no spec gate: the grill and the owner's answers are its approval. One session grills every one-shot ticket of the plan, one after another, so the owner answers all grills in one place. The terms **one-shot ticket**, **stuck**, and **left to spec** are the ones in **One-shot** in `craft:next`. Do not post `🤖 Gate: spec`.

This session keeps only the rules, the plan document, and a **decision log**: two to four lines per specified ticket, as a blocker brief has. The heavy reading and writing for each ticket runs in fresh subagents, one at a time, so the session stays small and each spec gets a clean context. If the session was compacted, load `craft:rules` and `craft:spec` again before the next ticket.

1. **Start.** Read the one-shot plan ticket, the plan document, `GLOSSARY.md`, and `docs/adr/`. Build the decision log from the `## Spec` of each one-shot ticket that has one. Read the state from Linear, so a new session goes on where an earlier one stopped.
2. **Loop.** While a one-shot ticket is left to spec, take the first one in build order whose blockers are all in **Ready to build**, **Building**, **In Review**, or **Done**, skipping tickets with `mode=gated`. Move it to **Specifying**. When the next ticket can already be taken, move it to **Specifying** before the current one leaves **Specifying**, for any state. A gap does no harm: the loop's own `craft:next` calls run the build lane only. For each ticket:
   1. **Scout.** Start a fresh subagent on the `spec scout` model from `models.md`. Give it the ticket key, the plan document, and the decision log. It loads `craft:bstack`, reads the ticket with its comments, the code, and the docs, as steps 1 and 3 describe, and returns: the facts from the code; the open questions in the **What to ask** scope, each with a recommended answer and how sure it is; and the `(agent)` and `(default)` decisions it proposes.
   2. **Grill.** Ask the owner the open questions in rounds in chat, as step 3 describes, and follow **How sure you are**. If an answer opens a question that needs more facts, ask the scout again. Run `craft:design` in ticket mode here for a `ui` ticket, because design rounds need the owner.
   3. **Write.** Start a fresh subagent on the `spec writer` model from `models.md`. Give it the ticket key, the scout's facts, each question with the owner's answer word for word, the decisions, the gallery pages, and the decision log. It writes `## Spec` as step 5 describes, and returns the number of criteria, the `(default)` lines, and a decision log entry. The owner's answers win over any default it proposes.
   4. **Review.** Run the spec review in ticket scope, as `spec-review.md` describes, against the specs written so far. Post it on the ticket as step 6 says. Fix a FAIL in this session: ask the owner a problem that needs them as a grill round, and let the spec writer fix the spec. After the third FAIL, counted after the latest `🤖 resume:` comment, move the ticket to **Needs human**, send the Needs human notice from `craft:next`, and go on with the loop.
   5. **Replan.** Run the replan check from `craft:next` with this spec's decisions and domain docs, and follow its one-shot rule.
   6. **Ready.** Move the ticket to **Ready to build**. Comment `🤖 spec: success — <n> criteria (one-shot)`. Add its entry to the decision log. Send no chat message: the next grill round follows. Then run `craft:next` for the build lane only, which may start a build of this or another ticket. This call never starts a spec session or the plan-scope review.
3. **End.** When no one-shot ticket is left to spec, run `craft:next`. It runs the plan-scope review and, when the run is done, the done report. This session's work ends here.

## Done when

The ticket has a `## Spec` section and a `🤖 Gate: spec` comment, and the owner has been asked. For `mode=one-shot`, no one-shot ticket of the plan is left to spec, and each specified one is in **Ready to build** or **Needs human**. A `ui` ticket also has its gallery pages committed on its branch.

## After approval

See The gate in `craft:rules`. One approval covers the spec and the replan proposals.

1. Apply the replan proposals, as the replan check in `craft:next` describes.
2. Move the ticket to **Ready to build**. Comment `🤖 spec: success — <n> criteria`.
3. Run `craft:next`. It starts the build lane if this ticket or another one is ready, and starts the next grill in a new session. This session's work ends here.
