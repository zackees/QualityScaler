from __future__ import annotations

from qualityscaler.gui.constants import OUTPUT_PATH_CODED
from qualityscaler.gui.ff_controller import build_settings, validate
from qualityscaler.gui.ff_state import FFUIState


def _valid_state() -> FFUIState:
    state = FFUIState()
    state.file_list = ["C:/videos/clip.mp4"]
    return state


def test_validate_requires_files() -> None:
    assert validate(FFUIState()) == "Please select a file"


def test_validate_rejects_non_video_files() -> None:
    state = _valid_state()
    state.file_list.append("C:/images/photo.jpg")
    assert validate(state) == "Fluid Frames supports video files only"


def test_validate_rejects_non_numeric_resize_factor() -> None:
    state = _valid_state()
    state.input_resize_factor = "abc"
    assert validate(state) == "Input resolution % must be a number"


def test_validate_rejects_zero_resize_factor() -> None:
    state = _valid_state()
    state.input_resize_factor = "0"
    assert validate(state) == "Input resolution % must be a value > 0"


def test_validate_rejects_non_numeric_cpu_number() -> None:
    state = _valid_state()
    state.cpu_number = "many"
    assert validate(state) == "CPU number must be a number"


def test_validate_rejects_zero_cpu_number() -> None:
    state = _valid_state()
    state.cpu_number = "0"
    assert validate(state) == "CPU number must be a value >= 1"


def test_validate_accepts_valid_state() -> None:
    assert validate(_valid_state()) is None


def test_build_settings_maps_labels() -> None:
    state = _valid_state()
    state.generation_option = "Slowmotion x4"
    state.video_output = ".mp4 (x265)"
    state.keep_frames = "OFF"
    state.input_resize_factor = "75"
    state.cpu_number = "6"

    settings = build_settings(state)

    assert settings.input_paths == ["C:/videos/clip.mp4"]
    assert settings.output_path is None  # OUTPUT_PATH_CODED maps to None
    assert settings.ai_model == "RIFE"
    assert settings.frame_gen_factor == 4
    assert settings.slowmotion is True
    assert settings.keep_frames is False
    assert settings.video_extension == ".mp4"
    assert settings.video_codec == "x265"
    assert settings.input_resize_factor == 0.75
    assert settings.cpu_number == 6


def test_build_settings_explicit_output_path() -> None:
    state = _valid_state()
    assert state.output_path == OUTPUT_PATH_CODED
    state.output_path = "C:/output"
    state.generation_option = "x2"

    settings = build_settings(state)

    assert settings.output_path == "C:/output"
    assert settings.frame_gen_factor == 2
    assert settings.slowmotion is False
    assert settings.keep_frames is True
    settings.validate()
