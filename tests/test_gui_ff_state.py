from __future__ import annotations

import pytest

from qualityscaler.app.constants import OUTPUT_PATH_CODED
from qualityscaler.app.ff_state import (
    FFUIState,
    generation_factor_from_label,
    video_output_from_label,
)


@pytest.mark.parametrize(
    ("label", "expected_factor", "expected_slowmotion"),
    [
        ("x2", 2, False),
        ("x4", 4, False),
        ("x8", 8, False),
        ("Slowmotion x2", 2, True),
        ("Slowmotion x4", 4, True),
        ("Slowmotion x8", 8, True),
    ],
)
def test_generation_factor_from_label(label: str, expected_factor: int, expected_slowmotion: bool) -> None:
    assert generation_factor_from_label(label) == (expected_factor, expected_slowmotion)


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        (".mp4 (x264)", (".mp4", "x264")),
        (".mp4 (x265)", (".mp4", "x265")),
        (".avi", (".avi", "x264")),
    ],
)
def test_video_output_from_label(label: str, expected: tuple) -> None:
    assert video_output_from_label(label) == expected


def test_ffui_state_defaults() -> None:
    state = FFUIState()
    assert state.ai_model == "RIFE"
    assert state.generation_option == "x2"
    assert state.keep_frames == "ON"
    assert state.image_extension == ".jpg"
    assert state.video_output == ".mp4 (x264)"
    assert state.output_path == OUTPUT_PATH_CODED
    assert state.input_resize_factor == "50"
    assert state.cpu_number == "4"
    assert state.file_list == []


def test_ffui_state_file_list_not_shared() -> None:
    first = FFUIState()
    second = FFUIState()
    first.file_list.append("video.mp4")
    assert second.file_list == []
