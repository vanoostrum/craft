# Craft

A software factory for AI-assisted software engineering.

Craft is a Claude Code plugin that runs software work for the owner. It takes a Linear ticket through **spec → build → test → review → merge**, and stops at a gate for the owner's approval: after the spec, and before the merge.

Before the tickets, craft can brainstorm an idea with the owner into a brief (`craft:brainstorm`), and plan the brief into tickets (`craft:plan`).

## Terms

| Term | Meaning |
|---|---|
| craft | This plugin. It runs the work for the owner. |
| the project | A repository that installs craft. |
| the owner | The human who owns the project. |
| gate | A point where a ticket stops for the owner's approval: the plan gate, the spec gate, and the merge gate. |
| retry | Another try after a step fails. |
| note | A `note=` argument on a ticket. |

The steps keep plain names: `craft:brainstorm`, `craft:plan`, `craft:spec`, `craft:design`, `craft:build`, `craft:review`, `craft:merge`, and `craft:next`. `craft:rules` holds the rules that every step loads first.

## Install

This repository is a plugin marketplace with two plugins: `craft`, and `pstack` pinned to the version that craft is tested with.

- **claude.ai project threads:** add the plugins to your account from GitHub, `vanoostrum/craft`. Threads load account plugins, but not a repository's `.claude/settings.json`.
- **Terminal and web sessions:** add the marketplace to the project's `.claude/settings.json`, pinned to a tag:

  ```json
  "extraKnownMarketplaces": {
    "craft": { "source": { "source": "github", "repo": "vanoostrum/craft", "ref": "v2.0.0" } }
  },
  "enabledPlugins": { "craft@craft": true, "pstack@craft": true }
  ```

To upload transcripts to Google Cloud Storage, set `CRAFT_GCS_BUCKET` in the cloud environment, and add a "GCP access token" network secret for `storage.googleapis.com`. See `plugins/craft/hooks/upload_transcripts.py`.

## Set up a project

A project gives craft these things:

1. **`.claude/craft.md`**, imported from `CLAUDE.md` with `@.claude/craft.md`:

   ```markdown
   # Project config

   | Key | Value |
   |---|---|
   | Linear team | `ABC` |
   | GitHub repo | `owner/repo` |
   | Base branch | `main` |
   | Required CI checks | `checks` |
   | Verify skill | `project-verify` |
   | App driver skill | `verify` |

   ## Standing notes

   Notes that apply to every ticket.
   ```

2. **A verify skill** in `.claude/skills/`: install, lint, type check, and test, as the required CI checks do.
3. **An app driver skill** in `.claude/skills/`: launch the app, drive each entry point, save evidence and screenshots, and clean up, with a feature map.
4. **Engineering rules in `CLAUDE.md`**, including the test seam rule, and this line for the project's own skills in project threads:

   > If a skill is unknown, read `.claude/skills/<name>/SKILL.md` and follow it.

5. **Fixed paths:** `GLOSSARY.md`, `docs/adr/`, and the design gallery in `design/`. `craft:design` creates the gallery on its first run.
6. **A Linear team** with the states Todo, Specifying, Ready to build, Building, In Review, Done, and Needs human, and the label `ui`.
7. **A GitHub repository** with the required checks on the base branch and "Automatically delete head branches" on.

## Development

- Fix craft here, not in a project.
- Try a change on a live ticket with `claude --plugin-dir <this checkout>/plugins/craft` in a terminal session.
- Run the checks with `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, and `uv run pytest`.
- Release with a tag, and bump `ref` in each project in its own PR.

`plugins/craft/VENDORED.md` lists the skills that come from other repositories.
