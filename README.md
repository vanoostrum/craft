# Craft

A software factory for AI-assisted software engineering.

Craft is a Claude Code plugin that runs software work for the owner. It takes a Linear ticket through **spec → build → test → review → merge**, and stops at a gate for the owner's approval: after the spec, and before the merge.

Before the tickets, craft can brainstorm an idea with the owner into a brief (`craft:brainstorm`), describe the project's environments into a brief (`craft:setup`), and plan a brief into tickets (`craft:plan`).

## Terms

| Term | Meaning |
|---|---|
| craft | This plugin. It runs the work for the owner. |
| the project | A repository that installs craft. |
| the owner | The human who owns the project. |
| gate | A point where a ticket stops for the owner's approval: the plan gate, the spec gate, and the merge gate. |
| retry | Another try after a step fails. |
| note | A `note=` argument on a ticket. |

The steps keep plain names: `craft:brainstorm`, `craft:setup`, `craft:plan`, `craft:spec`, `craft:design`, `craft:build`, `craft:review`, `craft:merge`, and `craft:next`. `craft:rules` holds the rules that every step loads first.

## One-shot mode

Run `craft:plan <brief> mode=one-shot` to take a whole plan to merged code with two approvals. The plan lists up front every action only you can take and every paid service, with its price. After the plan gate, craft grills every ticket with you, one after another, without spec gates. A fresh agent then reviews every spec, and all specs together, for gaps and contradictions. The launch gate shows that review, all specs, the open owner actions, and the costs. After you approve it, craft builds, reviews, and merges every ticket on its own, and tells you when it is done. Tickets that set up or change staging or production keep the spec gate and the merge gate, and run after the rest.

## Install

This repository is a plugin marketplace with two plugins: `craft`, and `pstack` pinned to the version that craft is tested with.

- **claude.ai project threads:** add the plugins to your account from GitHub, `vanoostrum/craft`. Threads load account plugins, but not a repository's `.claude/settings.json`.
- **Terminal and web sessions:** add the marketplace to the project's `.claude/settings.json`, pinned to a tag:

  ```json
  "extraKnownMarketplaces": {
    "craft": { "source": { "source": "github", "repo": "vanoostrum/craft", "ref": "v2.3.0" } }
  },
  "enabledPlugins": { "craft@craft": true, "pstack@craft": true }
  ```

To upload transcripts to Google Cloud Storage, set `CRAFT_GCS_BUCKET` in the cloud environment, and add a "GCP access token" network secret for `storage.googleapis.com`. See `plugins/craft/hooks/upload_transcripts.py`.

## Set up a project

Run `craft:setup dev` in the project, after `craft:brainstorm` for a new idea. It works out with you how each part of the project runs locally, on cloud agents, and in CI, writes `Brief: Dev environment`, and starts `craft:plan` on the brief. The plan's PR writes `.claude/craft.md`, and its first ticket is a walking skeleton that adds the verify skill, the app driver skill, and the required checks. When the skeleton is merged, craft plans the product brief. At v1, the milestone checkpoint offers `craft:setup deploy` for staging and production. Your hosting preferences are in `plugins/craft/skills/setup/preferences.md`.

When it is done, a project gives craft these things:

1. **`.claude/craft.md`**, imported from `CLAUDE.md` with `@.claude/craft.md`:

   ```markdown
   # Craft config

   | Key | Value |
   |---|---|
   | Linear team | `ABC` |
   | Linear project | `Abc` |
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
6. **A Linear team and a Linear project.** One team holds all of the owner's projects; each project is a Linear project in it, with the briefs and plans as documents and the tickets as its backlog. The team has the states Todo, Specifying, Ready to build, Building, In Review, Done, and Needs human, and the label `ui`. `craft:setup` creates the team, or completes an existing team, and creates the project, with `plugins/craft/skills/setup/scripts/linear_team.py`. The script needs a Linear personal API key that can create teams. In the cloud environment, allow the host `api.linear.app` and add a network secret for it: header `Authorization`, the key as the value, without `Bearer`. In a terminal, set `LINEAR_API_KEY`. Linear's Free plan allows two teams.
7. **A GitHub repository** with the required checks on the base branch and "Automatically delete head branches" on.

## Upgrade to 2.3

Craft 2.3 keeps all projects in one Linear team, with one Linear project per project. Its briefs and plans are documents in that project, and its tickets are the backlog. A plan's tickets are sub-issues of its plan ticket. To upgrade a project:

1. Pick the shared team, and run `linear_team.py <TEAM KEY> <team name> <project name>` from `plugins/craft/skills/setup/scripts/` to complete it and create the project.
2. Move the project's open tickets and briefs into that Linear project.
3. Add `| Linear project | <name> |` to `.claude/craft.md`, and set `Linear team` to the shared team.

A step that finds no `Linear project` key asks the owner for it and adds it.

## Development

- Fix craft here, not in a project.
- Try a change on a live ticket with `claude --plugin-dir <this checkout>/plugins/craft` in a terminal session.
- Run the checks with `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check`, and `uv run pytest`.
- Release with a tag, and bump `ref` in each project in its own PR.

`plugins/craft/VENDORED.md` lists the skills that come from other repositories.
