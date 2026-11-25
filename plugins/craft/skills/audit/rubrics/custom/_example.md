# Example rubric

Rubric version: 1
Phase: custom

A template for a custom rubric. Copy this file to `rubrics/custom/<name>.md`, with a name that does not start with `_`, and the weekly audit judges it next to the phase rubrics. `rubric=<name>` runs it on its own. The audit skips this file, because its name starts with `_`. The format is in **Rubric file** in the `craft:audit` skill.

## Items

### Spec decisions followed

Kind: Check
Reads: The ticket's `## Spec`, and the full review's PR comment.
Score: The share of tickets that pass.
Pass: The review names each decision in the spec's Decisions and says whether the PR follows it.
Partial: The review names some of the decisions.
Fail: The review names none of the decisions.
