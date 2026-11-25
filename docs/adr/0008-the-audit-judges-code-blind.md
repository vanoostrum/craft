# The audit judges code blind, with a versioned rubric

Superseded by `docs/adr/0010`: the audit judges the craft process with a rubric per phase, and has no blind code audit.

`craft:audit` judges merged PRs in a blind auditor that sees only the merged code, the project's own conventions, and the core rubric. It does not see the spec, craft's review, or the transcripts. A reviewer that reads what craft wrote inherits craft's blind spots, and the audit exists to find them. The transcripts are read only later, in the trace back, for the findings that craft's review missed.

The core rubric has a rubric version. Each change to it gets a new version, and the audit compares scores only within one version, so that a change of the rubric never looks like a change in code quality. A deep dive can propose an addition to the rubric, and that proposal goes through craft like any other change.

We rejected adding the rubric to `craft:review` first, because then craft grades its own work and there is no baseline to measure the change against. That change becomes a proposal that the audit measures.
