# The audit judges the process with a rubric per phase

This replaces `docs/adr/0008`.

`craft:audit` is one generic step that takes a rubric as input. There is one phase rubric per craft phase, starting with Review and Build, and the owner can add custom rubrics next to them. Each rubric asks whether its phase did its job, not whether the code is good. A low score names a phase and a skill to change, never a line of code to fix. The weekly run judges every rubric on every audited ticket, and writes one report.

A rubric item is a measure (a script scores it, with no AI judge), a check (a fresh audit judge answers a yes/no question and cites its evidence), or an escape (a later event, traced to the phase that should have caught it). An escape comes only from what happened after the ticket passed the phase: a fix PR within 14 days that changes the same files, or the owner's feedback at a gate.

Craft code is in the audit as far as it carries process logic: the hooks and the skill scripts, judged against the skill text and rules they serve. Craft's own tests and the repo CI are not.

Each rubric has a rubric version. Each change to it gets a new version, and the audit compares scores only within one version, so that a change of the rubric never looks like a change in the process. Rubrics are files in the craft plugin, custom rubrics too, so each change goes through craft and a release. A rubric holds only questions and craft terms, so it is safe in the public repo (`docs/adr/0009`).

We rejected the blind code audit of `docs/adr/0008`. It judged merged code against a code quality rubric, and that turned the audit into a code review, which the owner does not want (Theo, 2026-11-24). It was also the most expensive part of the audit. We also rejected a rotating deep dive: a theme the owner wants to look into becomes a custom rubric.
