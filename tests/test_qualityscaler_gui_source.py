from __future__ import annotations

import ast
from pathlib import Path


GUI_SOURCE = Path(__file__).resolve().parents[1] / "src" / "qualityscaler" / "QualityScaler.py"


def _get_app_method(method_name: str) -> ast.FunctionDef:
    source = GUI_SOURCE.read_text(encoding="utf-8")
    app_start = source.index("class App():")
    app_end = source.index("# Main functions", app_start)
    tree = ast.parse(source[app_start:app_end])
    app_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "App")
    return next(node for node in app_class.body if isinstance(node, ast.FunctionDef) and node.name == method_name)


def test_main_window_title_uses_window_title_builder() -> None:
    init_method = _get_app_method("__init__")
    title_calls = [
        node
        for node in ast.walk(init_method)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "window"
        and node.func.attr == "title"
    ]

    assert len(title_calls) == 1
    title_arg = title_calls[0].args[0]
    assert isinstance(title_arg, ast.Call)
    assert isinstance(title_arg.func, ast.Attribute)
    assert isinstance(title_arg.func.value, ast.Name)
    assert title_arg.func.value.id == "self"
    assert title_arg.func.attr == "_get_window_title"


def test_window_title_builder_uses_app_name_and_preserves_engine_info() -> None:
    title_method = _get_app_method("_get_window_title")

    returns_app_name = any(
        isinstance(node, ast.Return)
        and isinstance(node.value, ast.Name)
        and node.value.id == "app_name"
        for node in ast.walk(title_method)
    )
    returns_app_name_with_engine_info = any(
        isinstance(node, ast.Return)
        and isinstance(node.value, ast.JoinedStr)
        and any(isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name) and value.value.id == "app_name" for value in node.value.values)
        and any(isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name) and value.value.id == "AI_engine_info" for value in node.value.values)
        for node in ast.walk(title_method)
    )

    assert returns_app_name
    assert returns_app_name_with_engine_info
