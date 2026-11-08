# Models

Which model runs each part of craft and of pstack. Change a model here, in a PR to craft. Model names are the Claude Code family names: `opus`, `fable`, `sonnet`, `haiku`.

## Steps

Each `craft:*` step skill has the same model in its `model:` header, and Claude Code runs the step on it. A test fails CI when a header and this table differ.

| Step | Skill | Model |
|---|---|---|
| Brainstorm | `craft:brainstorm` | opus |
| Plan | `craft:plan` | opus |
| Spec | `craft:spec` | opus |
| Design | `craft:design` | opus |
| Build | `craft:build` | sonnet |
| Review | `craft:review` | opus |
| Merge | `craft:merge` | haiku |
| Next | `craft:next` | haiku |

## Subagents

A craft step starts each of these subagents with the model in this table.

| Subagent | Started by | Model |
|---|---|---|
| verify | `craft:build` | sonnet |
| app driver | `craft:build` | sonnet |
| CI polling and log reading | `craft:build` | haiku |
| fresh reviewer | `craft:review` | opus |
| brief reviewer | `craft:brainstorm` | opus |
| plan reviewer | `craft:plan` | opus |
| replan check | `craft:merge` | opus |

## pstack roles

pstack reads the lines below, in the format of its `setup-pstack` skill, once `craft:rules` has read this file into the session. `inherit-parent` runs the role on the model of the step that calls it. A panel role starts one subagent per list entry, and bstack asks before it starts more than one.

feature, refactoring: inherit-parent
bug-fix: inherit-parent
perf-issue: inherit-parent
hillclimb: inherit-parent
judgment and prose: inherit-parent
strongest judgment: inherit-parent
how explorer: inherit-parent
how explainer: inherit-parent
why investigators: inherit-parent
why synthesizer: inherit-parent
reflect tooling: inherit-parent
reflect judgment, divergent, synthesizer: inherit-parent
arena runners: opus, sonnet
arena cross-judge pool: opus, sonnet
swarm workers: inherit-parent
architect runners: opus, sonnet
interrogate reviewers: opus, sonnet

default effort: session
