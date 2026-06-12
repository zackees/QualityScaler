"""Guard: the whole ``qualityscaler`` package stays GUI-toolkit-free.

Walks every Python source under ``src/qualityscaler`` with ``ast`` and
asserts that no module imports ``tkinter`` or ``customtkinter`` — neither via
``import X`` nor ``from X import ...`` (dotted prefixes included). The CTk
GUI was deleted in issue #65 phase 5; the webview GUI must never reintroduce
a toolkit dependency.
"""

from __future__ import annotations

import ast
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1] / "src" / "qualityscaler"

FORBIDDEN_TOP_LEVEL = {"tkinter", "customtkinter"}


def _imported_top_level_modules(tree: ast.Module) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                modules.add(node.module.split(".")[0])
    return modules


def test_package_exists() -> None:
    assert PACKAGE_DIR.is_dir()
    assert any(PACKAGE_DIR.rglob("*.py"))


def test_gui_package_is_gone() -> None:
    assert not (PACKAGE_DIR / "gui").exists()


def test_no_module_imports_tkinter() -> None:
    for path in sorted(PACKAGE_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = _imported_top_level_modules(tree)
        offending = imported & FORBIDDEN_TOP_LEVEL
        assert not offending, (
            f"{path.relative_to(PACKAGE_DIR.parent)} imports forbidden GUI toolkit(s): "
            f"{sorted(offending)}"
        )
