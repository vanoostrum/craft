# Copyright (C) 2026 Theo van Oostrum
"""The rubric files of `craft:audit`, and `rubric.py`, which reads them.

`rubric.py` runs as a command, as the audit runs it. The fixture rubrics are
made up.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "plugins" / "craft" / "skills" / "audit"
RUBRICS = AUDIT / "rubrics"
SCRIPT = AUDIT / "scripts" / "rubric.py"
REVIEW_ITEMS = (
    "Read in context",
    "Criteria evidence",
    "Design and maintainability",
    "Findings rounds",
    "Process logic",
)

GOOD = """# Speed rubric

Rubric version: 2
Phase: custom

A made-up rubric.

## Items

### Quick review

Kind: Check
Reads: The full review's transcript digest.
Score: The share that passes.
Pass: The review took less than an hour.
Partial: It took one to two hours.
Fail: It took longer.

### Rounds

Kind: Measure
Reads: The PR's comments.
Score: `scripts/rounds.py` prints Rounds until PASS, as a median.

### Late bugs

Kind: Escape
Reads: Later fix PRs.
Score: The count per ticket.
"""


def run(*args: str | Path) -> subprocess.CompletedProcess[str]:
    """Run `rubric.py` with arguments."""
    return subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )


def rubric_files() -> list[Path]:
    """Return every rubric file in the plugin, templates too."""
    return sorted(RUBRICS.glob("*.md")) + sorted((RUBRICS / "custom").glob("*.md"))


def write(tmp_path: Path, name: str, text: str) -> Path:
    """Write a rubric file and return its path."""
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def review() -> str:
    """Return the text of the Review rubric."""
    return (RUBRICS / "review.md").read_text(encoding="utf-8")


def item(text: str, name: str) -> str:
    """Return the body of the `### <name>` item of a rubric."""
    return text.split(f"\n### {name}\n", 1)[1].split("\n### ", 1)[0]


# Criterion 4: the rubric file format.


@pytest.mark.parametrize("path", rubric_files(), ids=lambda path: path.name)
def test_every_rubric_file_follows_the_format(path: Path) -> None:
    """`_example.md` too."""
    result = run("check", path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_the_example_is_a_custom_rubric() -> None:
    """The template shows a custom rubric with one check."""
    text = (RUBRICS / "custom" / "_example.md").read_text(encoding="utf-8")
    assert re.search(r"^Phase: custom$", text, re.MULTILINE)
    assert re.findall(r"^Kind: (\w+)$", text, re.MULTILINE) == ["Check"]


def test_an_empty_file_fails(tmp_path: Path) -> None:
    """A file with no rubric in it is not a rubric."""
    assert run("check", write(tmp_path, "empty.md", "")).returncode == 1


def test_a_rubric_with_all_kinds_passes(tmp_path: Path) -> None:
    """The format accepts every kind."""
    result = run("check", write(tmp_path, "speed.md", GOOD))
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    ("change", "error"),
    [
        (("# Speed rubric", "# Speed"), "title"),
        (("Rubric version: 2", "Rubric version: two"), "Rubric version"),
        (("Phase: custom\n", ""), "Phase"),
        (("Phase: custom", "Phase: custom\nApplies to: some"), "Applies to"),
        (("Kind: Measure", "Kind: Guess"), "Kind"),
        (("Reads: The PR's comments.\n", ""), "Reads"),
        (("Partial: It took one to two hours.\n", ""), "Partial"),
        (("`scripts/rounds.py` prints", "a script prints"), "script"),
        (("Kind: Escape", "Kind: Escape\nPer: craft version"), "Per"),
        (("## Items", "## Things"), "Items"),
    ],
)
def test_a_broken_rubric_fails_with_its_error(
    tmp_path: Path, change: tuple[str, str], error: str
) -> None:
    """Each required line is checked, and the error names it."""
    old, new = change
    result = run("check", write(tmp_path, "speed.md", GOOD.replace(old, new, 1)))
    assert result.returncode == 1
    assert error in result.stdout


# Criterion 3: which rubrics run.


def test_the_names_are_every_rubric_without_an_underscore(tmp_path: Path) -> None:
    """Phase rubrics first, then custom rubrics; `_` files are templates."""
    write(tmp_path, "review.md", GOOD)
    write(tmp_path, "custom/speed.md", GOOD)
    write(tmp_path, "custom/_example.md", GOOD)
    result = run("names", tmp_path)
    assert result.returncode == 0
    assert result.stdout.split() == ["review", "speed"]


def test_the_plugin_runs_the_review_rubric_and_skips_the_example() -> None:
    """With no custom rubric, the weekly run judges only the Review rubric."""
    names = run("names").stdout.split()
    assert "review" in names
    assert "_example" not in names


def test_find_looks_in_rubrics_then_custom(tmp_path: Path) -> None:
    """A custom rubric without `_` is found by its name."""
    write(tmp_path, "custom/speed.md", GOOD)
    result = run("find", "speed", tmp_path)
    assert result.returncode == 0
    assert result.stdout.strip() == str(tmp_path / "custom" / "speed.md")


def test_an_unknown_name_lists_the_rubric_names(tmp_path: Path) -> None:
    """Review focus 3: the audit stops with this list."""
    write(tmp_path, "review.md", GOOD)
    write(tmp_path, "custom/speed.md", GOOD)
    result = run("find", "reveiw", tmp_path)
    assert result.returncode == 2  # noqa: PLR2004 - the usage error code.
    assert "unknown rubric 'reveiw'" in result.stderr
    assert "review, speed" in result.stderr


def test_a_template_is_not_found_by_name(tmp_path: Path) -> None:
    """`rubric=_example` is an unknown name."""
    write(tmp_path, "custom/_example.md", GOOD)
    assert run("find", "_example", tmp_path).returncode == 2  # noqa: PLR2004


# Criterion 5: the Review rubric.


def test_the_review_rubric_header() -> None:
    """Version 1, the review phase, tickets with a spec only."""
    text = review()
    assert text.startswith("# Review rubric\n")
    for line in (
        "Rubric version: 1",
        "Phase: review",
        "Applies to: tickets with a spec",
    ):
        assert re.search(f"^{line}$", text, re.MULTILINE), line


def test_the_review_rubric_has_the_five_items() -> None:
    """In this order."""
    items = re.findall(r"^### (.+)$", review(), re.MULTILINE)
    assert tuple(items) == REVIEW_ITEMS


def test_the_review_rubric_item_kinds() -> None:
    """Four checks, one of them per craft version, and one measure."""
    kinds = {name: item(review(), name) for name in REVIEW_ITEMS}
    assert "Kind: Measure" in kinds["Findings rounds"]
    assert "`scripts/rounds.py`" in kinds["Findings rounds"]
    for name in REVIEW_ITEMS[:3]:
        assert "Kind: Check" in kinds[name]
        assert "Per:" not in kinds[name]
    assert "Kind: Check" in kinds["Process logic"]
    assert "Per: craft version" in kinds["Process logic"]


def test_the_design_and_maintainability_check() -> None:
    """Theo's check, with its wording, and no score of the code."""
    text = item(review(), "Design and maintainability")
    assert (
        "Did the review look at design and maintainability, as the project's rules ask?"
    ) in text
    assert re.search(
        r"^Pass: .*structure, duplication, and fit with the existing code",
        text,
        re.MULTILINE,
    )
    assert re.search(r"^Fail: .*checked only the criteria", text, re.MULTILINE)
    assert "does not judge the code itself" in text


def test_process_logic_names_the_review_hooks_and_rules() -> None:
    """The two hooks that gate a review session, against the review rules."""
    text = item(review(), "Process logic")
    for path in (
        "hooks/one_step_per_session.py",
        "hooks/require_bstack.py",
        "skills/review/SKILL.md",
        "skills/rules/findings.md",
        "skills/rules/SKILL.md",
    ):
        assert path in text, path


def test_process_logic_results_do_not_overlap() -> None:
    """Reviews 1 and 2: one reading per case, so judges give the same result."""
    text = item(review(), "Process logic")
    assert "A hook rule is a rule in these files that names a hook" in text
    for case in (
        "another way to load the same skill",
        "a command that the owner typed",
        "an allow when the hook cannot read its input",
    ):
        assert case in text, case
    assert re.search(r"^Pass: .*every case the rule names", text, re.MULTILINE)
    assert re.search(
        r"^Partial: Each hook rule has a hook, and no hook blocks what a rule asks for",
        text,
        re.MULTILINE,
    )
    assert re.search(
        r"^Fail: A hook rule has no hook that enforces it, or a hook blocks",
        text,
        re.MULTILINE,
    )
    assert "something the rules do not say" not in text
