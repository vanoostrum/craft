---
name: brainstorm
description: Craft step before the plan. Brainstorm an idea with the owner until it is clear what to build and why, and write it into a brief for craft:plan. Use when the owner has an idea that is not yet a spec, or asks to brainstorm.
model: opus
argument-hint: "<idea, file, or link> [note=<text, file, or link>]..."
---

# craft:brainstorm

Load the `craft:rules` skill first, and follow it. Then load `craft:bstack` with the Skill tool, before any pstack skill.

The owner often has not finished working out what they want. This step helps the owner think it through, and adds ideas of its own. It is divergent: it opens the idea up before `craft:plan` narrows it down. Its output is a brief: what to build, for whom, and why. The brief is the input of `craft:plan`.

The brief is a snapshot. `craft:plan` reads it once. After the plan gate, Linear, `GLOSSARY.md`, `docs/adr/`, and `design/` are the truth, and nobody keeps the brief up to date.

## Input

An idea from the owner, as text, a file, or a link. Optional `note=` arguments follow it, as Steering in `craft:rules` describes.

## Steps

1. **Read what exists.** For an existing app, read the code, `GLOSSARY.md`, `docs/adr/`, `design/`, and the open tickets in the Linear project from the config. Read the files and links in the notes. Do not ask the owner what these already answer, and do not reopen what they already decide.
2. **First message.** Say the idea back in your own words: what the owner wants, for whom, and why, as far as the owner has said. Add what you found that bears on it, such as how the app works today, or a constraint or a cheaper path the owner may not have seen. Then ask one open question about why the owner wants it, unless the owner already said so.
3. **The conversation.** Ask one question at a time, in chat. Build each question on the owner's last answer or on something you found.
   - Until you know why the owner wants it, ask open questions, with no recommended answer and no options to pick from. Options steer the owner away from their own words.
   - After that, when a decision has choices you can name, sketch each one with what it trades off and say which you would pick.
   - Cover this ground, but do not read it out as a list: what kind of thing it is and what makes it special, who it is for, why now, what success looks like, goals, non-goals, anti-goals (what would make it a failure even if it works), prior art that the owner loved or hated, and the details the owner cares about.
   - Ask only about what it does and how it looks and feels. Decide technical matters yourself and say so in one line, as `craft:spec` describes in **What to decide yourself**.
   - When the owner says "you decide" or "what do you think", propose something concrete.
4. **Bring your own ideas.** Look further when it helps: in the code, in the owner's files, and on the web. Say what you looked for and what you found. Bring at least one idea that the owner did not ask for: a twist from prior art, a cheaper path, or a conflict with what exists.
5. **Play it back.** As soon as one part is clear, describe it back in 200 to 300 words, then go on to the next part. Mark what the owner said as the owner's, and what you added as your proposal, with your reason. End each playback by asking what is wrong or missing.
6. **Directions.** Once you know what the owner wants, lay out two or three product directions in a message of their own: different ways the idea could work for its users, not different technologies. Drop the weak ones. Say what each trades off, recommend one, and ask the owner to pick.
7. **Look and feel.** If the idea has screens and their look matters to it, settle the look here. This is the one place where the owner chooses between looks: `craft:plan` freezes what this step settles, and does not prototype it again. Work in Claude Design: the Artifact tool's Design type, started with `quickstart` and intent `design`.
   - Draw two or three variants that differ in direction, such as layout, density, or tone, not in detail. Draw them on the primary platform only. The owner picks one, or combines parts.
   - Then iterate on the chosen one with the owner until the owner says it is right. Settle the visual identity: colours, fonts, and the main shapes. Draw the defining screens: the one to three screens that show what makes the product special, such as the home screen. Go to the detail the owner wants.
   - Leave the other screens, the states, the edge cases, and the other platforms to `craft:design`: slicing in `craft:plan` decides which screens there are.
   - Do not write to `design/`: `craft:design` freezes the gallery in `craft:plan`.
8. **Size it.** If the idea is several increments, say so, agree on an order with the owner, and brief the first one only. Note the others under **Later** in the brief.
9. **Write the brief.** Write the brief as a Linear document in the Linear project from the config, titled `Brief: <name>`. For a new project, with no `.claude/craft.md` yet, ask the owner for the Linear team key and the project name first, and run `linear_team.py` as step 2 of `craft:setup` describes. It creates the team if needed, and the project. Name the team key and the project in the brief, so that `craft:setup dev` uses the same ones. Write it with the `craft:clear-technical-prose` skill:
   - **Intent:** what to build, for whom, and why, in the owner's terms.
   - **Success:** what success looks like to the owner.
   - **Goals**, **Non-goals**, and **Anti-goals.**
   - **Constraints:** hard values such as limits, platforms, and naming or copy rules, word for word as the owner gave them.
   - **Directions:** the directions from step 6, what each trades off, the one the owner picked, and why.
   - **Look:** only if step 7 ran. The links to the prototypes with the chosen one marked, a screenshot of each, the direction in words (what the owner picked, loved, and hated, and the references the owner gave), and what is still open. Also:
     - **Identity:** the values of the visual identity, such as the colours as hex codes and the font names, so that `craft:design` can write `design/gallery.css` from them;
     - **Screens:** each screen drawn, with the platform and where it is on the canvas.
   - **Decisions:** each decision from the conversation, one line each. Mark the ones you took yourself `(agent)`.
   - **Open for the plan:** what the plan must still settle.
   - **Later:** only if step 8 found more increments.
   - **Steering:** the `note=` arguments, if any.
10. **Builder check.** Start a subagent on the `brief reviewer` model from `models.md` from `craft:rules`. Give it only the link to the brief, and this task:

    > Load the `craft:bstack` skill first. You will plan this work into tickets, and you cannot talk to the person who wrote the brief. Read it. List only the questions you would still need answered to plan it well: places where you would have to guess, and a wrong guess would matter. For each, give the question and why the answer changes the plan. Rank them by importance. Skip what the brief leaves to the plan, and what you could decide yourself. If nothing important is left, say "nothing important left".

    Sort its questions: answered already (put the answer in the brief), minor (decide it yourself and mark it `(agent)`), or the owner's. Ask the owner's questions in one message, most important first, and update the brief.

## Approval

Ask the owner in chat to approve the brief, with its link, by 👍 on the message or a reply "approve". In the same message, list the arguments of the plan of this brief, one line each, with its default and what it does:

- `design-variants=<n>`, default `1`;
- `platforms=<list>`, default derived from the project;
- `mode=<gated|one-shot>`, default `gated`;
- `note=<text, file, or link>`, default none.

"approve" or 👍 keeps the defaults. The owner sets an argument by adding it to the reply, such as "approve mode=one-shot". The table in Steering in `craft:rules` has what each one does.

An argument that is not in this list, or a value that the table does not allow, such as `mode=fast`, is not an approval: name the arguments and values you accept, and ask again. Any other reply is feedback: go back to the step it belongs to. There is no gate and no Linear comment here, because there is no ticket yet. The plan gate is the first formal gate.

## After approval

Write the arguments the owner gave at approval into the brief's **Steering** section: only the arguments the owner gave, with no defaults filled in, so `craft:plan` can tell a choice from silence. A `note=` given at approval is added to the notes already in **Steering**; it does not replace them.

Start `craft:plan` in a new session, so that the plan starts with a fresh context and the brief is all it knows of the brainstorm. Use this prompt: `Run craft:plan on <brief link>.` Do not put the arguments in the prompt: `craft:plan` reads the brief's **Steering** as its arguments, and an argument in the prompt would replace the brief's values. For a new project, or a project with no `.claude/craft.md`, use `Run craft:setup dev on <brief link>.` instead: the dev environment comes first, and its plan runs before the plan of this brief. The owner's arguments stay in this product brief: its plan starts when the walking skeleton is merged, and reads them then. In a claude.ai project, ask the coordinator for a new thread. In a terminal, give the owner the command `claude "<prompt>"` to run in a new terminal. Tell the owner in chat in one line.

## Done when

The brief is a Linear document in the project's Linear project, the owner has approved it, and `craft:plan` or `craft:setup dev` is started on it.
