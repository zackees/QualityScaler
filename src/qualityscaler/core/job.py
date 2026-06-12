from __future__ import annotations

import queue
import threading
from typing import Iterator

from .events import UpscaleCompleted, UpscaleError, UpscaleEvent, UpscaleStopped
from .settings import UpscaleSettings

_TERMINAL_EVENTS = (UpscaleCompleted, UpscaleError, UpscaleStopped)


class UpscaleJob:
    def __init__(self, settings: UpscaleSettings) -> None:
        self._settings = settings
        self._events: queue.Queue[UpscaleEvent] = queue.Queue()
        self._cancel = threading.Event()
        self._thread: threading.Thread | None = None
        self._terminal_event: UpscaleEvent | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("UpscaleJob can only be started once")
        self._thread = threading.Thread(target=self._run, name="UpscaleJob", daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        self._cancel.set()

    def events(self) -> Iterator[UpscaleEvent]:
        while True:
            event = self._events.get()
            yield event
            if isinstance(event, _TERMINAL_EVENTS):
                return

    def wait(self, timeout: float | None = None) -> UpscaleEvent | None:
        if self._thread is None:
            return None
        self._thread.join(timeout)
        if self._thread.is_alive():
            return None
        return self._terminal_event

    @property
    def done(self) -> bool:
        return self._thread is not None and not self._thread.is_alive()

    def _run(self) -> None:
        from . import pipeline

        try:
            output_paths = pipeline.run_pipeline(self._settings, self._events.put, self._cancel)
        except Exception as exc:
            terminal: UpscaleEvent = UpscaleError(str(exc))
        else:
            if self._cancel.is_set():
                terminal = UpscaleStopped()
            else:
                terminal = UpscaleCompleted(tuple(output_paths))
        self._terminal_event = terminal
        self._events.put(terminal)
