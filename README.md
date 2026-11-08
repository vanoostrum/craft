# Sous

A software factory for AI-assisted software engineering.

Sous is a Claude Code plugin that runs software work for chef. It takes a Linear ticket through **spec → build → test → review → merge**, and stops at the pass for chef's approval: after the spec, and before the merge. A project that uses sous is a kitchen.

Before the tickets, sous can brainstorm an idea with chef into a brief (`sous:brainstorm`), and plan the brief into tickets (`sous:plan`).

## Kitchen terms

| Term | Meaning |
|---|---|
| sous | This plugin. It runs the work for chef. |
| the kitchen | A project that installs sous. |
| chef | The human who owns the kitchen. |
| the pass | The gates a ticket must clear: the plan pass, the spec pass, and the merge pass. |
| refire | Another try after a step fails. |
| ticket note | A `note=` argument on a ticket. |

The steps keep plain names: `sous:brainstorm`, `sous:plan`, `sous:spec`, `sous:design`, `sous:build`, `sous:review`, `sous:merge`, and `sous:next`. `sous:rules` holds the rules that every step loads first.

## Install

This repository is a plugin marketplace with two plugins: `sous`, and `pstack` pinned to the version that sous is tested with.

- **claude.ai project threads:** add the plugins to your account from GitHub, `vanoostrum/sous`. Threads load account plugins, but not a repository's `.claude/settings.json`.
- **Terminal and web sessions:** add the marketplace to the kitchen's `.claude/settings.json`, pinned to a tag:

  ```json
  "extraKnownMarketplaces": {
    "sous": { "source": { "source": "github", "repo": "vanoostrum/sous", "ref": "v1.2.0" } }
  },
  "enabledPlugins": { "sous@sous": true, "pstack@sous": true }
  ```

To upload transcripts to Google Cloud Storage, set `SOUS_GCS_BUCKET` in the cloud environment, and add a "GCP access token" network secret for `storage.googleapis.com`. See `plugins/sous/hooks/upload_transcripts.py`.

## A kitchen

A kitchen gives sous these things:

1. **`.claude/kitchen.md`**, imported from `CLAUDE.md` with `@.claude/kitchen.md`:

   ```markdown
   # Kitchen config

   | Key | Value |
   |---|---|
   | Linear team | `ABC` |
   | GitHub repo | `owner/repo` |
   | Base branch | `main` |
   | Required CI checks | `checks` |
   | Verify skill | `project-verify` |
   | App driver skill | `verify` |

   ## Standing notes

   Ticket notes that apply to every ticket.
   ```

2. **A verify skill** in `.claude/skills/`: install, lint, type check, and test, as the required CI checks do.
3. **An app driver skill** in `.claude/skills/`: launch the app, drive each entry point, save evidence and screenshots, and clean up, with a feature map.
4. **Engineering rules in `CLAUDE.md`**, including the test seam rule, and this line for the kitchen's own skills in project threads:

   > If a skill is unknown, read `.claude/skills/<name>/SKILL.md` and follow it.

5. **Fixed paths:** `GLOSSARY.md`, `docs/adr/`, and the design gallery in `design/`. `sous:design` creates the gallery on its first run.
6. **A Linear team** with the states Todo, Specifying, Ready to build, Building, In Review, Done, and Needs human, and the label `ui`.
7. **A GitHub repository** with the required checks on the base branch and "Automatically delete head branches" on.

## Development

- Fix sous here, not in a kitchen.
- Try a change on a live ticket with `claude --plugin-dir <this checkout>/plugins/sous` in a terminal session.
- Run the checks with `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, and `uv run pytest`.
- Release with a tag, and bump `ref` in each kitchen in its own PR.

`plugins/sous/VENDORED.md` lists the skills that come from other repositories.

## Possible new names

- workshop
