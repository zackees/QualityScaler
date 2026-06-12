from __future__ import annotations

from typing import Optional, cast

import pytest

from qualityscaler.core import UpscaleProgress
from qualityscaler.gui.constants import MENU_LIST_SEPARATOR, OUTPUT_PATH_CODED
from qualityscaler.gui.controller import UpscaleController, build_settings, format_progress_event, validate
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


class _FakeStopEvent:
    def __init__(self) -> None:
        self.set_called = False
        self.clear_called = False

    def set(self) -> None:
        self.set_called = True

    def clear(self) -> None:
        self.clear_called = True


class _FakeProcess:
    """Stand-in for a multiprocessing.Process orchestrator."""

    def __init__(self, alive_after_join: bool, kill_exception: Optional[BaseException] = None) -> None:
        self._alive_after_join = alive_after_join
        self._kill_exception = kill_exception
        self.join_timeouts: list[Optional[float]] = []
        self.kill_calls = 0

    def join(self, timeout: Optional[float] = None) -> None:
        self.join_timeouts.append(timeout)

    def is_alive(self) -> bool:
        return self._alive_after_join

    def kill(self) -> None:
        self.kill_calls += 1
        if self._kill_exception is not None:
            raise self._kill_exception


def _controller_with(process: Optional[_FakeProcess]) -> tuple[UpscaleController, _FakeStopEvent]:
    controller = UpscaleController.__new__(UpscaleController)
    stop_event = _FakeStopEvent()
    controller.event_stop_upscale_process = cast("object", stop_event)  # type: ignore[assignment]
    controller.process_upscale_orchestrator = cast("object", process)  # type: ignore[assignment]
    return controller, stop_event


class TestStopProcess:
    def test_skips_kill_when_orchestrator_already_exited(self) -> None:
        # Regression test for issue #57: after a successful run the
        # orchestrator has already exited; kill() must not be called.
        process = _FakeProcess(alive_after_join=False, kill_exception=PermissionError("[WinError 5] Access is denied"))
        controller, stop_event = _controller_with(process)

        controller.stop_process()

        assert process.kill_calls == 0
        assert len(process.join_timeouts) == 1
        assert process.join_timeouts[0] is not None  # bounded join, not unbounded
        assert stop_event.set_called is True
        assert stop_event.clear_called is True

    def test_absorbs_permission_error_from_kill_race(self) -> None:
        # The orchestrator exits between is_alive() and TerminateProcess; on
        # Windows kill() raises PermissionError, which must be swallowed.
        process = _FakeProcess(alive_after_join=True, kill_exception=PermissionError("[WinError 5] Access is denied"))
        controller, stop_event = _controller_with(process)

        controller.stop_process()

        assert process.kill_calls == 1
        assert len(process.join_timeouts) == 2  # graceful join, then reaping join
        assert stop_event.clear_called is True

    def test_kills_live_orchestrator(self) -> None:
        process = _FakeProcess(alive_after_join=True)
        controller, _ = _controller_with(process)

        controller.stop_process()

        assert process.kill_calls == 1

    def test_handles_missing_orchestrator(self) -> None:
        controller, stop_event = _controller_with(None)

        controller.stop_process()

        assert stop_event.set_called is True
        assert stop_event.clear_called is True
