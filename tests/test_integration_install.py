"""Network-dependent install checks. Run with ``pytest -m integration``."""

from __future__ import annotations

import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def test_runtime_lock_resolves_for_runtime_python(tmp_path) -> None:
    """Dry-run resolve of the real runtime requirements.

    A pin without a wheel for RUNTIME_PYTHON_VERSION on Windows (the #37
    failure: onnxruntime-directml had no cp310 wheel) makes this fail without
    downloading or installing anything.
    """
    from qualityscaler import cli

    python_version = cli.RUNTIME_PYTHON_VERSION.removeprefix("==").removesuffix(".*")
    requirements_in = tmp_path / "requirements.in"
    requirements_in.write_text(cli._runtime_lock_text(), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "uv",
            "pip",
            "compile",
            str(requirements_in),
            "--python-version",
            python_version,
            "--python-platform",
            "windows",
            "--no-header",
            "--output-file",
            str(tmp_path / "resolved.txt"),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )

    assert result.returncode == 0, f"runtime lock does not resolve:\n{result.stderr}"
    resolved = (tmp_path / "resolved.txt").read_text(encoding="utf-8")
    assert "onnxruntime-directml" in resolved
