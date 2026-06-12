from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def app_version() -> str:
    for distribution_name in ("quality-scaler", "quality_scaler"):
        try:
            return version(distribution_name)
        except PackageNotFoundError:
            continue
    return "0.0.0-dev"
