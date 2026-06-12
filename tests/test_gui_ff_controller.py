from __future__ import annotations

from typing import Optional, cast

from qualityscaler.app.constants import OUTPUT_PATH_CODED
from qualityscaler.app.controllers.framegen import FrameGenController, build_settings, validate
from qualityscaler.app.ff_state import FFUIState


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

    def __init__(
        self, alive_after_join: bool, kill_exception: Optional[BaseException] = None
    ) -> None:
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


def _controller_with(
    process: _FakeProcess,
) -> tuple[FrameGenController, _FakeStopEvent]:
    controller = FrameGenController.__new__(FrameGenController)
    stop_event = _FakeStopEvent()
    controller.event_stop_process = cast("object", stop_event)  # type: ignore[assignment]
    controller.process_orchestrator = cast("object", process)  # type: ignore[assignment]
    return controller, stop_event


def test_stop_process_skips_kill_when_orchestrator_already_exited() -> None:
    # Regression test for issue #57: after a successful run the orchestrator
    # has already exited; kill() must not be called at all.
    process = _FakeProcess(
        alive_after_join=False,
        kill_exception=PermissionError("[WinError 5] Access is denied"),
    )
    controller, stop_event = _controller_with(process)

    controller.stop_process()

    assert process.kill_calls == 0
    assert len(process.join_timeouts) == 1
    assert process.join_timeouts[0] is not None  # bounded join, not unbounded
    assert stop_event.set_called is True
    assert stop_event.clear_called is True


def test_stop_process_absorbs_permission_error_from_kill_race() -> None:
    # The orchestrator exits between is_alive() and TerminateProcess; on
    # Windows kill() raises PermissionError, which must be swallowed.
    process = _FakeProcess(
        alive_after_join=True,
        kill_exception=PermissionError("[WinError 5] Access is denied"),
    )
    controller, stop_event = _controller_with(process)

    controller.stop_process()

    assert process.kill_calls == 1
    assert len(process.join_timeouts) == 2  # graceful join, then reaping join
    assert stop_event.clear_called is True


def test_stop_process_kills_live_orchestrator() -> None:
    process = _FakeProcess(alive_after_join=True)
    controller, _ = _controller_with(process)

    controller.stop_process()

    assert process.kill_calls == 1


def test_stop_process_handles_missing_orchestrator() -> None:
    controller = FrameGenController.__new__(FrameGenController)
    stop_event = _FakeStopEvent()
    controller.event_stop_process = cast("object", stop_event)  # type: ignore[assignment]
    controller.process_orchestrator = None

    controller.stop_process()

    assert stop_event.set_called is True
    assert stop_event.clear_called is True
