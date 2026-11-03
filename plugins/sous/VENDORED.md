# Vendored skills

The skills in this table come from other repositories. The pstack skills are not vendored: the sous marketplace in `.claude-plugin/marketplace.json` lists the whole pstack plugin from [michael-denyer/pstack-claude](https://github.com/michael-denyer/pstack-claude), pinned to tag `v0.9.102`. Its skills carry the `pstack:` prefix. To update it, change the `ref` in `.claude-plugin/marketplace.json`. The `sous:bstack` skill limits pstack's subagent fan-out.

For each vendored skill, the first commit that added it is a literal copy. Later commits hold the local edits, so `git log -p -- <skill dir>` shows every change.

| Skill | Source | Commit | License |
|---|---|---|---|
| `grill-with-docs` | [mattpocock/skills](https://github.com/mattpocock/skills), `skills/engineering/` | `49dd158d1076134a641b33efb035946536778336` | MIT, Copyright (c) 2026 Matt Pocock |
| `domain-modeling` | [mattpocock/skills](https://github.com/mattpocock/skills), `skills/engineering/` | `49dd158d1076134a641b33efb035946536778336` | MIT, Copyright (c) 2026 Matt Pocock |
| `grilling` | [mattpocock/skills](https://github.com/mattpocock/skills), `skills/productivity/` | `49dd158d1076134a641b33efb035946536778336` | MIT, Copyright (c) 2026 Matt Pocock |

## Local edits

- `grill-with-docs`: removed `disable-model-invocation: true`, so `sous:spec` can call it.
- `grill-with-docs`: calls `sous:grilling` and `sous:domain-modeling`, the names these skills have in the plugin.
- `grill-with-docs`: the description says when to use it and no longer says the docs are written as the grill goes. The body says how the two skills combine and that the caller decides where the docs go.
- `domain-modeling`: the ADR conditions are listed only in `ADR-FORMAT.md`; `SKILL.md` links to them.

## Update a skill

1. Compare the pinned commit with the new upstream commit for the skill's directory.
2. Apply the upstream change. Keep the local edits.
3. Update the commit in this table.
