from __future__ import annotations

import pytest

from qualityscaler.core import (
    AI_MODELS,
    BLENDING_FACTORS,
    VIDEO_QUALITIES,
    VRAM_MODEL_USAGE,
    UpscaleSettings,
    tiles_resolution_for,
)


def test_ai_models_list() -> None:
    assert AI_MODELS == [
        "LVAx2",
        "RealESR_Gx4",
        "RealESR_Ax4",
        "BSRGANx2",
        "BSRGANx4",
        "RealESRGANx4",
        "MSharpx4",
        "IRCNN_Mx1",
        "IRCNN_Lx1",
    ]
    assert "----" not in AI_MODELS


def test_vram_model_usage_covers_all_models() -> None:
    assert set(VRAM_MODEL_USAGE) == set(AI_MODELS)


def test_blending_factors() -> None:
    assert BLENDING_FACTORS == {"OFF": 0, "Low": 0.3, "Medium": 0.5, "High": 0.7}


@pytest.mark.parametrize(
    ("model", "vram_gb", "expected"),
    [
        ("RealESR_Gx4", 4.0, 1000),
        ("BSRGANx2", 4.0, 320),
        ("IRCNN_Mx1", 2.0, 800),
        ("LVAx2", 4.0, 800),
        ("BSRGANx4", 8.0, 600),
    ],
)
def test_tiles_resolution_for(model: str, vram_gb: float, expected: int) -> None:
    assert tiles_resolution_for(model, vram_gb) == expected


def test_settings_defaults() -> None:
    settings = UpscaleSettings(input_paths=["a.png"])
    assert settings.output_path is None
    assert settings.ai_model == "RealESR_Gx4"
    assert settings.gpu == "Auto"
    assert settings.vram_gb == 4.0
    assert settings.multithreading == 1
    assert settings.input_resize_factor == 1.0
    assert settings.output_resize_factor == 1.0
    assert settings.blending == "OFF"
    assert settings.keep_frames is False
    assert settings.image_extension == ".png"
    assert settings.video_extension == ".mp4"
    assert settings.video_codec == "x264"
    assert settings.video_quality == "HIGH"


def test_video_qualities_list() -> None:
    assert VIDEO_QUALITIES == ["LOW", "MEDIUM", "HIGH"]


def test_settings_tiles_resolution_property() -> None:
    settings = UpscaleSettings(input_paths=["a.png"], ai_model="BSRGANx2", vram_gb=6.0)
    assert settings.tiles_resolution == tiles_resolution_for("BSRGANx2", 6.0)


def test_settings_blending_factor_property() -> None:
    assert UpscaleSettings(input_paths=["a.png"], blending="Medium").blending_factor == 0.5
    assert UpscaleSettings(input_paths=["a.png"]).blending_factor == 0


def test_validate_accepts_good_settings() -> None:
    UpscaleSettings(input_paths=["a.png"]).validate()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ai_model": "NotAModel"},
        {"ai_model": "----"},
        {"blending": "Maximum"},
        {"video_quality": "ULTRA"},
        {"video_quality": "high"},
        {"input_resize_factor": 0},
        {"input_resize_factor": -0.5},
        {"output_resize_factor": 0},
        {"vram_gb": 0},
        {"multithreading": 0},
    ],
)
def test_validate_rejects_bad_settings(kwargs: dict) -> None:
    settings = UpscaleSettings(input_paths=["a.png"], **kwargs)
    with pytest.raises(ValueError):
        settings.validate()
