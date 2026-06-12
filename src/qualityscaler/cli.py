"""
QualityScaler launcher.
"""

from __future__ import annotations

import datetime as _datetime
import os
import subprocess
import sys
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files
from pathlib import Path
from typing import IO

from qualityscaler._vendor.iso_env import IsoEnv, IsoEnvArgs, Requirements
from qualityscaler.runtime_wheel import build_installed_wheel

RUNTIME_ENV_VAR = "QUALITYSCALER_RUNTIME_ENV"
RUNTIME_TIMEOUT_ENV_VAR = "QUALITYSCALER_LAUNCH_TIMEOUT_SECONDS"
RUNTIME_LOG_DIR_ENV_VAR = "QUALITYSCALER_LOG_DIR"
# 3.11 is the only version with wheels for every runtime pin:
# onnxruntime-directml 1.24.4 ships cp311+ only; pillow 9.5.0 ships up to cp311.
RUNTIME_PYTHON_VERSION = "==3.11.*"
RUNTIME_LOCK_FILE = "requirements.runtime.lock.txt"
PACKAGE_DIST_NAME = "quality-scaler"
PACKAGE_MODULE_NAME = "quality_scaler"
LOG_TAIL_LINES = 40


def _is_checkout_root(root: Path) -> bool:
    pyproject = root / "pyproject.toml"
    source_file = root / "src" / "qualityscaler" / "QualityScaler.py"
    if not (pyproject.exists() and source_file.exists()):
        return False
    try:
        pyproject_text = pyproject.read_text(encoding="utf-8")
    except OSError:
        return False
    return 'name = "quality_scaler"' in pyproject_text


def _source_checkout_root() -> Path | None:
    """Return the repo root when running from a checkout.

    Checks the module location first (editable installs), then the current
    working directory and its parents (``pip install .`` run from the repo,
    where the module lives in site-packages but local code may be newer than
    the published wheel at the same version).
    """
    cwd = Path.cwd().resolve()
    for root in (Path(__file__).resolve().parents[2], cwd, *cwd.parents):
        if _is_checkout_root(root):
            return root
    return None


def _self_wheel_cache_dir() -> Path:
    return _default_runtime_env_path().parent / "self-wheel"


def _self_requirement() -> str:
    checkout_root = _source_checkout_root()
    if checkout_root is not None:
        return f"{PACKAGE_DIST_NAME} @ {checkout_root.as_uri()}"

    # Outside a checkout the index wheel at the installed version may be a
    # different (older) artifact than the locally installed code (see #55),
    # so re-pack the installed distribution instead of trusting the index.
    wheel_path = build_installed_wheel(_self_wheel_cache_dir())
    if wheel_path is not None:
        return f"{PACKAGE_DIST_NAME} @ {wheel_path.as_uri()}"

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
    return base / "QualityScaler" / "runtime-py311"


def _default_log_dir(env: Mapping[str, str] | None = None) -> Path:
    """Return the directory where launch logs are written."""
    env = env if env is not None else os.environ
    override = env.get(RUNTIME_LOG_DIR_ENV_VAR)
    if override:
        return Path(override).expanduser()

    if os.name == "nt":
        base = Path(env.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    else:
        base = Path(env.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))
    return base / "QualityScaler" / "logs"


def _new_log_path(log_dir: Path, now: _datetime.datetime | None = None) -> Path:
    """Return a fresh, timestamped log file path under ``log_dir``."""
    now = now if now is not None else _datetime.datetime.now()
    return log_dir / f"launch-{now.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}.log"


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


def _tee_stream(src: IO[bytes], destinations: list[IO[bytes]]) -> None:
    """Copy bytes from ``src`` to every destination until ``src`` reaches EOF."""
    while True:
        chunk = src.read(4096)
        if not chunk:
            break
        for dest in destinations:
            try:
                dest.write(chunk)
                dest.flush()
            except (BrokenPipeError, ValueError):
                pass


def _format_failure_message(returncode: int, log_path: Path, tail: str) -> str:
    header = (
        f"QualityScaler GUI exited with code {returncode}. "
        f"Full log: {log_path}"
    )
    if not tail.strip():
        return header + "\n"
    return f"{header}\n--- last {LOG_TAIL_LINES} log lines ---\n{tail}\n--- end ---\n"


def _tail_text(text: str, max_lines: int = LOG_TAIL_LINES) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text.rstrip("\n")
    return "\n".join(lines[-max_lines:])


def _read_log_tail(log_path: Path, max_lines: int = LOG_TAIL_LINES) -> str:
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return _tail_text(text, max_lines)


def run_qualityscaler(timeout_seconds: float | None = None) -> int:
    """Run the GUI inside the managed runtime environment."""
    iso = IsoEnv(_runtime_args())
    runtime_env = _runtime_process_env()
    log_dir = _default_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = _new_log_path(log_dir)

    with _parent_runtime_path(runtime_env), log_path.open("wb") as log_file:
        proc = iso.open_proc(
            ["python", "-u", "-m", "qualityscaler.QualityScaler"],
            env=runtime_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
        )
        parent_stdout = getattr(sys.stdout, "buffer", sys.stdout)
        tee_thread = threading.Thread(
            target=_tee_stream,
            args=(proc.stdout, [log_file, parent_stdout]),
            daemon=True,
        )
        tee_thread.start()

        try:
            if timeout_seconds is None:
                returncode = proc.wait()
            else:
                try:
                    returncode = proc.wait(timeout=timeout_seconds)
                except subprocess.TimeoutExpired:
                    _terminate_process_tree(proc)
                    returncode = 0
        finally:
            tee_thread.join(timeout=5)

    if returncode != 0:
        tail = _read_log_tail(log_path)
        sys.stderr.write(_format_failure_message(returncode, log_path, tail))
        sys.stderr.flush()
    return returncode


def run_cli(argv: list[str]) -> int:
    """Proxy CLI arguments into the managed runtime environment."""
    iso = IsoEnv(_runtime_args())
    runtime_env = _runtime_process_env()
    with _parent_runtime_path(runtime_env):
        proc = iso.open_proc(
            ["python", "-u", "-m", "qualityscaler.cli_runtime", *argv],
            env=runtime_env,
        )
        return proc.wait()


def main(argv: list[str] | None = None) -> int:
    """Dispatch to the GUI (``ui`` subcommand) or proxy to the runtime CLI."""
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    if argv and argv[0] == "ui":
        return run_qualityscaler(timeout_seconds=_timeout_seconds())
    return run_cli(argv)


if __name__ == "__main__":
    sys.exit(main())
