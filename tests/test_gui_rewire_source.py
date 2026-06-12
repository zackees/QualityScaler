from __future__ import annotations

import ast
from pathlib import Path


GUI_SOURCE = Path(__file__).resolve().parents[1] / "src" / "qualityscaler" / "QualityScaler.py"


def _source() -> str:
    return GUI_SOURCE.read_text(encoding="utf-8")


def _tree() -> ast.Module:
    return ast.parse(_source())


def test_pipeline_code_removed_from_gui() -> None:
    source = _source()
    tree = _tree()

    class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
    function_names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert "AI_upscale" not in class_names
    assert "VideoUpscaleTask" not in class_names
    assert "upscale_orchestrator" not in function_names
    assert "upscale_image" not in function_names
    assert "upscale_video" not in function_names
    assert "InferenceSession" not in source
    assert "MODEL_MANIFEST_BASE_URL" not in source


def test_gui_imports_core_contract() -> None:
    core_imports: set[str] = set()
    for node in ast.walk(_tree()):
        if isinstance(node, ast.ImportFrom) and node.module == "qualityscaler.core":
            core_imports.update(alias.name for alias in node.names)

    expected = {
        "UpscaleSettings",
        "UpscaleProgress",
        "UpscaleCompleted",
        "UpscaleError",
        "UpscaleStopped",
        "run_pipeline",
        "app_version",
    }
    assert expected <= core_imports


def test_gui_defines_pipeline_process_entry_point() -> None:
    tree = _tree()
    entry_points = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_pipeline_process_main"
    ]

    assert len(entry_points) == 1
    arg_names = [arg.arg for arg in entry_points[0].args.args]
    assert arg_names == ["event_q", "stop_mp_event", "settings"]


def test_version_is_not_hardcoded_string_literal() -> None:
    version_assignments = [
        node
        for node in _tree().body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "version" for target in node.targets)
    ]

    assert len(version_assignments) == 1
    value = version_assignments[0].value
    assert not isinstance(value, ast.Constant), "version must not be a hardcoded literal"
    assert isinstance(value, ast.Call)
    assert isinstance(value.func, ast.Name)
    assert value.func.id == "app_version"
