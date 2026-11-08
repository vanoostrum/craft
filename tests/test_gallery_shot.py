# Copyright (C) 2026 Theo van Oostrum
"""`gallery-shot` checks its arguments before it starts a browser."""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "craft" / "skills" / "rules" / "scripts" / "gallery-shot"


def run_script(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the script from a project's root."""
    return subprocess.run(  # noqa: S603 - runs the script under test.
        [str(SCRIPT), *args],
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
    )


def test_rejects_an_unknown_platform(tmp_path: Path) -> None:
    """A platform outside the gallery rules is an error."""
    result = run_script(tmp_path, "design/pages/a/default.html", "tv", str(tmp_path))
    assert result.returncode != 0
    assert "unknown platform 'tv'" in result.stderr


def test_rejects_a_missing_page(tmp_path: Path) -> None:
    """A page that is not in the project's design/ is an error."""
    result = run_script(tmp_path, "pages/a/default.html", "mobile", str(tmp_path))
    assert result.returncode != 0
    assert "no gallery page design/pages/a/default.html" in result.stderr
