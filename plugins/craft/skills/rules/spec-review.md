# Spec review

A fresh agent reviews specs before the owner approves them, so the review is not biased by having written them. It runs on the `spec reviewer` model from `models.md`.

- **Ticket scope.** `craft:spec` runs it on one spec, before the spec gate, in the gated flow.
- **Plan scope.** `craft:next` runs it on all specs of a one-shot plan at once, before the launch gate.

The calling step gives the subagent only the ticket key or the plan ticket key, the scope, and the task below, copied word for word.

## Task

> Load the `craft:bstack` skill first. Read `GLOSSARY.md` and `docs/adr/` on the base branch, and the `## Plan` of the plan ticket, if the ticket came from a plan.
>
> - **Ticket scope:** the spec under review is the `## Spec` of the given ticket. The other specs are the `## Spec` of each other ticket in its Linear project that has one, and the specs of the tickets that block it.
> - **Plan scope:** the specs under review are the `## Spec` of each ticket in the plan's Linear project that does not have `mode=gated`. The other specs are all of them.
>
> Check each spec under review on its own:
> - each acceptance criterion is testable, and a client can observe it at the test seam that the spec names;
> - each line under **Review focus** has a task in **Plan** that tests it;
> - the spec keeps the ticket's goal, its Consumes, Produces, and Constraints word for word, and the plan's decisions.
>
> Then check it against the other specs, as one system:
> - each name that a spec consumes is produced by a spec of a ticket it depends on, with the same name, fields, states, and errors; and each name it produces matches what a later spec consumes;
> - no two specs decide the same thing differently, such as a rule, a state, a limit, copy, or a glossary term, and no two **Domain docs** change the same term or ADR in different ways;
> - nothing falls between tickets: each step of each main flow in the plan is in the criteria of a spec, or of a ticket not yet specified, and no two specs build the same thing;
> - in plan scope, the specs together cover the plan's **Scope**, and nothing in its **Out of scope**;
> - where the flows of `ui` tickets meet, their gallery pages agree on navigation, names, and states.
>
> List real problems only. For each one, name the tickets and the spec lines it concerns, and say whether the fix needs the owner: a question on behavior, UX, or an architecture choice against `docs/adr/`. Write the review with the `craft:clear-technical-prose` skill. End with PASS or FAIL.
