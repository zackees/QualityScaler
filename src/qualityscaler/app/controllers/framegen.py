"""Fluid Frames orchestration: validation, settings building and process control.

Toolkit-free so it can be unit tested headlessly; the GUI layer provides an
``on_event`` callback to receive pipeline events.
"""

from __future__ import annotations

from multiprocessing import Process as multiprocessing_Process, Manager as multiprocessing_Manager
from os.path import splitext as os_path_splitext
from threading import Thread
from time import sleep
from typing import Callable, Optional

from qualityscaler.core import (
    UpscaleCompleted,
    UpscaleError,
    UpscaleStopped,
)
from qualityscaler.fluidframes.settings import FrameGenSettings
from qualityscaler.app.constants import OUTPUT_PATH_CODED, app_name, supported_video_extensions
from qualityscaler.app.ff_state import (
    FFUIState,
    generation_factor_from_label,
    video_output_from_label,
)
from qualityscaler.app.workers.framegen import CLOSE_APP_STATUS, _frame_generation_process_main
from qualityscaler.app.state import keep_frames_from_label

_SUPPORTED_VIDEO_EXTENSIONS_LOWER = {extension.lower() for extension in supported_video_extensions}

# How long to wait for the orchestrator to exit gracefully after the stop
# event is set, before falling back to kill().
_STOP_JOIN_TIMEOUT_SECONDS = 5.0


def validate(state: FFUIState) -> Optional[str]:
    """Return an error message for the info bar, or None if input is valid."""
    if len(state.file_list) <= 0:
        return "Please select a file"

    for file_path in state.file_list:
        extension = os_path_splitext(file_path)[1].lower()
        if extension not in _SUPPORTED_VIDEO_EXTENSIONS_LOWER:
            return "Fluid Frames supports video files only"

    try:
        input_resize_factor = int(float(str(state.input_resize_factor)))
    except Exception:
        return "Input resolution % must be a number"
    if input_resize_factor <= 0:
        return "Input resolution % must be a value > 0"

    try:
        cpu_number = int(float(str(state.cpu_number)))
    except Exception:
        return "CPU number must be a number"
    if cpu_number < 1:
        return "CPU number must be a value >= 1"

    return None


def build_settings(state: FFUIState) -> FrameGenSettings:
    frame_gen_factor, slowmotion = generation_factor_from_label(state.generation_option)
    video_extension, video_codec = video_output_from_label(state.video_output)
    output_path = state.output_path
    return FrameGenSettings(
        input_paths=list(state.file_list),
        output_path=None if output_path == OUTPUT_PATH_CODED else output_path,
        ai_model=state.ai_model,
        gpu=state.gpu,
        frame_gen_factor=frame_gen_factor,
        slowmotion=slowmotion,
        keep_frames=keep_frames_from_label(state.keep_frames),
        image_extension=state.image_extension,
        video_extension=video_extension,
        video_codec=video_codec,
        input_resize_factor=int(float(str(state.input_resize_factor))) / 100,
        cpu_number=int(float(str(state.cpu_number))),
    )


def _print_start_banner(settings: FrameGenSettings) -> None:
    print("=" * 50)
    print("> Starting frame generation:")
    print(f"    Files to process: {len(settings.input_paths)}")
    print(f"    Output path: {settings.output_path or OUTPUT_PATH_CODED}")
    print(f"    Selected AI model: {settings.ai_model}")
    print(f"    Frame generation factor: x{settings.frame_gen_factor}")
    print(f"    Slowmotion: {settings.slowmotion}")
    print(f"    Selected GPU: {settings.gpu}")
    print(f"    Selected image output extension: {settings.image_extension}")
    print(f"    Selected video output extension: {settings.video_extension}")
    print(f"    Selected video output codec: {settings.video_codec}")
    print(f"    Input resize factor: {int(settings.input_resize_factor * 100)}%")
    print(f"    CPU number: {settings.cpu_number}")
    print(f"    Save frames: {settings.keep_frames}")
    print("=" * 50)


class FrameGenController:
    """Owns the worker process, its stop event and the single-slot event queue."""

    def __init__(self, log_sink=None) -> None:
        self._manager = multiprocessing_Manager()
        self.process_status_q = self._manager.Queue(maxsize=1)
        self.event_stop_process = self._manager.Event()
        self.process_orchestrator: Optional[multiprocessing_Process] = None

        self.log_q = None
        self._log_bridge = None
        if log_sink is not None:
            from qualityscaler.app.console_log import MpLogBridge

            self.log_q = self._manager.Queue()
            self._log_bridge = MpLogBridge(self.log_q, log_sink)
            self._log_bridge.start()

    def write_process_status(self, status: object) -> None:
        while not self.process_status_q.empty():
            self.process_status_q.get()
        self.process_status_q.put(status)

    def start(self, settings: FrameGenSettings, on_event: Callable[[object], None]) -> None:
        _print_start_banner(settings)

        self.event_stop_process.clear()
        while not self.process_status_q.empty():
            self.process_status_q.get_nowait()

        self.process_orchestrator = multiprocessing_Process(
            target=_frame_generation_process_main,
            args=(self.process_status_q, self.event_stop_process, settings, self.log_q),
        )
        self.process_orchestrator.start()

        Thread(target=self._watch_events, args=(on_event,)).start()

    def _watch_events(self, on_event: Callable[[object], None]) -> None:
        sleep(1)

        while True:
            actual_event = self.process_status_q.get()
            print(f"[{app_name}] check_frame_generation_steps - {actual_event}")

            if actual_event == CLOSE_APP_STATUS:
                break

            on_event(actual_event)

            if isinstance(actual_event, (UpscaleStopped, UpscaleCompleted, UpscaleError)):
                break

            sleep(1)

    def stop_process(self) -> None:
        print(f"[{app_name}] stop_frame_generation_process - setting stop event")
        self.event_stop_process.set()

        process = self.process_orchestrator
        if process is not None:
            print(f"[{app_name}] stop_frame_generation_process - waiting for orchestrator to terminate")
            process.join(timeout=_STOP_JOIN_TIMEOUT_SECONDS)
            if process.is_alive():
                try:
                    process.kill()
                except (PermissionError, OSError):
                    # The orchestrator exited between is_alive() and
                    # TerminateProcess; on Windows this raises
                    # PermissionError (WinError 5). Nothing to do.
                    pass
                process.join()
            print(f"[{app_name}] stop_frame_generation_process - orchestrator terminated")

        self.event_stop_process.clear()

    def request_stop(self) -> None:
        self.write_process_status(UpscaleStopped())
        self.stop_process()

    def notify_close(self) -> None:
        self.write_process_status(f"{CLOSE_APP_STATUS}")
        self.stop_process()
        if self._log_bridge is not None:
            self._log_bridge.stop()
