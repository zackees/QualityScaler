"""Guard: the frontend-agnostic ``qualityscaler.app`` package stays toolkit-free.

Walks every Python source under ``src/qualityscaler/app`` with ``ast`` and
asserts that no module imports ``tkinter`` or ``customtkinter`` — neither via
``import X`` nor ``from X import ...`` (dotted prefixes included).
"""

from __future__ import annotations

import ast
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1] / "src" / "qualityscaler" / "app"

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


def test_app_package_exists() -> None:
    assert APP_DIR.is_dir()
    assert any(APP_DIR.rglob("*.py"))


def test_app_modules_do_not_import_tkinter() -> None:
    for path in sorted(APP_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported = _imported_top_level_modules(tree)
        offending = imported & FORBIDDEN_TOP_LEVEL
        assert not offending, (
            f"{path.relative_to(APP_DIR.parent)} imports forbidden GUI toolkit(s): "
            f"{sorted(offending)}"
        )
