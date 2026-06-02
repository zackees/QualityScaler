"""
QualityScaler launcher.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files
from pathlib import Path

from qualityscaler._vendor.iso_env import IsoEnv, IsoEnvArgs, Requirements

RUNTIME_ENV_VAR = "QUALITYSCALER_RUNTIME_ENV"
RUNTIME_TIMEOUT_ENV_VAR = "QUALITYSCALER_LAUNCH_TIMEOUT_SECONDS"
RUNTIME_PYTHON_VERSION = "==3.10.*"
RUNTIME_LOCK_FILE = "requirements.runtime.lock.txt"
PACKAGE_DIST_NAME = "quality-scaler"
PACKAGE_MODULE_NAME = "quality_scaler"


def _source_checkout_root() -> Path | None:
    """Return the repo root when this package is running from a checkout."""
    root = Path(__file__).resolve().parents[2]
    pyproject = root / "pyproject.toml"
    source_file = root / "src" / "qualityscaler" / "QualityScaler.py"
    if pyproject.exists() and source_file.exists():
        return root
    return None


def _self_requirement() -> str:
    checkout_root = _source_checkout_root()
    if checkout_root is not None:
        return f"{PACKAGE_DIST_NAME} @ {checkout_root.as_uri()}"

    try:
        installed_version = version(PACKAGE_MODULE_NAME)
    except PackageNotFoundError:
        installed_version = version(PACKAGE_DIST_NAME)
    return f"{PACKAGE_DIST_NAME}=={installed_version}"


def _runtime_lock_text() -> str:
    lock_resource = files("qualityscaler").joinpath(RUNTIME_LOCK_FILE)
    lock_text = lock_resource.read_text(encoding="utf-8").strip()
    return f"{_self_requirement()}\n{lock_text}"


def _default_runtime_env_path() -> Path:
    override = os.environ.get(RUNTIME_ENV_VAR)
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "QualityScaler" / "runtime-py310"


def _runtime_process_env() -> dict[str, str]:
    env = dict(os.environ)
    scripts_dir = Path(sys.executable).resolve().parent
    env["PATH"] = f"{scripts_dir}{os.pathsep}{env.get('PATH', '')}"
    return env


@contextmanager
def _parent_runtime_path(env: dict[str, str]) -> Iterator[None]:
    original_path = os.environ.get("PATH")
    os.environ["PATH"] = env.get("PATH", original_path or "")
    try:
        yield
    finally:
        if original_path is None:
            os.environ.pop("PATH", None)
        else:
            os.environ["PATH"] = original_path


def _runtime_args() -> IsoEnvArgs:
    return IsoEnvArgs(
        venv_path=_default_runtime_env_path(),
        build_info=Requirements(_runtime_lock_text(), python_version=RUNTIME_PYTHON_VERSION),
    )


def _timeout_seconds() -> float | None:
    timeout = os.environ.get(RUNTIME_TIMEOUT_ENV_VAR)
    if not timeout:
        return None
    return float(timeout)


def _terminate_process_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


def run_qualityscaler(timeout_seconds: float | None = None) -> int:
    """Run the GUI inside the managed runtime environment."""
    iso = IsoEnv(_runtime_args())
    runtime_env = _runtime_process_env()
    with _parent_runtime_path(runtime_env):
        proc = iso.open_proc(
            ["python", "-m", "qualityscaler.QualityScaler"],
            env=runtime_env,
        )
    if timeout_seconds is None:
        return proc.wait()
    try:
        return proc.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _terminate_process_tree(proc)
        return 0


def main() -> int:
    """Launch QualityScaler in its isolated Python 3.10 runtime."""
    return run_qualityscaler(timeout_seconds=_timeout_seconds())


if __name__ == "__main__":
    sys.exit(main())
