# Audit data stays in Linear

`vanoostrum/craft`, `vanoostrum/craft-console`, and `vanoostrum/librag` are public repos. So the audit keeps its scores, its findings, and anything from transcripts or from other projects' code in Linear only, in the audit report. The craft repo holds the core rubric and the skill changes. A proposal, and its ticket, spec, and PR, links the audit report and quotes only craft's own skill text and summary numbers, such as "0 of 41 reviews".

We rejected a scores file in the craft repo, which would have made the trend easy to diff, because it would publish findings about the code of other projects.
