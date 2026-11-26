# Technical findings block only on written rules

The build review has two parts. The **functional** part checks that the PR does what the spec says. The **technical** part checks the code against the engineering rules (`docs/adr/0011`). One fresh reviewer writes both parts, so it reads the files once.

Each finding keeps one of the two severities, blocking or non-blocking, and also gets one label:

- `spec`: a functional finding. Blocking.
- `rule`: a written rule is broken, a metric is over its threshold, or the PR adds a new duplicate of existing code. The finding names the rule. Blocking.
- `lens`: a judgement call, named by a smell or a principle. Non-blocking.
- `lesson`: a rule candidate, marked `project` or `stack`. It comes only from a blocking technical finding or from technical owner feedback at the merge gate. The owner approves its wording at the merge gate before it is written.

Tools measure complexity, CRAP, duplication, and file length in each project's verify skill and CI, as a metric report that compares the base and the head of the PR. The report adds no required check. The reviewer judges the change: a PR must not push a function or a file that it touches over a threshold. Excess that the PR did not cause is for the codebase review.

We chose to block only on written rules (Theo, 2026-11-26, brief "Technical code review"). Rules grow from the owner's decisions, not from the reviewer's taste. We rejected blocking on every technical finding, because judgement calls vary between runs and add rounds. We rejected a technical part that never blocks, because that is the review of today, and the drift goes on. We rejected a severity scale such as major, minor, and nit: the labels say what kind of finding it is, and blocking says what it does to the review.
