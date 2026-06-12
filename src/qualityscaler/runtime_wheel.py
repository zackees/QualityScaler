"""Re-pack the installed quality-scaler distribution into a wheel.

When the launcher runs outside a source checkout it cannot assume that the
index wheel at the installed version matches the local code: a manual
``pip install .`` produces a local-only build under a version number that may
also exist on PyPI with different (older) contents (see #55). Rebuilding a
wheel from the files the running launcher was actually installed from
guarantees the managed runtime executes the same code.
"""

from __future__ import annotations

import base64
import hashlib
import zipfile
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from pathlib import Path

_DIST_NAMES = ("quality_scaler", "quality-scaler")
# Installer-generated files that must not appear inside a wheel.
_EXCLUDED_DIST_INFO_FILES = {"RECORD", "RECORD.jws", "RECORD.p7s", "INSTALLER", "REQUESTED", "direct_url.json"}
_REQUIRED_MEMBERS = ("qualityscaler/__init__.py", "qualityscaler/cli_runtime.py")


def _installed_distribution() -> Distribution | None:
    for name in _DIST_NAMES:
        try:
            return distribution(name)
        except PackageNotFoundError:
            continue
    return None


def _archive_name(parts: tuple[str, ...]) -> str | None:
    """Map an installed file to its in-wheel path, or None to skip it."""
    if not parts or ".." in parts or "__pycache__" in parts:
        return None
    if parts[-1].endswith(".pyc"):
        return None
    if parts[0].endswith(".dist-info"):
        if len(parts) == 2 and parts[1] in _EXCLUDED_DIST_INFO_FILES:
            return None
        return "/".join(parts)
    if parts[0] != "qualityscaler":
        return None
    return "/".join(parts)


def _collect_members(dist: Distribution) -> dict[str, bytes] | None:
    """Read every wheel member into memory, or None if the installed layout
    cannot be re-packed (editable installs, files missing on disk)."""
    files = dist.files
    if not files:
        return None

    members: dict[str, bytes] = {}
    for package_path in files:
        # RECORD entries may use either path separator depending on installer.
        parts = tuple(part for part in str(package_path).replace("\\", "/").split("/") if part)
        name = _archive_name(parts)
        if name is None:
            continue
        source = Path(str(dist.locate_file(package_path)))
        try:
            members[name] = source.read_bytes()
        except OSError:
            return None

    if any(required not in members for required in _REQUIRED_MEMBERS):
        return None
    dist_info_dirs = {name.split("/", 1)[0] for name in members if name.split("/", 1)[0].endswith(".dist-info")}
    if len(dist_info_dirs) != 1 or f"{next(iter(dist_info_dirs))}/METADATA" not in members:
        return None
    return members


def _content_build_tag(members: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(members):
        digest.update(name.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(hashlib.sha256(members[name]).digest())
    # Build tags must start with a digit (PEP 427).
    return "0" + digest.hexdigest()[:12]


def _record_hash(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode("ascii")


def build_installed_wheel(cache_dir: Path, dist: Distribution | None = None) -> Path | None:
    """Build a wheel from the installed distribution into ``cache_dir``.

    Returns the wheel path, or None when the installed distribution cannot be
    re-packed (not installed, editable install, or incomplete files); callers
    should then fall back to another requirement source.
    """
    dist = dist if dist is not None else _installed_distribution()
    if dist is None:
        return None
    members = _collect_members(dist)
    if members is None:
        return None

    build_tag = _content_build_tag(members)
    wheel_path = cache_dir / f"quality_scaler-{dist.version}-{build_tag}-py3-none-any.whl"
    if wheel_path.exists():
        return wheel_path

    cache_dir.mkdir(parents=True, exist_ok=True)
    for stale in cache_dir.glob("quality_scaler-*.whl"):
        try:
            stale.unlink()
        except OSError:
            pass

    dist_info_dir = next(name.split("/", 1)[0] for name in members if name.split("/", 1)[0].endswith(".dist-info"))
    record_name = f"{dist_info_dir}/RECORD"
    temp_path = wheel_path.with_name(wheel_path.name + ".tmp")
    with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as wheel:
        record_lines = []
        for name in sorted(members):
            data = members[name]
            wheel.writestr(name, data)
            record_lines.append(f"{name},sha256={_record_hash(data)},{len(data)}")
        record_lines.append(f"{record_name},,")
        wheel.writestr(record_name, "\n".join(record_lines) + "\n")
    temp_path.replace(wheel_path)
    return wheel_path
