# Engineering rules in three layers, loaded by each step

The engineering rules are the written rules that the code of a project must follow. They come in three layers:

- the **shared rules**, in the craft plugin at `plugins/craft/skills/rules/engineering.md`, for every project;
- one **stack profile** per stack, in the craft plugin at `plugins/craft/skills/rules/profiles/<stack>.md`: `python-fastapi`, `nextjs`, `nestjs`, `swift-ios`, and `kotlin-android`;
- the **project rules**, in the project's repo at `docs/engineering.md`: the project's own choices, each linked to the ADR, the `CLAUDE.md` line, or the code behind it.

The project rules win over the profile, and the profile wins over the shared rules. The `Stacks` key in `.claude/craft.md` names the profile of each path of the repo, so a repo with two stacks works now, and a project with more than one repo fits later.

`craft:spec`, `craft:build`, and `craft:review` each read all three layers explicitly, before they write or judge anything. Spec raises a conflict between a ticket and a rule in the grill, build follows the rules before it writes code, and review checks the code against the same text. No rule is hidden until the review.

A rule earns its place only when it is a choice between valid options that the model cannot guess, or something that agents get wrong although they know better. Well-known practice is named in one line, not restated. The main reader of the code is the next agent.

We chose profiles in the plugin and project choices in the repo (Theo, 2026-11-26, brief "Technical code review"). One fix to a profile reaches every project at the next release, and the audit, which proposes fixes to craft only, can propose profile fixes. We rejected a template copied into each repo at setup, because a lesson from one project never reaches the others and the copies drift apart. We rejected rules written from scratch for each repo, because nothing is reused. We do not use `.claude/rules/`: project threads start Claude Code without repo settings, so the rules would not load by themselves.
