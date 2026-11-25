# Review rubric

Rubric version: 1
Phase: review
Applies to: tickets with a spec

Did craft's review phase do its job? The review phase is `craft:review`: a fresh reviewer checks a PR against its spec, and posts its review as a PR comment that ends with a verdict line. The audit judges how the review worked, never the code (`docs/adr/0010`). The per-ticket checks judge the full review, the first review of the PR. Follow-up reviews count only in Findings rounds.

## Items

### Read in context

Kind: Check
Reads: The full review's transcript digest.
Score: The share of tickets that pass.
Pass: The reviewer opened the changed files in full and ran or read the tests, not only the diff.
Partial: The reviewer did one of these: it opened the changed files in full, or it ran or read the tests.
Fail: The reviewer read only the diff.

### Criteria evidence

Kind: Check
Reads: The full review's PR comment, and the ticket's `## Spec`.
Score: The share of tickets that pass.
Pass: Every acceptance criterion has met or not met, with evidence: a test name, or a file and line.
Partial: Every acceptance criterion has met or not met, but some have no evidence.
Fail: Some acceptance criteria have no answer.

### Design and maintainability

Kind: Check
Reads: The full review's transcript digest and PR comment.
Score: The share of tickets that pass. The question is: "Did the review look at design and maintainability, as the project's rules ask?" The judge answers from what the reviewer did and wrote. It does not judge the code itself.
Pass: The reviewer looked at structure, duplication, and fit with the existing code.
Partial: The reviewer looked at one or two of structure, duplication, and fit with the existing code.
Fail: The review checked only the criteria.

### Findings rounds

Kind: Measure
Reads: The PR's issue comments, from `gh api repos/<repo>/issues/<n>/comments`.
Score: `scripts/rounds.py` prints two values: Rounds until PASS, the review rounds up to the first PASS, and Blocking per round, the blocking findings per round. Each is a median per craft version. A PR with verdict lines but no PASS gets its count of verdict lines and "no PASS". A PR with no verdict line, such as a review from before craft 2.9.0, is "no data".

### Process logic

Kind: Check
Per: craft version
Reads: At the release tag `v<version>` of `vanoostrum/craft`: the hooks `plugins/craft/hooks/one_step_per_session.py` and `plugins/craft/hooks/require_bstack.py`, and the rules `plugins/craft/skills/review/SKILL.md`, `plugins/craft/skills/rules/findings.md`, and `plugins/craft/skills/rules/SKILL.md`.
Score: Judged once per craft version, and shown next to the phase score, not in it. The question is: do the hooks that gate a review session do what the review rules say? A hook rule is a rule in these files that names a hook, or says that craft blocks or denies something. Behavior in a case that the rule does not name does not change the result: another way to load the same skill, a stricter reset, a command that the owner typed, or an allow when the hook cannot read its input, such as a missing transcript. `hooks/upload_transcripts.py` also runs in a review session, but it records metrics and carries no review rule, so it is not in this check. The review skill has no scripts.
Pass: Each hook rule has a hook that enforces it in every case the rule names, and no hook blocks what a rule asks for.
Partial: Each hook rule has a hook, and no hook blocks what a rule asks for, but at least one hook lets through a case that its rule names.
Fail: A hook rule has no hook that enforces it, or a hook blocks what a rule asks for.
