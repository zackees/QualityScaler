from __future__ import annotations

import pytest

from qualityscaler.core import UpscaleProgress
from qualityscaler.gui.constants import MENU_LIST_SEPARATOR, OUTPUT_PATH_CODED
from qualityscaler.gui.controller import build_settings, format_progress_event, validate
from qualityscaler.gui.state import UIState


def _valid_state(**overrides) -> UIState:
    state = UIState(file_list=["photo.png"])
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


class TestValidate:
    def test_valid_state_returns_none(self) -> None:
        assert validate(_valid_state()) is None

    def test_empty_file_list(self) -> None:
        assert validate(_valid_state(file_list=[])) == "Please select a file"

    def test_separator_ai_model(self) -> None:
        state = _valid_state(ai_model=MENU_LIST_SEPARATOR[0])
        assert validate(state) == "Please select the AI model"

    def test_input_resize_not_a_number(self) -> None:
        state = _valid_state(input_resize_factor="abc")
        assert validate(state) == "Input resolution % must be a number"

    def test_input_resize_not_positive(self) -> None:
        state = _valid_state(input_resize_factor="0")
        assert validate(state) == "Input resolution % must be a value > 0"

    def test_output_resize_not_a_number(self) -> None:
        state = _valid_state(output_resize_factor="abc")
        assert validate(state) == "Output resolution % must be a number"

    def test_output_resize_not_positive(self) -> None:
        state = _valid_state(output_resize_factor="-5")
        assert validate(state) == "Output resolution % must be a value > 0"

    def test_vram_not_a_number(self) -> None:
        state = _valid_state(vram_limiter="abc")
        assert validate(state) == "GPU VRAM value must be a number"

    def test_vram_not_positive(self) -> None:
        state = _valid_state(vram_limiter="0")
        assert validate(state) == "GPU VRAM value must be a value > 0"

    def test_vram_below_one_truncates_to_zero(self) -> None:
        # Historical behavior: int(float("0.5")) == 0, which fails positivity
        state = _valid_state(vram_limiter="0.5")
        assert validate(state) == "GPU VRAM value must be a value > 0"

    def test_float_strings_are_accepted(self) -> None:
        state = _valid_state(input_resize_factor="50.5", output_resize_factor="100.0")
        assert validate(state) is None


class TestBuildSettings:
    def test_defaults(self) -> None:
        settings = build_settings(_valid_state())

        assert settings.input_paths == ["photo.png"]
        assert settings.output_path is None  # OUTPUT_PATH_CODED maps to None
        assert settings.ai_model == UIState().ai_model
        assert settings.vram_gb == 4.0
        assert settings.multithreading == 1  # "OFF"
        assert settings.input_resize_factor == 0.5
        assert settings.output_resize_factor == 1.0
        assert settings.blending == "Low"
        assert settings.keep_frames is True  # default label "ON"
        settings.validate()

    def test_explicit_output_path_is_kept(self) -> None:
        settings = build_settings(_valid_state(output_path="C:/out"))
        assert settings.output_path == "C:/out"

    def test_coded_output_path_maps_to_none(self) -> None:
        settings = build_settings(_valid_state(output_path=OUTPUT_PATH_CODED))
        assert settings.output_path is None

    def test_label_conversions(self) -> None:
        state = _valid_state(
            ai_multithreading="4 threads",
            keep_frames="OFF",
            blending="High",
            vram_limiter="2.5",
        )
        settings = build_settings(state)

        assert settings.multithreading == 4
        assert settings.keep_frames is False
        assert settings.blending == "High"
        assert settings.vram_gb == 2.5

    def test_resize_factors_are_fractions(self) -> None:
        state = _valid_state(input_resize_factor="75", output_resize_factor="120")
        settings = build_settings(state)

        assert settings.input_resize_factor == pytest.approx(0.75)
        assert settings.output_resize_factor == pytest.approx(1.2)


class TestFormatProgressEvent:
    def test_plain_message(self) -> None:
        assert format_progress_event(UpscaleProgress(message="Upscaling")) == "Upscaling"

    def test_file_index_prefix(self) -> None:
        event = UpscaleProgress(message="Upscaling", file_index=2)
        assert format_progress_event(event) == "2. Upscaling"

    def test_fraction_suffix(self) -> None:
        event = UpscaleProgress(message="Upscaling", file_index=1, fraction=0.42)
        assert format_progress_event(event) == "1. Upscaling 42%"
