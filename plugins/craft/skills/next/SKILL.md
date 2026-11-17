---
name: next
description: Craft picker. Pick the next Linear ticket for the spec lane and the build lane, and start both lanes in parallel. Also holds the replan check and the milestone checkpoint. Use after a plan gate, a spec gate, or a merge, or when the owner asks craft to pick up the next ticket.
model: haiku
---

# craft:next

Load the `craft:rules` skill first, and follow it.

Craft works in two lanes. The **spec lane** needs the owner: grill, design, and the spec gate. The **build lane** runs on its own: build, test, review, up to the merge gate. This skill picks the next ticket for each lane and starts the lanes in parallel, so the owner answers grills while earlier tickets build.

## Input

None, or a plan ticket. Without one, use every open ticket in the Linear project from the config. With one, use its sub-issues. A ticket's plan is its parent plan ticket, and the plan document is the `Plan: <name>` document that the plan ticket links. A Linear project holds the tickets of several plans over time.

## Lanes

| Lane | Takes a ticket when | Limit | Runs |
|---|---|---|---|
| Spec | It is in **Todo**, and each ticket that blocks it is in **Ready to build**, **Building**, **In Review**, or **Done**. | One ticket in **Specifying**, and at most 4 tickets in **Ready to build**. | `craft:spec`, in a new session for each ticket. |
| Build | It is in **Ready to build**, and each ticket that blocks it is **Done**. | One ticket in **Building**. A ticket in **In Review** does not count. | `craft:build`, then `craft:review`, in a new session. |

"Blocks" means a Linear "blocked by" relation. A blocked ticket is never picked. A ticket can be grilled before its blockers are built, because the grill needs their decisions, not their code.

## Steps

1. **Read the board.** List the open tickets with their state, priority, blocking relations, and plan ticket. Skip tickets in **Needs human**, plan tickets, and the tickets without `mode=gated` of an open plan ticket with `mode=one-shot`: **One-shot** below runs those. The lane limits count only the tickets that this step does not skip, except that a one-shot ticket in **Building** counts toward the build lane limit of a gated ticket of the same plan.
2. **Sort** the candidates of each lane by Linear priority, then by plan, oldest plan ticket first, then by the build order in the table of the ticket's plan document.
3. **Build lane.** If the lane has room and a ticket is ready, start a new Claude Code session for it with this prompt: `Run craft:build on <key>, then craft:review. Stop at the merge gate.` Use what the environment offers. In a claude.ai project, ask the coordinator for a new thread. In a terminal, run `claude -p "<prompt>"` in a background shell. A build must not run in a spec session, because the grill there waits on the owner.
4. **Spec lane.** If the lane has room and a ticket is ready, start a new Claude Code session for it, so that each grill starts with a fresh context. The new session reads `GLOSSARY.md` and `docs/adr/` for the shared conventions and decisions. It gets one more thing from this session: a blocker brief, of the tickets that this ticket depends on.
   - **Write the blocker brief.** For each ticket that blocks this ticket, read its `## Spec` and write two to four lines: the key and title, the goal, what it produces that this ticket consumes, and the decisions and domain docs that this ticket builds on. Leave out the rest. If no ticket blocks it, the blocker brief is `none`.
   - **Start the session** with this prompt: `Run craft:spec on <key>. Brief: <blocker brief>` In a claude.ai project, ask the coordinator for a new thread. In a terminal, a background shell cannot grill, so give the owner the command `claude "<prompt>"` to run in a new terminal.
   - Tell the owner in chat in one line that a grill is waiting, with the ticket link and where it runs.
5. **Nothing to pick.** If neither lane can take a ticket, say why in one line: what each lane waits on.

## One-shot

For each open plan ticket whose `## Steering` has `mode=one-shot`, or for the plan ticket given as input if it has one, run these lanes for the sub-issues of that plan ticket, before the Steps above. **One-shot mode** in `craft:rules` gives the overview. There is no gate after the plan gate: the owner's grill answers are the approval of each spec.

Terms for this section:
- A **one-shot ticket** is a sub-issue of the plan ticket without `mode=gated`. A ticket with `mode=gated` takes no part in the lanes below.
- A one-shot ticket is **stuck** when it, or a ticket that blocks it, directly or through others, is in **Needs human**.
- A one-shot ticket is **left to spec** when it is in **Todo** or **Specifying** and is not stuck.
- Who called this step matters. `craft:plan`, `craft:spec`, and the owner can start the spec session and the plan-scope review. `craft:build`, `craft:review`, and `craft:merge` cannot.

Find the phase of the run from the comments on the plan ticket:

| Plan ticket has | Run |
|---|---|
| no `🤖 one-shot:` comment | **Resume**, then the spec lane, the build lane, the plan-scope review, and the done report, each when its condition holds |
| a `🤖 one-shot: partial` comment as its latest `🤖 one-shot:` comment | The same, while a one-shot ticket is neither **Done** nor stuck; and the Steps above for the tickets with `mode=gated` |
| a `🤖 one-shot: success` comment | None. Run the Steps above for the tickets with `mode=gated`. |

The lanes run at the same time, so each condition below reads the current state in Linear.

1. **Spec lane.** If a one-shot ticket is left to spec and none is in **Specifying**, and this step was called by `craft:plan` after the plan gate, by `craft:spec` at the end of its loop, after a plan-scope FAIL, or on the owner's request, start one new Claude Code session with the prompt `Run craft:spec on the one-shot plan <plan key>.` In a claude.ai project, ask the coordinator for a new thread; in a terminal, give the owner the command `claude "<prompt>"`. Tell the owner in chat in one line that the grills are waiting, and where. That session grills every ticket left to spec, one after another. `craft:next` from `craft:build`, `craft:review`, or `craft:merge` never starts it. The call that a running spec session makes after each ticket runs the build lane only, so it never starts a second session either.
2. **Build lane.** Run it at the same time as the spec lane: start a build for a one-shot ticket in **Ready to build** whose spec passed review, as step 1 of `craft:build` says, and whose blockers are all **Done**. Keep one ticket of the plan in **Building**, gated or not; the limit is shared in both directions, so the gated build lane in the Steps also counts the one-shot tickets of the same plan in **Building**. Pick in build order. Start a new session with the prompt `Run craft:build on <key>, then craft:review and craft:merge. Do not stop at the merge gate.`, as Build lane in the Steps describes. `craft:build` claims the ticket first, so two calls cannot build it twice.
3. **Plan-scope review.** Only `craft:next` run from `craft:spec`, or on the owner's request, runs it, when no one-shot ticket is left to spec, and no plan-scope `🤖 spec review:` comment on the plan ticket is newer than the latest `🤖 spec: success` of its tickets. Run it in plan scope, as `spec-review.md` from `craft:rules` describes. Give the subagent the plan ticket key.

   Post the review on the plan ticket as `🤖 spec review: <PASS or FAIL> — <one line>`, with the review below it. If it ends in FAIL, move each ticket with a problem that is not yet in **Building** back to **Todo**, and post its problem as `🤖 spec review: <problem>` only on the tickets that go back to **Todo**. Then start a new spec session as the spec lane says: it grills them again, and this review runs again when it ends. A problem in a ticket in **Building** or later goes only on the plan ticket, as a `🤖 replan: pending` proposal for the done report, so it never reads as that ticket's latest spec review. A FAIL counts as a failed attempt for the plan ticket, counted after the latest `🤖 resume:` comment. After the fifth FAIL, move the unbuilt tickets with open problems to **Needs human**, send the Needs human notice, and list the open problems in the done report.
4. **Needs human notice.** Each time a one-shot ticket moves to **Needs human**, in either lane, the step that moves it tells the owner at once in chat, and with a push notification if the environment has one: the ticket, what blocks it, what the owner must do and where, and the tickets that now wait behind it. It ends with: reply "fixed" in this chat when it is done. It also says that a comment or a state change in Linear counts too, but waits for the next `craft:next` run, or for "resume" in chat, because craft does not watch Linear.
5. **Resume.** Any craft session that gets "fixed" or "resume" from the owner first writes the owner's words as a comment on the ticket it concerns, then runs `craft:next` on the plan ticket. A "fixed" that names no ticket concerns every Needs human ticket of the plan whose block the owner can fix, or the session asks which one. `craft:next` resumes a one-shot ticket in **Needs human** with an owner reply or comment newer than its move there, and a one-shot ticket that the owner moved out of **Needs human**:
   - **Owner first** items, or failed build, review, or merge attempts: move it to **Ready to build**.
   - A stale spec, a spec review FAIL, or a replan: move it to **Todo**.
   - A state that the owner set is kept.

   Post `🤖 resume: <cause> → <state>` on the ticket and on the plan ticket. The ticket's attempt counts, the plan-scope FAIL count, and the no-repeat check of the done report all start after the latest `🤖 resume:` comment. The ticket and the tickets behind it rejoin the lanes with no gates.
6. **Done report.** Post it when every one-shot ticket is **Done** or stuck, the latest plan-scope `🤖 spec review:` is newer than the latest `🤖 spec: success` and ends in PASS or is the fifth FAIL, and no `🤖 one-shot:` comment is newer than the latest `🤖 resume:` comment or state change of a one-shot ticket, so it is never repeated. Post `🤖 one-shot: success — <n> tickets merged` on the plan ticket, or `🤖 one-shot: partial — <n> merged, <m> need you`. Tell the owner in chat, and send a push notification too if the environment has one:
   - what shipped, with the PR links and the app screenshots;
   - each ticket in **Needs human** or stuck behind one, and what blocks it;
   - every `(default)` decision of every spec, one line each, with its ticket;
   - the `🤖 replan: pending` proposals;
   - the **Owner after** items, with where to do each;
   - the gated tickets, if any.

   After `🤖 one-shot: success`, move the plan ticket to **Done**. After `🤖 one-shot: partial`, the plan ticket stays open, so a resumed ticket continues the run, and the tickets in **Needs human** stay open for the owner.

   After the first done report, run the Steps above for the gated tickets, with their spec gates and merge gates. If there are none, and the project has no `Brief: Staging and production` yet, offer `craft:setup deploy`.

The milestone checkpoint does not run in the one-shot lanes. The done report covers it.

**Plans from before craft 2.8.** A one-shot plan ticket can still have a `🤖 Gate: launch`. Its tickets build if it is approved, as The gate in `craft:rules` says, and no ticket went back to **Todo** after the approval. An unapproved one counts too, unless the owner commented after it: such feedback on a spec moves that ticket back to **Todo**, and the spec lane grills it again. A ticket from such a plan that is left to spec is grilled by the spec lane as usual.

## Replan check

`craft:spec` runs this after the owner approves a spec. `craft:merge` runs it after a merge, in a subagent on the `replan check` model from `models.md`, because the merge step runs on a small model. It keeps the backlog in step with what craft has learned.

1. Read what is new: the decisions and domain docs of the approved spec, or the glossary terms, ADRs, and code of the merged PR.
2. Read the open tickets in the same Linear project, with their goals and gallery pages.
3. For each ticket that the new facts affect, propose one change: rewrite the goal, split, drop, add a ticket, change a blocker, or reorder. Do not propose details that the ticket's own grill will settle.
4. **Gallery pages.** For each open `ui` ticket, check its gallery pages against the new facts:
   - A change to the look lives in `design/gallery.css` or, from gallery stage 2, `design/components/`. Every page follows. Propose no redraw. Name the pages to look at again in their next screenshots.
   - A change to a screen, such as a field, a state, or the copy, does not follow on its own. Propose to mark the page stale. Do not redraw it now: `craft:design` redraws it when that ticket is grilled.
5. Post the proposals with the gate or the merge message, as the calling step says. They need the owner's approval. One approval covers the gate and the proposals. For a ticket with `mode=one-shot`, nobody waits, and the same rule holds from a spec or a merge. A proposal that shows that the spec of a ticket in **Ready to build** is wrong moves that ticket back to **Todo**, with the proposal as a comment, while a one-shot ticket is left to spec, so the running spec session grills it again. After that, it moves the ticket to **Needs human**, with the reason and the Needs human notice. A proposal for a ticket in **Todo** goes on that ticket: its grill reads it. Post every other proposal on the plan ticket as `🤖 replan: pending — <proposal>`, for the done report.
6. **After approval**, apply each change in Linear. Mark a stale page with a ticket comment `🤖 replan: stale <page> — <the decision that changed it>`. A change to a ticket in **Ready to build** moves it back to **Todo**, so the spec lane grills it again.
7. Comment on each changed ticket `🤖 replan: success — <one line>`.

If nothing is affected, say "No replan changes" in the gate or merge message.

## Milestone checkpoint

`craft:merge` runs this when the merged ticket was the last open ticket of a Linear milestone.

1. Post on the plan ticket, and tell the owner in chat: what shipped in the milestone, with links to the PRs and the app screenshots, and the decisions made.
2. Ask the owner to reorder the priorities in Linear if needed. For a bigger change of direction, offer `craft:plan` for the next increment. If the project has no `Brief: Staging and production` yet, ask whether this milestone is v1, the version for real users, and if so offer `craft:setup deploy`.
3. Run the Steps above only after the owner replies.

## Done when

Each lane has a ticket, or the owner knows what each lane waits on.
