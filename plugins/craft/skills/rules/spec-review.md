# Spec review

A fresh agent reviews specs before the owner approves them, so the review is not biased by having written them. It runs on the `spec reviewer` model from `models.md`.

- **Ticket scope.** `craft:spec` runs it on one spec: before the spec gate in the gated flow, and before **Ready to build** in one-shot mode, against the specs written so far.
- **Plan scope.** `craft:next` runs it on all specs of a one-shot plan at once, after the last spec, as a last check.

The review follows `findings.md`: the first review of a spec is a full review, and each later one is a follow-up review.

The calling step gives the subagent only the ticket key or the plan ticket key, the scope, and the task below, copied word for word. For a follow-up review, it also gives the previous review and the fix summaries since it:
- **Ticket scope:** the `🤖 spec review:` comment and the `🤖 fix:` comments since it on the ticket. After a re-spec from a plan-scope FAIL, the previous review is the plan-scope review, and its findings on this ticket.
- **Plan scope:** the plan-scope `🤖 spec review:` comment on the plan ticket, and the fix summary of each ticket that went back to **Todo** since it.

## Task

> Load the `craft:bstack` skill first. Follow `findings.md` from `craft:rules`: a full review, or a follow-up review if you got a previous review. Read `GLOSSARY.md` and `docs/adr/` on the base branch, and the plan document, if the ticket came from a plan: the `Plan: <name>` document that the plan ticket links.
>
> - **Ticket scope:** the spec under review is the `## Spec` of the given ticket. The other specs are the `## Spec` of each other sub-issue of its plan ticket, of each other open ticket in its Linear project, and of the tickets that block it.
> - **Plan scope:** the specs under review are the `## Spec` of each sub-issue of the plan ticket that does not have `mode=gated`. The other specs are all of them.
>
> Check each spec under review on its own:
> - each acceptance criterion is testable, and a client can observe it at the test seam that the spec names;
> - each line under **Review focus** has a task in **Plan** that tests it;
> - each **Paths** row has an acceptance criterion that covers it, and each state change that the spec adds is a row;
> - the spec keeps the ticket's goal, its Consumes, Produces, and Constraints word for word, and the plan's decisions.
>
> Then check it against the other specs, as one system:
> - each name that a spec consumes is produced by a spec of a ticket it depends on, with the same name, fields, states, and errors; and each name it produces matches what a later spec consumes;
> - no two specs decide the same thing differently, such as a rule, a state, a limit, copy, or a glossary term, and no two **Domain docs** change the same term or ADR in different ways;
> - nothing falls between tickets: each step of each main flow in the plan is in the criteria of a spec, or of a ticket not yet specified, and no two specs build the same thing;
> - in plan scope, the specs together cover the plan's **Scope**, and nothing in its **Out of scope**;
> - where the flows of `ui` tickets meet, their gallery pages agree on navigation, names, and states.
>
> Report every finding at once, blocking or non-blocking, as `findings.md` says. For each one, name the tickets and the spec lines it concerns, and say whether the fix needs the owner: a question on behavior, UX, or an architecture choice against `docs/adr/`. Write the review with the `craft:clear-technical-prose` skill. End with the verdict line, with the counts, such as `PASS — 0 blocking, 2 non-blocking`.
