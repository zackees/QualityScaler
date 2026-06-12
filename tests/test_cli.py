from __future__ import annotations

import datetime as _datetime
import importlib
import io
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

        def open_proc(self, command: list[str], **process_args: Any) -> Any:
            raise AssertionError("tests should install a fake process")

    iso_env_module.IsoEnv = IsoEnv
    iso_env_module.IsoEnvArgs = IsoEnvArgs
    iso_env_module.Requirements = Requirements

    monkeypatch.setitem(sys.modules, "qualityscaler._vendor", vendor_module)
    monkeypatch.setitem(sys.modules, "qualityscaler._vendor.iso_env", iso_env_module)

    module = importlib.import_module("qualityscaler.cli")
    yield module
    sys.modules.pop("qualityscaler.cli", None)


def test_main_ui_passes_launch_timeout_to_runtime(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = []
    monkeypatch.setenv(cli_module.RUNTIME_TIMEOUT_ENV_VAR, "2.5")

    def fake_run_qualityscaler(timeout_seconds: float | None = None) -> int:
        calls.append(timeout_seconds)
        return 17

    monkeypatch.setattr(cli_module, "run_qualityscaler", fake_run_qualityscaler)

    assert cli_module.main(["ui"]) == 17
    assert calls == [2.5]


def test_main_without_args_proxies_to_runtime_cli(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(cli_module, "run_cli", lambda argv: calls.append(argv) or 7)

    assert cli_module.main([]) == 7
    assert calls == [[]]


def test_main_proxies_cli_args_to_runtime_cli(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(cli_module, "run_cli", lambda argv: calls.append(argv) or 0)

    assert cli_module.main(["upscale", "photo.png", "--quiet"]) == 0
    assert calls == [["upscale", "photo.png", "--quiet"]]


def test_main_uses_sys_argv_when_argv_omitted(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(cli_module, "run_cli", lambda argv: calls.append(argv) or 3)
    monkeypatch.setattr(cli_module.sys, "argv", ["qualityscaler", "models"])

    assert cli_module.main() == 3
    assert calls == [["models"]]


def test_run_cli_executes_cli_runtime_module_and_propagates_exit_code(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    open_calls: list[tuple[object, list[str], dict[str, Any]]] = []
    process = _FakeProcess(returncode=5)
    _install_fake_iso_env(cli_module, monkeypatch, process, open_calls)

    assert cli_module.run_cli(["upscale", "photo.png", "-m", "RealESR_Gx4"]) == 5

    assert len(open_calls) == 1
    _, command, process_args = open_calls[0]
    assert command == ["python", "-u", "-m", "qualityscaler.cli_runtime", "upscale", "photo.png", "-m", "RealESR_Gx4"]
    assert process_args["env"] == {"PATH": "x"}
    assert "stdout" not in process_args
    assert "stderr" not in process_args


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
    assert "onnxruntime-directml==1.24.4" in args.build_info.requirement_text
    assert "torch-directml" not in args.build_info.requirement_text


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


class _FakeProcess:
    """Stand-in for ``subprocess.Popen`` exposing just what the launcher uses."""

    def __init__(
        self,
        stdout_bytes: bytes = b"",
        returncode: int = 0,
        raise_timeout: bool = False,
    ) -> None:
        self.stdout = io.BytesIO(stdout_bytes)
        self._returncode = returncode
        self._raise_timeout = raise_timeout
        self.wait_calls: list[float | None] = []

    def wait(self, timeout: float | None = None) -> int:
        self.wait_calls.append(timeout)
        if self._raise_timeout:
            raise subprocess.TimeoutExpired(["python"], timeout)
        return self._returncode

    def poll(self) -> int | None:
        return self._returncode


def _install_fake_iso_env(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    process: _FakeProcess,
    open_calls: list[tuple[object, list[str], dict[str, Any]]] | None = None,
) -> None:
    class FakeIsoEnv:
        def __init__(self, args: object) -> None:
            self.args = args

        def open_proc(
            self, command: list[str], **process_args: Any
        ) -> _FakeProcess:
            if open_calls is not None:
                open_calls.append((self.args, command, process_args))
            return process

    monkeypatch.setattr(cli_module, "IsoEnv", FakeIsoEnv)
    monkeypatch.setattr(cli_module, "_runtime_args", lambda: object())
    monkeypatch.setattr(cli_module, "_runtime_process_env", lambda: {"PATH": "x"})


def test_run_qualityscaler_pipes_subprocess_output_to_log_file(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    open_calls: list[tuple[object, list[str], dict[str, Any]]] = []
    process = _FakeProcess(stdout_bytes=b"hello from gui\n")
    _install_fake_iso_env(cli_module, monkeypatch, process, open_calls)

    monkeypatch.setenv(cli_module.RUNTIME_LOG_DIR_ENV_VAR, str(tmp_path))

    assert cli_module.run_qualityscaler() == 0

    assert len(open_calls) == 1
    _, command, process_args = open_calls[0]
    assert command == ["python", "-u", "-m", "qualityscaler.QualityScaler"]
    assert process_args["stdout"] is subprocess.PIPE
    assert process_args["stderr"] == subprocess.STDOUT

    log_files = list(tmp_path.glob("launch-*.log"))
    assert len(log_files) == 1
    assert log_files[0].read_bytes() == b"hello from gui\n"


def test_run_qualityscaler_reports_failure_with_log_tail(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    crash_output = (
        b"Traceback (most recent call last):\n"
        b"  File \"<stdin>\", line 1\n"
        b"ImportError: numpy.core.multiarray failed to import\n"
    )
    process = _FakeProcess(stdout_bytes=crash_output, returncode=1)
    _install_fake_iso_env(cli_module, monkeypatch, process)
    monkeypatch.setenv(cli_module.RUNTIME_LOG_DIR_ENV_VAR, str(tmp_path))

    assert cli_module.run_qualityscaler() == 1

    err = capsys.readouterr().err
    assert "QualityScaler GUI exited with code 1" in err
    assert "ImportError: numpy.core.multiarray failed to import" in err
    log_files = list(tmp_path.glob("launch-*.log"))
    assert len(log_files) == 1
    assert str(log_files[0]) in err


def test_run_qualityscaler_timeout_terminates_process(
    cli_module: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    terminated: list[object] = []
    process = _FakeProcess(raise_timeout=True)
    _install_fake_iso_env(cli_module, monkeypatch, process)
    monkeypatch.setenv(cli_module.RUNTIME_LOG_DIR_ENV_VAR, str(tmp_path))
    monkeypatch.setattr(
        cli_module,
        "_terminate_process_tree",
        lambda proc: terminated.append(proc),
    )

    assert cli_module.run_qualityscaler(timeout_seconds=0.01) == 0
    assert terminated == [process]


def test_default_log_dir_honors_override(
    cli_module: Any,
    tmp_path: Path,
) -> None:
    override = tmp_path / "custom-logs"
    env = {cli_module.RUNTIME_LOG_DIR_ENV_VAR: str(override)}

    assert cli_module._default_log_dir(env=env) == override


def test_default_log_dir_uses_platform_default_when_unset(
    cli_module: Any,
) -> None:
    log_dir = cli_module._default_log_dir(env={})
    assert log_dir.parts[-2:] == ("QualityScaler", "logs")


def test_new_log_path_is_timestamped_and_unique(
    cli_module: Any,
    tmp_path: Path,
) -> None:
    fixed_now = _datetime.datetime(2026, 6, 2, 12, 34, 56)
    path = cli_module._new_log_path(tmp_path, now=fixed_now)

    assert path.parent == tmp_path
    assert path.name.startswith("launch-20260602-123456-")
    assert path.suffix == ".log"


def test_format_failure_message_includes_tail(
    cli_module: Any,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "launch.log"
    message = cli_module._format_failure_message(
        returncode=1,
        log_path=log_path,
        tail="line1\nline2",
    )
    assert "exited with code 1" in message
    assert str(log_path) in message
    assert "line1\nline2" in message


def test_tail_text_keeps_only_last_lines(cli_module: Any) -> None:
    text = "\n".join(str(i) for i in range(100))
    tail = cli_module._tail_text(text, max_lines=5)
    assert tail.splitlines() == ["95", "96", "97", "98", "99"]


def test_tee_stream_writes_to_all_destinations(cli_module: Any) -> None:
    src = io.BytesIO(b"abc" * 2000)
    dest_a = io.BytesIO()
    dest_b = io.BytesIO()

    cli_module._tee_stream(src, [dest_a, dest_b])

    expected = b"abc" * 2000
    assert dest_a.getvalue() == expected
    assert dest_b.getvalue() == expected


def test_runtime_python_version_has_wheels_for_all_pins(cli_module: Any) -> None:
    """onnxruntime-directml 1.24.4 ships cp311+ only; pillow 9.5.0 tops out at cp311."""
    assert cli_module.RUNTIME_PYTHON_VERSION == "==3.11.*"


def test_runtime_lock_pins_numpy_below_2(cli_module: Any) -> None:
    """Keep the ONNX Runtime / OpenCV stack on NumPy 1.x."""
    lock_text = cli_module._runtime_lock_text()
    assert "numpy==1.26.4" in lock_text
    assert "numpy==2." not in lock_text


def test_runtime_lock_pins_opencv_before_numpy2_requirement(cli_module: Any) -> None:
    """opencv-python-headless 4.12+ requires numpy 2.x."""
    lock_text = cli_module._runtime_lock_text()
    assert "opencv-python-headless==4.11.0.86" in lock_text
    assert "opencv-python-headless==4.12" not in lock_text
    assert "opencv-python-headless==4.13" not in lock_text


def test_runtime_lock_includes_pillow_for_app_images(cli_module: Any) -> None:
    lock_text = cli_module._runtime_lock_text()
    assert "pillow==" in lock_text
    assert "moviepy==" not in lock_text
    assert "imageio==" not in lock_text
    assert "imageio-ffmpeg==" not in lock_text


def test_runtime_lock_includes_static_ffmpeg(cli_module: Any) -> None:
    lock_text = cli_module._runtime_lock_text()
    assert "static-ffmpeg==3.0" in lock_text


def test_runtime_lock_uses_onnxruntime_directml_stack(cli_module: Any) -> None:
    lock_text = cli_module._runtime_lock_text()
    assert "onnx==" not in lock_text
    assert "onnxconverter-common==" not in lock_text
    assert "ml-dtypes==" not in lock_text
    assert "natsort==8.4.0" in lock_text
    assert "onnxoptimizer==" not in lock_text
    assert "onnxruntime-directml==1.24.4" in lock_text
    assert "psutil==7.2.2" in lock_text
    assert "moviepy==" not in lock_text
    assert "torch==" not in lock_text


def test_is_checkout_root_detects_quality_scaler_checkout(cli_module: Any, tmp_path: Path) -> None:
    (tmp_path / "src" / "qualityscaler").mkdir(parents=True)
    (tmp_path / "src" / "qualityscaler" / "QualityScaler.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "quality_scaler"\n', encoding="utf-8")

    assert cli_module._is_checkout_root(tmp_path)


def test_is_checkout_root_rejects_other_projects(cli_module: Any, tmp_path: Path) -> None:
    (tmp_path / "src" / "qualityscaler").mkdir(parents=True)
    (tmp_path / "src" / "qualityscaler" / "QualityScaler.py").write_text("", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "other_project"\n', encoding="utf-8")

    assert not cli_module._is_checkout_root(tmp_path)


def test_source_checkout_root_uses_cwd_when_module_in_site_packages(cli_module: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """pip install . then running from the repo must use local code, not PyPI."""
    fake_site = tmp_path / "site-packages" / "qualityscaler"
    fake_site.mkdir(parents=True)
    monkeypatch.setattr(cli_module, "__file__", str(fake_site / "cli.py"))

    checkout = tmp_path / "repo"
    (checkout / "src" / "qualityscaler").mkdir(parents=True)
    (checkout / "src" / "qualityscaler" / "QualityScaler.py").write_text("", encoding="utf-8")
    (checkout / "pyproject.toml").write_text('[project]\nname = "quality_scaler"\n', encoding="utf-8")
    monkeypatch.chdir(checkout)

    assert cli_module._source_checkout_root() == checkout.resolve()
    assert cli_module._self_requirement().startswith("quality-scaler @ file://")


def test_self_requirement_repacks_installed_wheel_outside_checkout(
    cli_module: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Outside a checkout the runtime must install the re-packed local wheel,
    never `quality-scaler==<version>` from the index (see #55)."""
    wheel_path = tmp_path / "self-wheel" / "quality_scaler-9.9.9-012345678-py3-none-any.whl"
    cache_dirs: list[Path] = []

    def fake_build_installed_wheel(cache_dir: Path) -> Path:
        cache_dirs.append(cache_dir)
        return wheel_path

    monkeypatch.setattr(cli_module, "_source_checkout_root", lambda: None)
    monkeypatch.setattr(cli_module, "build_installed_wheel", fake_build_installed_wheel)
    monkeypatch.setenv(cli_module.RUNTIME_ENV_VAR, str(tmp_path / "runtime"))

    assert cli_module._self_requirement() == f"quality-scaler @ {wheel_path.as_uri()}"
    assert cache_dirs == [tmp_path / "self-wheel"]


def test_self_requirement_falls_back_to_version_pin_when_repack_fails(
    cli_module: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_module, "_source_checkout_root", lambda: None)
    monkeypatch.setattr(cli_module, "build_installed_wheel", lambda cache_dir: None)
    monkeypatch.setattr(cli_module, "version", lambda name: "1.2.3")
    monkeypatch.setenv(cli_module.RUNTIME_ENV_VAR, str(tmp_path / "runtime"))

    assert cli_module._self_requirement() == "quality-scaler==1.2.3"
