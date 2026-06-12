from __future__ import annotations

import pytest

from qualityscaler.app.constants import (
    AI_models_list,
    AI_multithreading_list,
    blending_list,
    keep_frames_list,
)
from qualityscaler.app.state import (
    UIState,
    blending_from_label,
    blending_to_label,
    keep_frames_from_label,
    keep_frames_to_label,
    multithreading_from_label,
    multithreading_to_label,
    upscale_factor_for_model,
)


def test_default_state_matches_historical_defaults() -> None:
    state = UIState()
    assert state.app_zoom == "100%"
    assert state.ai_model == AI_models_list[0]
    assert state.ai_multithreading == AI_multithreading_list[0]
    assert state.keep_frames == keep_frames_list[1]
    assert state.video_quality == "HIGH"
    assert state.blending == blending_list[1]
    assert state.output_path == "Same path as input files"
    assert state.input_resize_factor == "50"
    assert state.output_resize_factor == "100"
    assert state.vram_limiter == "4"


@pytest.mark.parametrize("label, threads", [("OFF", 1), ("2 threads", 2), ("4 threads", 4), ("6 threads", 6), ("8 threads", 8)])
def test_multithreading_label_round_trip(label: str, threads: int) -> None:
    assert multithreading_from_label(label) == threads
    assert multithreading_to_label(threads) == label


@pytest.mark.parametrize("label, keep", [("OFF", False), ("ON", True)])
def test_keep_frames_label_round_trip(label: str, keep: bool) -> None:
    assert keep_frames_from_label(label) is keep
    assert keep_frames_to_label(keep) == label


@pytest.mark.parametrize("label, factor", [("OFF", 0), ("Low", 0.3), ("Medium", 0.5), ("High", 0.7)])
def test_blending_label_round_trip(label: str, factor: float) -> None:
    assert blending_from_label(label) == factor
    assert blending_to_label(factor) == label


@pytest.mark.parametrize(
    "model, factor",
    [
        ("----", 0),
        ("IRCNN_Mx1", 1),
        ("LVAx2", 2),
        ("BSRGANx2", 2),
        ("RealESR_Gx4", 4),
        ("RealESRGANx4", 4),
    ],
)
def test_upscale_factor_for_model(model: str, factor: int) -> None:
    assert upscale_factor_for_model(model) == factor


def test_every_menu_model_has_an_upscale_factor() -> None:
    for model in AI_models_list:
        if model == "----":
            continue
        assert upscale_factor_for_model(model) in (1, 2, 3, 4)
