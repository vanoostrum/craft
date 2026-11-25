# Audit data stays in Linear

`vanoostrum/craft`, `vanoostrum/craft-console`, and `vanoostrum/librag` are public repos. So the audit keeps its scores, its findings, and anything from transcripts or from other projects' code in Linear only: in the audit report, and in the ticket and spec of a proposal. A proposal ticket links the audit report, and its ticket and spec may describe the evidence behind it, with short examples, so that the spec writer knows what to fix. The craft repo holds the rubrics and the skill changes. A proposal's PR, its commits, and every file in the repo quote only craft's own skill text and summary numbers, such as "0 of 41 reviews". Here the PR means its title, its body, every comment on it (the review and the fix summaries too), and every commit.

The ticket title becomes the PR title, the branch name, and the squash commit title, so a proposal ticket's title names only the craft change, such as "Make `craft:review` check duplication": no findings, no files, and no project's code.

The build and review steps copy a spec into PR text, tests, and docs, so each proposal ticket carries a `note=` under `## Steering` that every step reads. The note says: the acceptance criteria name no findings; the examples stay in a separate section of the ticket that links the audit report; and the PR (title, body, every comment, every commit), the branch name, and every repo file, tests and fixtures too, quote only craft's skill text and summary numbers.

This loosens the brief's rule that a proposal's ticket and spec also quote only craft's skill text and numbers. Linear is private, and only the PR and the repo are public (Theo, 2026-11-23, at the plan gate).

We rejected a scores file in the craft repo, which would have made the trend easy to diff, because it would publish findings about the code of other projects.
