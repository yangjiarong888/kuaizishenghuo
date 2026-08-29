import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
COMMAND_INDEX = SCRIPTS_DIR / "README.md"


def _run_scripts() -> list[Path]:
    return sorted(SCRIPTS_DIR.glob("run_*.py"))


@pytest.mark.parametrize("script", _run_scripts(), ids=lambda path: path.name)
def test_run_script_docstring_contains_copyable_command(script: Path):
    module = ast.parse(script.read_text(encoding="utf-8-sig"))
    docstring = ast.get_docstring(module, clean=False) or ""

    assert f"python scripts/{script.name}" in docstring


def test_script_command_index_covers_every_run_entry():
    assert COMMAND_INDEX.exists()
    content = COMMAND_INDEX.read_text(encoding="utf-8")

    missing = [
        script.name
        for script in _run_scripts()
        if f"python scripts/{script.name}" not in content
    ]
    assert missing == []
