# Models

Which model runs each part of sous and of pstack. Change a model here, in a PR to sous. Model names are the Claude Code family names: `opus`, `fable`, `sonnet`, `haiku`.

## Steps

Each `sous:*` step skill has the same model in its `model:` header, and Claude Code runs the step on it. A test fails CI when a header and this table differ.

| Step | Skill | Model |
|---|---|---|
| Brainstorm | `sous:brainstorm` | opus |
| Plan | `sous:plan` | opus |
| Spec | `sous:spec` | opus |
| Design | `sous:design` | opus |
| Build | `sous:build` | sonnet |
| Review | `sous:review` | opus |
| Merge | `sous:merge` | haiku |
| Next | `sous:next` | haiku |

## Subagents

A sous step starts each of these subagents with the model in this table.

| Subagent | Started by | Model |
|---|---|---|
| verify | `sous:build` | sonnet |
| app driver | `sous:build` | sonnet |
| CI polling and log reading | `sous:build` | haiku |
| fresh reviewer | `sous:review` | opus |
| brief reviewer | `sous:brainstorm` | opus |
| plan reviewer | `sous:plan` | opus |
| replan check | `sous:merge` | opus |

## pstack roles

pstack reads the lines below, in the format of its `setup-pstack` skill, once `sous:rules` has read this file into the session. `inherit-parent` runs the role on the model of the step that calls it. A panel role starts one subagent per list entry, and bstack asks before it starts more than one.

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
