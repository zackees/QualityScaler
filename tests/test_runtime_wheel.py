"""Tests for re-packing the installed distribution into a wheel (see #55)."""

from __future__ import annotations

import base64
import hashlib
import zipfile
from importlib.metadata import Distribution
from pathlib import Path

from qualityscaler.runtime_wheel import build_installed_wheel

METADATA = "Metadata-Version: 2.1\nName: quality-scaler\nVersion: 9.9.9\n"
WHEEL = "Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n"


def make_installed_dist(
    site: Path,
    extra_files: dict[str, str] | None = None,
    package_files: dict[str, str] | None = None,
) -> Distribution:
    """Lay out a pip-style installed distribution and return it."""
    if package_files is None:
        package_files = {
            "qualityscaler/__init__.py": "",
            "qualityscaler/cli_runtime.py": "print('cli')\n",
            "qualityscaler/core/pipeline.py": "print('core')\n",
            "qualityscaler/requirements.runtime.lock.txt": "filelock==3.13.0\n",
        }
    dist_info = "quality_scaler-9.9.9.dist-info"
    files = {
        **package_files,
        f"{dist_info}/METADATA": METADATA,
        f"{dist_info}/WHEEL": WHEEL,
        f"{dist_info}/entry_points.txt": "[console_scripts]\nquality-scaler = qualityscaler.cli:main\n",
        f"{dist_info}/top_level.txt": "qualityscaler\n",
        f"{dist_info}/INSTALLER": "pip\n",
        f"{dist_info}/REQUESTED": "",
        f"{dist_info}/direct_url.json": "{}",
        "qualityscaler/__pycache__/__init__.cpython-313.pyc": "bytecode",
        **(extra_files or {}),
    }
    record_rows = []
    for name, content in files.items():
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        record_rows.append(f"{name},,")
    record_rows.append(f"{dist_info}/RECORD,,")
    record_rows.append("../../Scripts/quality-scaler.exe,,")
    (site / dist_info / "RECORD").write_text("\n".join(record_rows) + "\n", encoding="utf-8")
    return Distribution.at(site / dist_info)


def test_build_wheel_contains_package_and_metadata(tmp_path: Path) -> None:
    dist = make_installed_dist(tmp_path / "site")

    wheel_path = build_installed_wheel(tmp_path / "wheels", dist=dist)

    assert wheel_path is not None
    assert wheel_path.name.startswith("quality_scaler-9.9.9-0")
    assert wheel_path.name.endswith("-py3-none-any.whl")
    with zipfile.ZipFile(wheel_path) as wheel:
        names = set(wheel.namelist())
    assert "qualityscaler/cli_runtime.py" in names
    assert "qualityscaler/core/pipeline.py" in names
    assert "quality_scaler-9.9.9.dist-info/METADATA" in names
    assert "quality_scaler-9.9.9.dist-info/WHEEL" in names
    assert "quality_scaler-9.9.9.dist-info/entry_points.txt" in names
    assert "quality_scaler-9.9.9.dist-info/RECORD" in names


def test_build_wheel_excludes_installer_artifacts(tmp_path: Path) -> None:
    dist = make_installed_dist(tmp_path / "site")

    wheel_path = build_installed_wheel(tmp_path / "wheels", dist=dist)

    assert wheel_path is not None
    with zipfile.ZipFile(wheel_path) as wheel:
        names = set(wheel.namelist())
    assert "quality_scaler-9.9.9.dist-info/INSTALLER" not in names
    assert "quality_scaler-9.9.9.dist-info/REQUESTED" not in names
    assert "quality_scaler-9.9.9.dist-info/direct_url.json" not in names
    assert not any("__pycache__" in name for name in names)
    assert not any(name.endswith(".exe") for name in names)


def test_build_wheel_record_hashes_are_valid(tmp_path: Path) -> None:
    dist = make_installed_dist(tmp_path / "site")

    wheel_path = build_installed_wheel(tmp_path / "wheels", dist=dist)

    assert wheel_path is not None
    with zipfile.ZipFile(wheel_path) as wheel:
        record_text = wheel.read("quality_scaler-9.9.9.dist-info/RECORD").decode("utf-8")
        for row in record_text.strip().splitlines():
            name, digest, size = row.rsplit(",", 2)
            data = wheel.read(name)
            if not digest:
                continue
            expected = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")
            assert digest == f"sha256={expected}"
            assert int(size) == len(data)


def test_build_wheel_is_idempotent_and_prunes_stale_wheels(tmp_path: Path) -> None:
    site = tmp_path / "site"
    wheels = tmp_path / "wheels"
    dist = make_installed_dist(site)

    first = build_installed_wheel(wheels, dist=dist)
    second = build_installed_wheel(wheels, dist=dist)
    assert first is not None
    assert first == second

    (site / "qualityscaler" / "cli_runtime.py").write_text("print('changed')\n", encoding="utf-8")
    third = build_installed_wheel(wheels, dist=Distribution.at(site / "quality_scaler-9.9.9.dist-info"))

    assert third is not None
    assert third != first
    assert list(wheels.glob("*.whl")) == [third]


def test_build_wheel_returns_none_for_editable_layout(tmp_path: Path) -> None:
    site = tmp_path / "site"
    dist_info = "quality_scaler-9.9.9.dist-info"
    (site / dist_info).mkdir(parents=True)
    (site / dist_info / "METADATA").write_text(METADATA, encoding="utf-8")
    (site / dist_info / "WHEEL").write_text(WHEEL, encoding="utf-8")
    (site / "__editable__.quality_scaler-9.9.9.pth").write_text("/checkout/src", encoding="utf-8")
    record = f"{dist_info}/METADATA,,\n{dist_info}/WHEEL,,\n{dist_info}/RECORD,,\n__editable__.quality_scaler-9.9.9.pth,,\n"
    (site / dist_info / "RECORD").write_text(record, encoding="utf-8")

    assert build_installed_wheel(tmp_path / "wheels", dist=Distribution.at(site / dist_info)) is None


def test_build_wheel_returns_none_when_files_missing_on_disk(tmp_path: Path) -> None:
    site = tmp_path / "site"
    dist = make_installed_dist(site)
    (site / "qualityscaler" / "cli_runtime.py").unlink()

    assert build_installed_wheel(tmp_path / "wheels", dist=dist) is None


def test_build_wheel_returns_none_when_not_installed(tmp_path: Path, monkeypatch) -> None:
    import qualityscaler.runtime_wheel as runtime_wheel

    monkeypatch.setattr(runtime_wheel, "_installed_distribution", lambda: None)
    assert build_installed_wheel(tmp_path / "wheels") is None
