# Build rubric

Rubric version: 1
Phase: build
Applies to: tickets with a spec

Did craft's build phase do its job? The build phase is `craft:build`: it builds a PR from its approved spec, with tests first, runs the verify skill, proves the change in the running app with the app driver, and waits for CI. The audit judges how the build worked (`docs/adr/0010`). An item's `Reads:` line sets what the judge must get and judge. The judge may read any other code as evidence, such as the PR diff or the repository at the PR's merge commit, but it never scores the code on its own and never proposes a fix to the code. The per-ticket checks judge every build segment of the ticket, retries and fixes after a review FAIL too.

## Items

### Tests first

Kind: Check
Reads: The build digest, and the PR's commit list with each commit's SHA, message, and time.
Score: The share of tickets that pass.
Pass: For each task in the spec's **Plan** that changes code, the build wrote a test and ran it, and saw it fail, before it wrote the code.
Partial: The tests came before the code, but the build did not run them and see them fail first, or this holds for some tasks and not for others.
Fail: For a task, the code came before its tests, or the build added the tests after the code worked.

### Tests check behavior

Kind: Check
Reads: The test-file diff, the test seam rule in the project's `CLAUDE.md`, and the spec's **Testing decisions**.
Score: The share of tickets that pass. The question is: did the build follow the test seam rule? The judge does not judge whether the code is good. A PR that changes no test file gets the line `no test files changed`, and the judge judges that against the spec's **Testing decisions**.
Pass: The tests connect at the seam that the spec names, and assert what a user or client sees, so they fail when that behavior breaks.
Partial: Some tests sit below the seam with no reason that the seam rule allows, or check internals.
Fail: Most new tests check internals, or the change has no test for the behavior it adds and the spec gives no reason.

### Tests not bent

Kind: Check
Reads: The build digest, and the test-file diff.
Score: The share of tickets that pass.
Pass: No test changed after it failed, or each such change follows from the spec or a review finding.
Partial: A test changed after it failed, with a reason in the transcript that the spec or a finding does not give.
Fail: A test was changed, skipped, or deleted to match code that broke it, with no reason.

### App evidence

Kind: Check
Reads: The PR body's **App evidence**, the titles of the ticket's Linear attachments, and the app driver's part of the build digest.
Score: The share of tickets that pass.
Pass: Each entry point that the ticket adds or changes has output from the running app, and that output matches what the app driver's tool calls returned.
Partial: Some entry points have such output, or some evidence comes from tests instead of the running app.
Fail: There is no app evidence, or there is evidence that the app driver's tool calls did not return.

### Environment failures

Kind: Check
Reads: The build digest.
Score: The share of tickets that pass. An environment failure is a verify, app driver, or CI failure that the change did not cause, such as a flaky test, a missing tool, a network block, or a CI runner problem. A script cannot tell it from a failure that the change caused, so the judge decides, and cites each failure.
Pass: No verify, app driver, or CI failure came from the environment.
Partial: The build hit an environment failure and recovered on its own, with no failed attempt.
Fail: An environment failure cost a failed attempt, or stopped the build.

### Attempts

Kind: Measure
Reads: The ticket's Linear comments, the check runs on the PR's commits, and the ticket's build segments.
Score: `scripts/build.py` attempts prints three values, each a median per craft version: Failed attempts, the `🤖 build: retry` comments; CI reds, the failed or timed-out runs of a required CI check; and Work minutes, the `work_seconds` of the build segments, in minutes. With no build segment, Work minutes is no data.

### Feedback speed

Kind: Measure
Reads: The subagents of the ticket's build segments, and the check runs on the PR's commits.
Score: `scripts/build.py` speed prints two values, each a median per craft version: Verify minutes, the median duration of the build's verify subagents, and CI minutes, the median duration of the completed runs of the required CI checks. A value with no run is no data.

### Process logic

Kind: Check
Per: craft version
Reads: At the release tag `v<version>` of `vanoostrum/craft`: the hooks `plugins/craft/hooks/one_step_per_session.py` and `plugins/craft/hooks/require_bstack.py`, the script `plugins/craft/skills/rules/scripts/gallery-shot`, and the rules `plugins/craft/skills/build/SKILL.md`, `plugins/craft/skills/rules/SKILL.md`, and `plugins/craft/skills/rules/gallery.md`.
Score: Judged once per craft version, and shown next to the phase score, not in it. The question is: do the hooks that gate a build session, and the script that the build runs, do what the build rules say? A hook or script rule is a rule in these files that names a hook or the script, or says that craft blocks or denies something. Behavior in a case that the rule does not name does not change the result: another way to load the same skill, a stricter reset, a command that the owner typed, or an allow when the hook cannot read its input, such as a missing transcript. `hooks/upload_transcripts.py` also runs in a build session, but it records metrics and carries no build rule, so it is not in this check.
Pass: Each hook or script rule has a hook or script that enforces it in every case the rule names, and no hook or script blocks what a rule asks for.
Partial: Each hook or script rule has a hook or script, and no hook or script blocks what a rule asks for, but at least one hook or script lets through a case that its rule names.
Fail: A hook or script rule has no hook or script that enforces it, or a hook or script blocks what a rule asks for.
