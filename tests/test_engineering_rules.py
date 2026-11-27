# Copyright (C) 2026 Theo van Oostrum
"""Spec, build, and the fresh reviewer read the three layers of engineering rules."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "plugins" / "craft" / "skills"
RULES_DIR = SKILLS / "rules"
SHARED = RULES_DIR / "engineering.md"
TEMPLATE = RULES_DIR / "profiles" / "_template.md"
SHARED_RULE_NAMES = [
    "Reuse before you write.",
    "Clean up what you touch.",
    "Catch narrowly.",
    "Keep a file to one read.",
    "Leave no dead code.",
    "Few layers.",
    "Make the code pass, not the test.",
    "Mock only at the boundary.",
    "Tests show intent.",
    "Finish the job.",
    "No secrets in the code.",
    "Add dependencies on purpose.",
]
NAMED_WORKS = ["Fowler", "Ousterhout", "Google's code review guide", "Beck", "Martin"]
PROFILE_SECTIONS = [
    "Structure",
    "Naming",
    "Libraries",
    "Error handling",
    "Metrics",
    "Sources",
]
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def skill(name: str) -> str:
    """Return the text of a skill's `SKILL.md`."""
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return the body of the `## <heading>` section of `text`."""
    return text.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def step(text: str, name: str) -> str:
    """Return the numbered step or bullet whose bold name is `name`."""
    rest = text.split(f"**{name}**", 1)[1].split("\n## ", 1)[0]
    end = re.search(r"\n\s*(?:\d+\.|-) \*\*", rest)
    return rest[: end.start()] if end else rest


def table_row(text: str, key: str) -> str:
    """Return the table row of `text` whose first cell is `key`."""
    return next(line for line in text.splitlines() if line.startswith(f"| {key} |"))


def engineering_rules() -> str:
    """Return the **Engineering rules** section of `craft:rules`."""
    return section(skill("rules"), "Engineering rules")


# Criterion 1: the shared rules.


def test_shared_rules_hold_the_twelve_named_rules() -> None:
    """`engineering.md` has 12 rule bullets, each with its bold name, in order."""
    rules = section(SHARED.read_text(encoding="utf-8"), "Rules")
    bullets = [line for line in rules.splitlines() if line.startswith("- ")]
    names = [re.match(r"- \*\*(.+?)\*\* ", b) for b in bullets]
    assert [m.group(1) for m in names if m] == SHARED_RULE_NAMES
    assert len(bullets) == len(SHARED_RULE_NAMES)


def test_shared_rules_name_the_works_without_restating_them() -> None:
    """The **Named, not restated** section names each work on its own line."""
    named = section(SHARED.read_text(encoding="utf-8"), "Named, not restated")
    for work in NAMED_WORKS:
        assert work in named
    assert "Its very small functions and many classes add layers" in named


def test_shared_rules_put_the_project_rules_first() -> None:
    """The intro gives the order of the layers and cites the ADR."""
    intro = SHARED.read_text(encoding="utf-8").split("\n## ", 1)[0]
    assert "the project rules win over both (`docs/adr/0011`)" in intro


# Criterion 2: the profile template.


def test_profile_template_has_the_sections() -> None:
    """`_template.md` holds each profile section, in order."""
    text = TEMPLATE.read_text(encoding="utf-8")
    positions = [text.find(f"\n## {name}\n") for name in PROFILE_SECTIONS]
    assert -1 not in positions
    assert positions == sorted(positions)


def test_profile_template_says_it_is_never_in_stacks() -> None:
    """A file whose name starts with `_` is a template, never named in `Stacks`."""
    intro = TEMPLATE.read_text(encoding="utf-8").split("\n## ", 1)[0]
    assert "starts with `_` is a template" in intro
    assert "`Stacks` never names it" in intro


def test_rule_files_hold_no_email_address() -> None:
    """The repo is public: no rule file holds an email address."""
    for path in (SHARED, *sorted((RULES_DIR / "profiles").glob("*.md"))):
        assert not EMAIL.search(path.read_text(encoding="utf-8")), path


# Criterion 3 and Review focus 1, 2, 3, and 5: the Engineering rules section.


def test_section_names_the_three_layers_in_order() -> None:
    """The section names the three files and which layer wins."""
    text = engineering_rules()
    for path in (
        "`<rules>/engineering.md`",
        "`<rules>/profiles/<stack>.md`",
        "`docs/engineering.md`",
    ):
        assert path in text
    assert "The project rules win over the profile" in text
    assert "the profile wins over the shared rules" in text


def test_section_gives_the_stacks_format() -> None:
    """`Stacks` is one table row of path → profile pairs, or `none`."""
    stacks = step(engineering_rules(), "Stacks.")
    assert "`| Stacks | <list> |`" in stacks
    assert "`` `<path>` → `<profile>` ``" in stacks
    assert "ends with `/`, and `/` is the whole repo" in stacks
    assert "A missing key reads as `none`" in stacks
    assert "the longest path that holds it" in stacks


def test_section_gives_the_project_rules_format() -> None:
    """`docs/engineering.md` has its title, sources, and `## In CLAUDE.md` links."""
    project = step(engineering_rules(), "`docs/engineering.md` format.")
    assert "`# Engineering rules`" in project
    assert "`Source:`" in project
    assert "`Replaces: <file> **<name>**`" in project
    assert "`## In CLAUDE.md`" in project
    assert "no copy of its text" in project


def test_section_gives_the_rule_format() -> None:
    """Each rule starts with a bold name, and a finding names file and rule."""
    rule = step(engineering_rules(), "Rule format.")
    assert "starts with a bold name" in rule
    assert "by its file and its bold name" in rule


def test_section_reads_the_files_with_the_read_tool() -> None:
    """Each step reads every rule file in full with the Read tool."""
    read = step(engineering_rules(), "Read the rules.")
    assert "with the Read tool, in full" in read
    assert "right after they load `craft:bstack`" in read
    assert "absolute path" in read


def test_section_reads_the_shared_rules_first() -> None:
    """The shared rules come first, also in a repo without `.claude/craft.md`."""
    read = step(engineering_rules(), "Read the rules.")
    assert "First read `<rules>/engineering.md`" in read
    assert "also when `.claude/craft.md` is missing" in read


def test_section_skips_missing_files_without_asking() -> None:
    """No `Stacks`, a missing profile, or no project rules: skip and say so."""
    skips = step(engineering_rules(), "Skips.")
    assert "Do not ask the owner" in skips
    assert "step comment" in skips
    assert "`Stacks: none`" in skips
    assert "`profile <stack> missing`" in skips
    assert "`no docs/engineering.md`" in skips


def test_section_names_the_exception_marker() -> None:
    """A spec decision `(exception: <rule name>)` lets the ticket break the rule."""
    exception = step(engineering_rules(), "Rule exception.")
    assert "`(exception: <rule name>)`" in exception
    assert "is not a blocking finding" in exception


# Criterion 4: the fixed-paths row and the `<rules>` table.


def test_fixed_paths_row_names_the_three_layers() -> None:
    """The `Engineering rules` row names the three files and what `CLAUDE.md` keeps."""
    row = table_row(skill("rules"), "Engineering rules")
    assert "`<rules>/engineering.md`" in row
    assert "`<rules>/profiles/<stack>.md`" in row
    assert "`Stacks`" in row
    assert "`docs/engineering.md`" in row
    assert "`CLAUDE.md` keeps the commands and the test seam rule" in row


def test_rules_table_lists_the_rule_files() -> None:
    """The `<rules>` file table lists `engineering.md` and `profiles/`."""
    text = skill("rules")
    assert table_row(text, "`engineering.md`")
    assert table_row(text, "`profiles/`")


# Criterion 5: spec and build read the rules first.


def test_spec_and_build_read_the_rules_after_bstack() -> None:
    """The line after the bstack line sends the step to **Engineering rules**."""
    for name in ("spec", "build"):
        lines = [line for line in skill(name).splitlines() if line]
        bstack = next(i for i, line in enumerate(lines) if "`craft:bstack`" in line)
        after = lines[bstack + 1]
        assert "read the engineering rules" in after, name
        assert "**Engineering rules** in `craft:rules`" in after, name


# Criterion 6: the grill raises each conflict with a rule.


def test_grill_asks_every_conflict_with_three_options() -> None:
    """A conflict is always asked, with follow, exception, or change the rule."""
    rules = step(skill("spec"), "Rules.")
    assert "Check the ticket against the engineering rules" in rules
    assert "whatever your certainty" in rules
    assert "The ticket follows the rule, and the spec changes" in rules
    assert "`(exception: <rule name>)` under **Decisions**" in rules
    assert "The rule changes" in rules
    assert "rule change ticket" in rules


# Criterion 7: Domain docs hold project rules, and build writes them.


def test_domain_docs_can_change_the_project_rules() -> None:
    """Spec step 5 holds `docs/engineering.md` entries, and build writes them."""
    steps = section(skill("spec"), "Steps")
    domain_docs = steps.split("**Domain docs:**", 1)[1].split("\n", 1)[0]
    assert "`docs/engineering.md`" in domain_docs
    build_docs = step(skill("build"), "Domain docs.")
    assert "`docs/engineering.md`" in build_docs


# Criterion 8: the one-shot scout and writer read the rules.


def test_one_shot_scout_and_writer_read_the_rules() -> None:
    """Both subagents get the rule paths and read them."""
    one_shot = section(skill("spec"), "One-shot")
    for name in ("Scout.", "Write."):
        part = step(one_shot, name)
        assert "absolute paths of the engineering rule files" in part, name
        assert "reads them" in part, name


# Criterion 9 and Review focus 4 and 5: the fresh reviewer.


def test_review_gives_the_reviewer_absolute_rule_paths() -> None:
    """The review step passes absolute paths, not `<rules>`, to the subagent."""
    fresh = step(skill("review"), "Review in a fresh agent.")
    task = fresh.split("> ", 1)[1]
    assert "the absolute path of each engineering rule file" in fresh.split("> ", 1)[0]
    assert "<rules>" not in task


def test_reviewer_reads_each_rule_file_and_blocks_on_a_break() -> None:
    """The task reads each rule file, lists it, and blocks on a break."""
    task = step(skill("review"), "Review in a fresh agent.").split("> ", 1)[1]
    assert "Read in full each engineering rule file whose path you got" in task
    assert "list it under **Files read**" in task
    assert "a blocking finding that names the file and the rule" in task
    assert "`(exception: <rule name>)`" in task
    assert "not a blocking finding" in task


def test_review_names_each_skip_in_its_step_comment() -> None:
    """A skipped rule file shows on every path: gate, one-shot, and FAIL."""
    paths = step(skill("review"), "Review in a fresh agent.").split("> ", 1)[0]
    assert "name each skip in the step comment" in paths
    assert "**Skips** in `craft:rules`" in paths
    for comment in (
        "`🤖 Gate: merge`",
        "`🤖 review: success`",
        "review comment on the PR",
    ):
        assert comment in paths
    assert "gate comment" not in paths


# Criterion 10: the blocking list.


def test_findings_block_on_a_broken_rule() -> None:
    """A broken engineering rule is blocking, unless the spec has an exception."""
    findings = (RULES_DIR / "findings.md").read_text(encoding="utf-8")
    blocking = findings.split("**Blocking**", 1)[1].split("**Non-blocking**", 1)[0]
    assert (
        "a broken engineering rule, unless the spec has an exception for it" in blocking
    )


# Criterion 11: the test seam rule in `CLAUDE.md`.


def test_gallery_stage_two_names_the_test_seam_rule() -> None:
    """Stage 2 adds `tests/design/` to the test seam rule in `CLAUDE.md`."""
    gallery = (RULES_DIR / "gallery.md").read_text(encoding="utf-8")
    row = next(line for line in gallery.splitlines() if line.startswith("| 2. "))
    assert "the test seam rule in `CLAUDE.md`" in row


def test_no_skill_puts_the_engineering_rules_in_claude_md() -> None:
    """No skill file says the engineering rules live in `CLAUDE.md`."""
    for path in SKILLS.rglob("*.md"):
        text = path.read_text(encoding="utf-8").lower()
        assert "the engineering rules in `claude.md`" not in text, path


# Criterion 13: the rule change ticket.


def test_rule_change_ticket_goes_to_the_craft_project() -> None:
    """The grill files it in **Backlog** of the Craft project, with its title."""
    ticket = step(skill("spec"), "Rule change ticket.")
    assert "the Linear project `Craft`, in **Backlog**" in ticket
    assert "also when this ticket is in another project" in ticket
    assert "`Change <file> rule **<name>**`" in ticket
    for part in ("proposed wording", "reason from the grill", "link to this ticket"):
        assert part in ticket


def test_rule_change_ticket_labels_a_profile_rule() -> None:
    """A profile rule gets the label `profile`, created when missing."""
    ticket = step(skill("spec"), "Rule change ticket.")
    assert "add the label `profile`" in ticket
    assert "create the label" in ticket
    assert "A shared rule gets no label" in ticket


def test_rule_change_ticket_adds_evidence_to_an_open_ticket() -> None:
    """The rule's file and bold name are the dedupe key: no second ticket."""
    ticket = step(skill("spec"), "Rule change ticket.")
    assert "its file and its bold name, is the dedupe key" in ticket
    assert "add a link to this ticket there as evidence" in ticket
    assert "file no second ticket" in ticket


def test_rule_tickets_live_in_the_craft_project() -> None:
    """**One project's tickets** lets rule tickets live in the Craft project."""
    one_project = step(skill("rules"), "One project's tickets.")
    assert "a ticket about a shared or profile rule" in one_project
    assert "lives in the Linear project `Craft`" in one_project
    assert "whatever project raised it" in one_project
