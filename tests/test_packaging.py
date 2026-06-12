"""Packaging guards: uv cache invalidation and wheel completeness (see #53).

The managed runtime installs ``quality-scaler @ file://<checkout>``; without
``tool.uv.cache-keys`` covering ``src/**`` uv reuses a stale cached wheel when
only source files change, so the GUI silently runs old code.
"""

from __future__ import annotations

import subprocess
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"


def test_pyproject_declares_uv_cache_keys() -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    assert "[tool.uv]" in text
    assert "cache-keys" in text
    assert 'file = "src/**/*.py"' in text
    assert 'file = "pyproject.toml"' in text


@pytest.mark.integration
def test_wheel_contains_all_packages(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    wheels = list(tmp_path.glob("*.whl"))
    assert len(wheels) == 1

    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())

    expected = [
        "qualityscaler/QualityScaler.py",
        "qualityscaler/cli.py",
        "qualityscaler/cli_runtime.py",
        "qualityscaler/runtime_wheel.py",
        "qualityscaler/requirements.runtime.lock.txt",
        "qualityscaler/core/pipeline.py",
        "qualityscaler/gui/app.py",
        "qualityscaler/gui/ff_panel.py",
        "qualityscaler/fluidframes/pipeline.py",
        "qualityscaler/_vendor/iso_env/api.py",
    ]
    missing = [name for name in expected if name not in names]
    assert not missing, f"wheel is missing: {missing}"
