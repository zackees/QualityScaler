"""Headless tests for qualityscaler.app.media_info.

The module keeps its cv2/numpy imports lazy, so the pure helpers
(extension detection, resolution-projection formatting) are testable
without OpenCV installed.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from qualityscaler.app.media_info import (
    check_if_file_is_video,
    format_resolution_projection,
)

MEDIA_INFO_SOURCE = Path(__file__).resolve().parent.parent / "src" / "qualityscaler" / "gui" / "media_info.py"


@pytest.mark.parametrize(
    "file_path, expected",
    [
        ("movie.mp4", True),
        ("clip.MKV".lower(), True),
        ("C:/videos/holiday.avi", True),
        ("photo.png", False),
        ("photo.jpg", False),
        ("notes.txt", False),
    ],
)
def test_check_if_file_is_video(file_path: str, expected: bool) -> None:
    assert check_if_file_is_video(file_path) == expected


def test_projection_matches_legacy_arithmetic() -> None:
    # 1920x1080 at 50% input, x2 model, 100% output
    text = format_resolution_projection(1920, 1080, 2, 50, 100)
    assert text == (
        "AI input (50%)\t= 960x540\n"
        "AI output (x2)\t= 1920x1080\n"
        "File output (100%)\t= 1920x1080"
    )


def test_projection_truncates_like_int_cast() -> None:
    # 333x333 at 33% must use int() truncation, not rounding
    text = format_resolution_projection(333, 333, 4, 33, 75)
    input_w = int(333 * 0.33)          # 109
    upscaled_w = input_w * 4           # 436
    output_w = int(upscaled_w * 0.75)  # 327
    assert f"= {input_w}x{input_w}" in text
    assert f"= {upscaled_w}x{upscaled_w}" in text
    assert f"= {output_w}x{output_w}" in text


@pytest.mark.parametrize("factors", [(0, 50, 100), (2, 0, 100), (2, 50, 0)])
def test_projection_empty_when_any_factor_unset(factors: tuple) -> None:
    upscale, input_rf, output_rf = factors
    assert format_resolution_projection(1920, 1080, upscale, input_rf, output_rf) == ""


def test_module_has_no_top_level_cv2_or_numpy_import() -> None:
    """media_info must stay importable headlessly: cv2/numpy lazy only."""
    tree = ast.parse(MEDIA_INFO_SOURCE.read_text(encoding="utf-8"))
    for node in tree.body:  # top level only; nested (lazy) imports are fine
        if isinstance(node, ast.Import):
            names = {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            names = {(node.module or "").split(".")[0]}
        else:
            continue
        assert not names & {"cv2", "numpy", "tkinter", "customtkinter"}, (
            f"forbidden top-level import in media_info.py: {names}"
        )
