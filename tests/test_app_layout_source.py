from __future__ import annotations

import ast
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "qualityscaler"
SHIM_SOURCE = SRC_ROOT / "QualityScaler.py"
GUI_DIR = SRC_ROOT / "gui"
APP_DIR = SRC_ROOT / "app"
WORKER_SOURCE = APP_DIR / "workers" / "upscale.py"
CONSTANTS_SOURCE = APP_DIR / "constants.py"

APP_AND_GUI_SOURCES = (
    sorted(GUI_DIR.glob("*.py")) + sorted(APP_DIR.rglob("*.py")) + [SHIM_SOURCE]
)

TOOLKIT_FREE_SOURCES = [
    APP_DIR / "__init__.py",
    APP_DIR / "assets.py",
    APP_DIR / "constants.py",
    APP_DIR / "controllers" / "__init__.py",
    APP_DIR / "controllers" / "upscale.py",
    APP_DIR / "controllers" / "framegen.py",
    APP_DIR / "ff_constants.py",
    APP_DIR / "ff_info_texts.py",
    APP_DIR / "ff_preferences.py",
    APP_DIR / "ff_state.py",
    APP_DIR / "file_chooser.py",
    APP_DIR / "info_texts.py",
    APP_DIR / "media_info.py",
    APP_DIR / "preferences.py",
    APP_DIR / "state.py",
    APP_DIR / "workers" / "__init__.py",
    APP_DIR / "workers" / "upscale.py",
    APP_DIR / "workers" / "framegen.py",
    GUI_DIR / "__init__.py",
]


def _source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _tree(path: Path) -> ast.Module:
    return ast.parse(_source(path))


def test_pipeline_code_removed_from_gui() -> None:
    for path in APP_AND_GUI_SOURCES:
        source = _source(path)
        tree = ast.parse(source)

        class_names = {node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)}
        function_names = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        assert "AI_upscale" not in class_names, path.name
        assert "VideoUpscaleTask" not in class_names, path.name
        assert "upscale_orchestrator" not in function_names, path.name
        assert "upscale_image" not in function_names, path.name
        assert "upscale_video" not in function_names, path.name
        assert "InferenceSession" not in source, path.name
        assert "MODEL_MANIFEST_BASE_URL" not in source, path.name


def test_gui_imports_core_contract() -> None:
    core_imports: set[str] = set()
    for path in APP_AND_GUI_SOURCES:
        for node in ast.walk(_tree(path)):
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
    tree = _tree(WORKER_SOURCE)
    entry_points = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_pipeline_process_main"
    ]

    assert len(entry_points) == 1
    arg_names = [arg.arg for arg in entry_points[0].args.args]
    assert arg_names == ["event_q", "stop_mp_event", "settings", "log_q"]


def test_version_is_not_hardcoded_string_literal() -> None:
    version_assignments = [
        node
        for node in _tree(CONSTANTS_SOURCE).body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "version" for target in node.targets)
    ]

    assert len(version_assignments) == 1
    value = version_assignments[0].value
    assert not isinstance(value, ast.Constant), "version must not be a hardcoded literal"
    assert isinstance(value, ast.Call)
    assert isinstance(value.func, ast.Name)
    assert value.func.id == "app_version"


def test_toolkit_free_modules_do_not_import_gui_toolkit() -> None:
    forbidden = {"tkinter", "customtkinter"}
    for path in TOOLKIT_FREE_SOURCES:
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.Import):
                modules = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                modules = {(node.module or "").split(".")[0]}
            else:
                continue
            assert not (modules & forbidden), f"{path.name} imports a GUI toolkit"


def test_shim_is_small_and_delegates_to_gui_app() -> None:
    tree = _tree(SHIM_SOURCE)
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "qualityscaler.gui.app"
    ]
    assert len(imports) == 1
    assert any(alias.name == "main" for alias in imports[0].names)
    assert len(_source(SHIM_SOURCE).splitlines()) < 25
