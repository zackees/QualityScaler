"""Asset paths and on-demand download, kept free of any GUI toolkit imports."""

import sys
from os.path import (
    dirname as os_path_dirname,
    abspath as os_path_abspath,
    join as os_path_join,
    exists as os_path_exists,
)

# Anchor paths to the qualityscaler package root (one level above gui/),
# matching where QualityScaler.py historically lived.
_PACKAGE_ROOT = os_path_dirname(os_path_dirname(os_path_abspath(__file__)))


def find_by_relative_path(relative_path: str) -> str:
    return os_path_join(getattr(sys, '_MEIPASS', _PACKAGE_ROOT), relative_path)


HERE = _PACKAGE_ROOT

ASSETS_ZIP_URL = "https://github.com/zackees/QualityScaler/raw/main/assets.zip"
ASSETS_TARGET_DIR = os_path_join(HERE, "Assets")
ASSETS_TARGET_ZIP = os_path_join(HERE, "assets.zip")


def ensure_assets() -> None:
    if os_path_exists(ASSETS_TARGET_DIR):
        return
    from shutil import unpack_archive as shutil_unpack_archive

    from download import download

    download(ASSETS_ZIP_URL, ASSETS_TARGET_ZIP, replace=True, kind="file", timeout=60 * 5)
    shutil_unpack_archive(ASSETS_TARGET_ZIP, ASSETS_TARGET_DIR)
