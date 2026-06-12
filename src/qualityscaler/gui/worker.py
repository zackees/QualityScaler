"""Pipeline subprocess entry point, kept free of any GUI toolkit imports.

This module is the target of the upscale ``multiprocessing.Process`` so the
spawned child only imports this small module (plus ``qualityscaler.core``)
instead of the whole GUI.
"""

from threading import Thread, Event as threading_Event
from time import sleep
from queue import Empty, Full

from qualityscaler.core import (
    UpscaleSettings,
    UpscaleEvent,
    UpscaleCompleted,
    UpscaleError,
    UpscaleStopped,
    run_pipeline,
)

CLOSE_APP_STATUS = "CloseApp"


def _pipeline_process_main(
        event_q,
        stop_mp_event,
        settings: UpscaleSettings
        ) -> None:

    cancel_threading_event = threading_Event()

    def watch_stop_event() -> None:
        while not cancel_threading_event.is_set():
            if stop_mp_event.is_set():
                cancel_threading_event.set()
                break
            sleep(0.25)

    Thread(target=watch_stop_event, daemon=True).start()

    def emit_event(event: UpscaleEvent) -> None:
        # Keep only the freshest event so the pipeline never blocks on the GUI
        while not event_q.empty():
            try:
                event_q.get_nowait()
            except Empty:
                break
        try:
            event_q.put_nowait(event)
        except Full:
            pass

    def emit_terminal_event(event: UpscaleEvent) -> None:
        while not event_q.empty():
            try:
                event_q.get_nowait()
            except Empty:
                break
        event_q.put(event)

    try:
        output_paths = run_pipeline(settings, emit=emit_event, cancel=cancel_threading_event)
    except Exception as exception:
        if cancel_threading_event.is_set() or stop_mp_event.is_set():
            emit_terminal_event(UpscaleStopped())
        else:
            emit_terminal_event(UpscaleError(str(exception)))
    else:
        if cancel_threading_event.is_set() or stop_mp_event.is_set():
            emit_terminal_event(UpscaleStopped())
        else:
            emit_terminal_event(UpscaleCompleted(tuple(output_paths)))
