from __future__ import annotations

import importlib
import os
import subprocess
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest


def test_vendored_iso_env_accepts_runtime_python_version() -> None:
    from qualityscaler._vendor.iso_env import Requirements

    requirements = Requirements("requests", python_version="==3.10.*")

    assert requirements.content == "requests"
    assert requirements.python_version == "==3.10.*"


@pytest.fixture()
def cli_module(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Import the launcher with a fake iso-env module for unit tests."""
    sys.modules.pop("qualityscaler.cli", None)

    vendor_module = types.ModuleType("qualityscaler._vendor")
    vendor_module.__path__ = []
    iso_env_module = types.ModuleType("qualityscaler._vendor.iso_env")

    @dataclass
    class Requirements:
        requirement_text: str
        python_version: str | None = None

    @dataclass
    class IsoEnvArgs:
        venv_path: Path
        build_info: Requirements

    class IsoEnv:
        def __init__(self, args: IsoEnvArgs) -> None:
            self.args = args

        def open_proc(self, command: list[str], env: dict[str, str]) -> Any:
            raise AssertionError("tests should install a fake process")

    iso_env_module.IsoEnv = IsoEnv
    iso_env_module.IsoEnvArgs = IsoEnvArgs
    iso_env_module.Requirements = Requirements

    monkeypatch.setitem(sys.modules, "qualityscaler._vendor", vendor_module)
    monkeypatch.setitem(sys.modules, "qualityscaler._vendor.iso_env", iso_env_module)

    module = importlib.import_module("qualityscaler.cli")
    yield module
    sys.modules.pop("qualityscaler.cli", None)


def test_main_passes_launch_timeout_to_runtime(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    monkeypatch.setenv(cli_module.RUNTIME_TIMEOUT_ENV_VAR, "2.5")

    def fake_run_qualityscaler(timeout_seconds: float | None = None) -> int:
        calls.append(timeout_seconds)
        return 17

    monkeypatch.setattr(cli_module, "run_qualityscaler", fake_run_qualityscaler)

    assert cli_module.main() == 17
    assert calls == [2.5]


def test_runtime_args_use_override_path_and_locked_python(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    runtime_path = tmp_path / "runtime"
    monkeypatch.setenv(cli_module.RUNTIME_ENV_VAR, str(runtime_path))

    args = cli_module._runtime_args()
    self_requirement = args.build_info.requirement_text.splitlines()[0]

    assert args.venv_path == runtime_path
    assert args.build_info.python_version == cli_module.RUNTIME_PYTHON_VERSION
    assert self_requirement.startswith(
        f"{cli_module.PACKAGE_DIST_NAME} @ file:///"
    ) or self_requirement.startswith(f"{cli_module.PACKAGE_DIST_NAME}==")
    assert "torch-directml==0.1.13.1.dev230413" in args.build_info.requirement_text


def test_runtime_process_env_prepends_launcher_scripts_directory(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    scripts_dir = tmp_path / "Scripts"
    scripts_dir.mkdir()
    launcher_python = scripts_dir / "python.exe"
    launcher_python.touch()

    monkeypatch.setattr(cli_module.sys, "executable", str(launcher_python))
    monkeypatch.setenv("PATH", "existing-path")

    env = cli_module._runtime_process_env()

    assert env["PATH"].split(os.pathsep)[0] == str(scripts_dir.resolve())
    assert env["PATH"].endswith("existing-path")


def test_run_qualityscaler_opens_gui_module_in_iso_env(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    open_calls = []
    runtime_args = object()
    runtime_env = {"PATH": "runtime-path"}

    class FakeProcess:
        def __init__(self) -> None:
            self.wait_calls = []

        def wait(self, timeout: float | None = None) -> int:
            self.wait_calls.append(timeout)
            return 23

    process = FakeProcess()

    class FakeIsoEnv:
        def __init__(self, args: object) -> None:
            self.args = args

        def open_proc(self, command: list[str], env: dict[str, str]) -> FakeProcess:
            open_calls.append((self.args, command, env))
            return process

    monkeypatch.setattr(cli_module, "IsoEnv", FakeIsoEnv)
    monkeypatch.setattr(cli_module, "_runtime_args", lambda: runtime_args)
    monkeypatch.setattr(cli_module, "_runtime_process_env", lambda: runtime_env)

    assert cli_module.run_qualityscaler() == 23
    assert open_calls == [
        (
            runtime_args,
            ["python", "-m", "qualityscaler.QualityScaler"],
            runtime_env,
        )
    ]
    assert process.wait_calls == [None]


def test_run_qualityscaler_timeout_terminates_process(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timeout = 0.01
    terminated = []

    class FakeProcess:
        def wait(self, timeout: float | None = None) -> int:
            raise subprocess.TimeoutExpired(["python"], timeout)

    process = FakeProcess()

    class FakeIsoEnv:
        def __init__(self, args: object) -> None:
            self.args = args

        def open_proc(self, command: list[str], env: dict[str, str]) -> FakeProcess:
            return process

    monkeypatch.setattr(cli_module, "IsoEnv", FakeIsoEnv)
    monkeypatch.setattr(cli_module, "_runtime_args", lambda: object())
    monkeypatch.setattr(cli_module, "_runtime_process_env", lambda: {})
    monkeypatch.setattr(
        cli_module,
        "_terminate_process_tree",
        lambda proc: terminated.append(proc),
    )

    assert cli_module.run_qualityscaler(timeout_seconds=timeout) == 0
    assert terminated == [process]
