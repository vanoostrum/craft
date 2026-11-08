---
name: bstack
description: >-
  Budget overlay on pstack Poteto Mode. Keeps Poteto playbook routing and
  engineering behavior, but minimizes multi-agent fan-out. Requires explicit
  user approval before 2+ subagents are used for one goal. Load it before any
  pstack skill; a hook blocks pstack skills until it is loaded.
---

# bstack

Budget overlay on pstack. Keep the plugin. Do not edit it.

## Non-negotiables

Read the installed **poteto-mode** skill. Follow its playbook matching,
principles, engineering steps, and verification behavior. If it is not
installed, say so and work without pstack; in a craft step, follow the pstack
rule in `craft:rules`.

Prefer the parent agent. One focused helper subagent is allowed when useful.

Never create a cluster of **2+ subagents working toward the same goal** without
explicit user approval immediately beforehand.

This includes multiple explorers, architecture candidates, Arena,
multi-reviewer Interrogate, Swarm, and equivalent fan-out.

Before creating a cluster, state:

* why multiple agents materially help
* exact number of agents
* their roles
* that token usage will increase

Then ask for approval and stop.

Approval applies only to that specific cluster. Do not reuse earlier approval.

## In a craft step

Craft runs without the owner between the gates, so a question stalls the
ticket. Inside a `craft:*` step:

* Never create a cluster. Do not ask for one either: use the parent agent or
  one focused helper, and go on.
* The single-purpose subagents that the craft steps name (verify, app driver,
  CI polling, fresh reviewer, replan check) are not a cluster. Each one has its
  own goal.
* In a grill, look up facts with one sub-agent at a time, not one per fact
  in parallel.
* If a cluster would clearly change the result, say so in the step's Linear
  comment, so the owner can ask for it at the next gate.

## Writing

For every text a human reads (chat messages, Linear comments, specs, PR bodies,
review comments, commit messages, docs), use the
`craft:clear-technical-prose` skill. Do not load pstack's `technical-writing` or
`unslop` for these texts, even where poteto-mode says to. Two style guides for
one text cost tokens and conflict.

## Budget routing

When Poteto would fan out, first try to compress the work:

| Poteto behavior                   | bstack default                        |
| --------------------------------- | ------------------------------------- |
| Multiple `/how` explorers         | Parent agent or 1 explorer            |
| Architecture panel                | Parent agent or 1 architecture helper |
| `/arena`                          | Ask before running                    |
| Multiple `/interrogate` reviewers | Parent review or 1 reviewer           |
| `/swarm`                          | Ask before running                    |
| Full multi-agent orchestration    | Ask before running                    |

Do not use extra agents merely for confidence or generic second opinions.

Keep repository context tight: search first, read minimal relevant slices, and
stop exploring once the implementation is clear.

Do not reduce verification quality to save tokens. Prefer concrete checks and
runtime evidence over additional model opinions.

## Examples

If one explorer can trace an unclear runtime path, use one.

If Poteto wants 3 architecture candidates:

> This would benefit from 3 architecture agents comparing the viable designs.
> That will increase token usage. Approve the 3-agent panel?

If approval is declined, continue with the parent agent or one focused helper.
