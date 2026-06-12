"""Upscale orchestration: validation, settings building and process control.

Toolkit-free so it can be unit tested headlessly; the GUI layer provides an
``on_event`` callback to receive pipeline events.
"""

from __future__ import annotations

from multiprocessing import Process as multiprocessing_Process, Manager as multiprocessing_Manager
from threading import Thread
from time import sleep
from typing import Callable, Optional

from qualityscaler.core import (
    UpscaleSettings,
    UpscaleProgress,
    UpscaleCompleted,
    UpscaleError,
    UpscaleStopped,
)

from qualityscaler.gui.constants import MENU_LIST_SEPARATOR, OUTPUT_PATH_CODED, app_name
from qualityscaler.gui.state import (
    UIState,
    keep_frames_from_label,
    multithreading_from_label,
)
from qualityscaler.gui.worker import CLOSE_APP_STATUS, _pipeline_process_main

# How long to wait for the orchestrator to exit gracefully after the stop
# event is set, before falling back to kill().
_STOP_JOIN_TIMEOUT_SECONDS = 5.0


def format_progress_event(event: UpscaleProgress) -> str:
    message = event.message
    if event.file_index > 0:
        message = f"{event.file_index}. {message}"
    if event.fraction is not None:
        message = f"{message} {int(event.fraction * 100)}%"
    return message


def validate(state: UIState) -> Optional[str]:
    """Return an error message for the info bar, or None if input is valid."""
    if len(state.file_list) <= 0:
        return "Please select a file"

    if state.ai_model == MENU_LIST_SEPARATOR[0]:
        return "Please select the AI model"

    try:
        input_resize_factor = int(float(str(state.input_resize_factor)))
    except Exception:
        return "Input resolution % must be a number"
    if input_resize_factor <= 0:
        return "Input resolution % must be a value > 0"

    try:
        output_resize_factor = int(float(str(state.output_resize_factor)))
    except Exception:
        return "Output resolution % must be a number"
    if output_resize_factor <= 0:
        return "Output resolution % must be a value > 0"

    try:
        vram = int(float(str(state.vram_limiter)))
    except Exception:
        return "GPU VRAM value must be a number"
    if vram <= 0:
        return "GPU VRAM value must be a value > 0"

    return None


def build_settings(state: UIState) -> UpscaleSettings:
    output_path = state.output_path
    return UpscaleSettings(
        input_paths=list(state.file_list),
        output_path=None if output_path == OUTPUT_PATH_CODED else output_path,
        ai_model=state.ai_model,
        gpu=state.gpu,
        vram_gb=float(str(state.vram_limiter)),
        multithreading=multithreading_from_label(state.ai_multithreading),
        input_resize_factor=int(float(str(state.input_resize_factor))) / 100,
        output_resize_factor=int(float(str(state.output_resize_factor))) / 100,
        blending=state.blending,
        keep_frames=keep_frames_from_label(state.keep_frames),
        image_extension=state.image_extension,
        video_extension=state.video_extension,
        video_codec=state.video_codec,
        video_quality=state.video_quality,
    )


def _print_start_banner(settings: UpscaleSettings) -> None:
    print("=" * 50)
    print("> Starting upscale:")
    print(f"    Files to upscale: {len(settings.input_paths)}")
    print(f"    Output path: {settings.output_path or OUTPUT_PATH_CODED}")
    print(f"    Selected AI model: {settings.ai_model}")
    print(f"    Blending: {settings.blending}")
    print(f"    AI multithreading: {settings.multithreading}")
    print(f"    Selected GPU: {settings.gpu}")
    print(f"    Tiles resolution for selected GPU VRAM: {settings.tiles_resolution}x{settings.tiles_resolution}px")
    print(f"    Selected image output extension: {settings.image_extension}")
    print(f"    Selected video output extension: {settings.video_extension}")
    print(f"    Selected video output codec: {settings.video_codec}")
    print(f"    Input resize factor: {int(settings.input_resize_factor * 100)}%")
    print(f"    Output resize factor: {int(settings.output_resize_factor * 100)}%")
    print(f"    Save frames: {settings.keep_frames}")
    print("=" * 50)


class UpscaleController:
    """Owns the worker process, its stop event and the single-slot event queue."""

    def __init__(self, log_sink=None) -> None:
        self._manager = multiprocessing_Manager()
        self.process_status_q = self._manager.Queue(maxsize=1)
        self.event_stop_upscale_process = self._manager.Event()
        self.process_upscale_orchestrator: Optional[multiprocessing_Process] = None

        self.log_q = None
        self._log_bridge = None
        if log_sink is not None:
            from qualityscaler.gui.console_log import MpLogBridge

            self.log_q = self._manager.Queue()
            self._log_bridge = MpLogBridge(self.log_q, log_sink)
            self._log_bridge.start()

    def write_process_status(self, status: object) -> None:
        while not self.process_status_q.empty():
            self.process_status_q.get()
        self.process_status_q.put(status)

    def start(self, settings: UpscaleSettings, on_event: Callable[[object], None]) -> None:
        _print_start_banner(settings)

        self.event_stop_upscale_process.clear()
        while not self.process_status_q.empty():
            self.process_status_q.get_nowait()

        self.process_upscale_orchestrator = multiprocessing_Process(
            target=_pipeline_process_main,
            args=(self.process_status_q, self.event_stop_upscale_process, settings, self.log_q),
        )
        self.process_upscale_orchestrator.start()

        Thread(target=self._watch_events, args=(on_event,)).start()

    def _watch_events(self, on_event: Callable[[object], None]) -> None:
        sleep(1)

        while True:
            actual_event = self.process_status_q.get()
            print(f"[{app_name}] check_upscale_steps - {actual_event}")

            if actual_event == CLOSE_APP_STATUS:
                break

            on_event(actual_event)

            if isinstance(actual_event, (UpscaleStopped, UpscaleCompleted, UpscaleError)):
                break

            sleep(1)

    def stop_process(self) -> None:
        print(f"[{app_name}] stop_upscale_process - setting upscale process stop event")
        self.event_stop_upscale_process.set()

        process = self.process_upscale_orchestrator
        if process is not None:
            print(f"[{app_name}] stop_upscale_process - waiting for upscale orchestrator to terminate")
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
            print(f"[{app_name}] stop_upscale_process - upscale orchestrator terminated")

        self.event_stop_upscale_process.clear()

    def request_stop(self) -> None:
        self.write_process_status(UpscaleStopped())
        self.stop_process()

    def notify_close(self) -> None:
        self.write_process_status(f"{CLOSE_APP_STATUS}")
        self.stop_process()
        if self._log_bridge is not None:
            self._log_bridge.stop()
