---
name: next
description: Craft picker. Pick the next Linear ticket for the spec lane and the build lane, and start both lanes in parallel. Also holds the replan check and the milestone checkpoint. Use after a plan gate, a spec gate, or a merge, or when the owner asks craft to pick up the next ticket.
model: haiku
---

# craft:next

Load the `craft:rules` skill first, and follow it.

Craft works in two lanes. The **spec lane** needs the owner: grill, design, and the spec gate. The **build lane** runs on its own: build, test, review, up to the merge gate. This skill picks the next ticket for each lane and starts the lanes in parallel, so the owner answers grills while earlier tickets build.

## Input

None, or a Linear project. Without a project, use every open ticket in the Linear team from the config.

## Lanes

| Lane | Takes a ticket when | Limit | Runs |
|---|---|---|---|
| Spec | It is in **Todo**, and each ticket that blocks it is in **Ready to build**, **Building**, **In Review**, or **Done**. | One ticket in **Specifying**, and at most 4 tickets in **Ready to build**. | `craft:spec`, in a new session for each ticket. |
| Build | It is in **Ready to build**, and each ticket that blocks it is **Done**. | One ticket in **Building**. A ticket in **In Review** does not count. | `craft:build`, then `craft:review`, in a new session. |

"Blocks" means a Linear "blocked by" relation. A blocked ticket is never picked. A ticket can be grilled before its blockers are built, because the grill needs their decisions, not their code.

## Steps

1. **Read the board.** List the open tickets with their state, priority, and blocking relations. Skip tickets in **Needs human** and plan tickets.
2. **Sort** the candidates of each lane by Linear priority, then by the build order in the plan ticket's `## Plan` table.
3. **Build lane.** If the lane has room and a ticket is ready, start a new Claude Code session for it with this prompt: `Run craft:build on <key>, then craft:review. Stop at the merge gate.` Use what the environment offers. In a claude.ai project, ask the coordinator for a new thread. In a terminal, run `claude -p "<prompt>"` in a background shell. A build must not run in a spec session, because the grill there waits on the owner.
4. **Spec lane.** If the lane has room and a ticket is ready, start a new Claude Code session for it, so that each grill starts with a fresh context. The new session reads `GLOSSARY.md` and `docs/adr/` for the shared conventions and decisions. It gets one more thing from this session: a blocker brief, of the tickets that this ticket depends on.
   - **Write the blocker brief.** For each ticket that blocks this ticket, read its `## Spec` and write two to four lines: the key and title, the goal, what it produces that this ticket consumes, and the decisions and domain docs that this ticket builds on. Leave out the rest. If no ticket blocks it, the blocker brief is `none`.
   - **Start the session** with this prompt: `Run craft:spec on <key>. Brief: <blocker brief>` In a claude.ai project, ask the coordinator for a new thread. In a terminal, a background shell cannot grill, so give the owner the command `claude "<prompt>"` to run in a new terminal.
   - Tell the owner in chat in one line that a grill is waiting, with the ticket link and where it runs.
5. **Nothing to pick.** If neither lane can take a ticket, say why in one line: what each lane waits on.

## One-shot

When the plan ticket's `## Steering` has `mode=one-shot`, run these phases for the tickets of its Linear project instead of the Steps above. **One-shot mode** in `craft:rules` gives the overview. A ticket with `mode=gated` takes no part in them.

Find the phase from the comments on the plan ticket:

| Plan ticket has | Phase |
|---|---|
| no approved `🤖 Gate: launch` | Spec phase. When it is done, the spec review, then the launch gate. |
| an approved `🤖 Gate: launch`, and no `🤖 one-shot:` comment | Build phase, or the done report when the build lane has nothing left |
| a `🤖 one-shot:` comment | None. Run the Steps above for the tickets with `mode=gated`. |

A launch gate counts as approved as The gate in `craft:rules` says, and only if no ticket went back to **Todo** after the approval.

1. **Spec phase.** Run the spec lane only. It has no limit on **Ready to build**, and takes one ticket in **Specifying** at a time, in build order, each in a new session as Spec lane in the Steps describes. The build lane takes no ticket yet. Each spec ends without a spec gate and runs `craft:next` again.
2. **Spec review.** When every ticket of the phase is in **Ready to build** or **Needs human**, run the spec review in plan scope, as `spec-review.md` from `craft:rules` describes. Give the subagent the plan ticket key.

   Post the review on the plan ticket as `🤖 spec review: <PASS or FAIL> — <one line>`, with the review below it. If it ends in FAIL, post each problem on each ticket it concerns as `🤖 spec review: <problem>`, and move those tickets back to **Todo**. The spec phase grills them again, and then this review runs again. That counts as a failed attempt for the plan ticket. After the third FAIL, do not move tickets to **Needs human**: go on to the launch gate, and list the open problems on it for the owner.
3. **Launch gate.** When the spec review ends in PASS, or after its third FAIL, check each **Owner first** item and each open **Up front** item that you can. Then post `🤖 Gate: launch` on the plan ticket with:
   - the link to the spec review, and its open problems, if any;
   - each ticket: key, title, number of criteria, and its `ui` pages;
   - every `(default)` decision of every spec, one line each, with its ticket;
   - the `🤖 replan: pending` comments on the plan ticket;
   - the owner actions that are still open, where to do each, and the value to use;
   - the paid services from **Up front**;
   - the tickets in **Needs human**, and what blocks each one; they and the tickets that depend on them are not built;
   - the gated tickets, which come after the done report;
   - "Do the open actions, then reply approve, or give feedback."

   In chat, ask for approval, by 👍 on the message or a reply "approve", with the plan ticket link, the number of tickets, the open owner actions, and the paid services, one line each. Stop. Feedback on a spec moves that ticket back to **Todo**: the spec phase grills it again, and then this gate comes again. After the approval, apply the approved replan proposals as **Replan check** step 6 says. If that moves a ticket back to **Todo**, the approval no longer counts: go back to the spec phase, and post this gate again when it is done.
4. **Build phase.** After the approval, run the build lane only, as in the Steps, one ticket in **Building** at a time. The session prompt is `Run craft:build on <key>, then craft:review and craft:merge. Do not stop at the merge gate.` A ticket in **Needs human** does not stop the phase: go on with the tickets that do not depend on it.
5. **Done report.** When the build lane has nothing left to take, post `🤖 one-shot: success — <n> tickets merged` on the plan ticket, or `🤖 one-shot: partial — <n> merged, <m> need you`. Tell the owner in chat, and send a push notification too if the environment has one:
   - what shipped, with the PR links and the app screenshots;
   - each ticket in **Needs human** or blocked by one, and what blocks it;
   - the `🤖 replan: pending` proposals from the build phase;
   - the **Owner after** items, with where to do each;
   - the gated tickets, if any.

   Move the plan ticket to **Done**. The tickets in **Needs human** stay open for the owner.

   Then run the Steps above for the gated tickets, with their spec gates and merge gates. If there are none, and the project has no `Brief: Staging and production` yet, offer `craft:setup deploy`. If the plan's input was a `Brief: Dev environment` that names a **Product brief**, and its walking skeleton is merged, start `craft:plan` on the product brief in a new session, as `craft:merge` step 8 does. Give it `mode=one-shot`: the owner still approves its plan gate.

The milestone checkpoint does not run in the one-shot phases. The done report covers it.

## Replan check

`craft:spec` runs this after the owner approves a spec. `craft:merge` runs it after a merge, in a subagent on the `replan check` model from `models.md`, because the merge step runs on a small model. It keeps the backlog in step with what craft has learned.

1. Read what is new: the decisions and domain docs of the approved spec, or the glossary terms, ADRs, and code of the merged PR.
2. Read the open tickets in the same Linear project, with their goals and gallery pages.
3. For each ticket that the new facts affect, propose one change: rewrite the goal, split, drop, add a ticket, change a blocker, or reorder. Do not propose details that the ticket's own grill will settle.
4. **Gallery pages.** For each open `ui` ticket, check its gallery pages against the new facts:
   - A change to the look lives in `design/gallery.css` or, from gallery stage 2, `design/components/`. Every page follows. Propose no redraw. Name the pages to look at again in their next screenshots.
   - A change to a screen, such as a field, a state, or the copy, does not follow on its own. Propose to mark the page stale. Do not redraw it now: `craft:design` redraws it when that ticket is grilled.
5. Post the proposals with the gate or the merge message, as the calling step says. They need the owner's approval. One approval covers the gate and the proposals. For a ticket with `mode=one-shot`, nobody waits: post each proposal on the plan ticket as `🤖 replan: pending — <proposal>`, for the launch gate or the done report. If a proposal shows that the spec of a ticket in **Ready to build** is wrong, also move that ticket to **Needs human** in the build phase, with the reason. In the spec phase, post a proposal for a ticket in **Todo** on that ticket too: its grill reads it.
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
