from __future__ import annotations

import pytest

from qualityscaler.fluidframes import FF_AI_MODELS, FrameGenSettings
from qualityscaler.fluidframes.settings import FF_FRAME_GEN_FACTORS, FF_VIDEO_QUALITIES


def test_ff_ai_models_list() -> None:
    assert FF_AI_MODELS == ["RIFE", "RIFE_Lite"]


def test_ff_frame_gen_factors() -> None:
    assert FF_FRAME_GEN_FACTORS == (2, 4, 8)


def test_ff_video_qualities_list() -> None:
    assert FF_VIDEO_QUALITIES == ["LOW", "MEDIUM", "HIGH"]


def test_settings_defaults() -> None:
    settings = FrameGenSettings(input_paths=["a.mp4"])
    assert settings.output_path is None
    assert settings.ai_model == "RIFE"
    assert settings.gpu == "Auto"
    assert settings.frame_gen_factor == 2
    assert settings.slowmotion is False
    assert settings.keep_frames is False
    assert settings.image_extension == ".jpg"
    assert settings.video_extension == ".mp4"
    assert settings.video_codec == "x264"
    assert settings.video_quality == "HIGH"
    assert settings.input_resize_factor == 0.5
    assert settings.cpu_number == 4


def test_validate_accepts_good_settings() -> None:
    FrameGenSettings(input_paths=["a.mp4"]).validate()


@pytest.mark.parametrize("frame_gen_factor", [2, 4, 8])
def test_validate_accepts_all_factors(frame_gen_factor: int) -> None:
    FrameGenSettings(input_paths=["a.mp4"], frame_gen_factor=frame_gen_factor).validate()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ai_model": "NotAModel"},
        {"ai_model": "rife"},
        {"frame_gen_factor": 1},
        {"frame_gen_factor": 3},
        {"frame_gen_factor": 16},
        {"video_quality": "ULTRA"},
        {"video_quality": "high"},
        {"input_resize_factor": 0},
        {"input_resize_factor": -0.5},
        {"cpu_number": 0},
        {"cpu_number": -1},
    ],
)
def test_validate_rejects_bad_settings(kwargs: dict) -> None:
    settings = FrameGenSettings(input_paths=["a.mp4"], **kwargs)
    with pytest.raises(ValueError):
        settings.validate()


@pytest.mark.parametrize(
    ("kwargs", "expected_fragment"),
    [
        ({"ai_model": "NotAModel"}, "Unknown AI model"),
        ({"frame_gen_factor": 3}, "frame_gen_factor"),
        ({"video_quality": "ULTRA"}, "Unknown video quality"),
        ({"input_resize_factor": 0}, "input_resize_factor"),
        ({"cpu_number": 0}, "cpu_number"),
    ],
)
def test_validate_error_messages(kwargs: dict, expected_fragment: str) -> None:
    settings = FrameGenSettings(input_paths=["a.mp4"], **kwargs)
    with pytest.raises(ValueError, match=expected_fragment):
        settings.validate()
