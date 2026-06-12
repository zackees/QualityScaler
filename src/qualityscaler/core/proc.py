"""Subprocess execution with live stdout/stderr line streaming.

Uses the ``running-process`` package (threaded readers feeding atomic
queues, proper Windows process-group kill) when available, otherwise a
plain ``subprocess.Popen`` with two daemon reader threads.
"""

from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import time
from typing import Callable, Sequence

LineCallback = Callable[[str, str], None]

_POLL_INTERVAL_SECONDS = 0.1


def _default_on_line(line: str, stream: str) -> None:
    target = sys.stderr if stream == "stderr" else sys.stdout
    try:
        target.write(line + "\n")
        target.flush()
    except Exception:
        pass


def _startupinfo():
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return startupinfo
    return None


def _use_running_process() -> bool:
    try:
        from running_process import RunningProcess  # noqa: F401
    except Exception:
        return False
    return True


def _stream_with_running_process(
    command: Sequence[str],
    on_line: LineCallback,
    cancel: threading.Event | None,
    tick: Callable[[], None] | None,
) -> int:
    from running_process import RunningProcess

    extra_kwargs = {}
    if os.name == "nt":
        extra_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW

    # stderr must be requested explicitly, otherwise it is merged into stdout
    process = RunningProcess(list(command), check=False, stderr=subprocess.PIPE, **extra_kwargs)

    def drain_output() -> bool:
        drained = False
        for line in process.drain_stdout():
            drained = True
            on_line(str(line), "stdout")
        for line in process.drain_stderr():
            drained = True
            on_line(str(line), "stderr")
        return drained

    cancelled = False
    last_tick = time.monotonic()
    try:
        while True:
            drain_output()

            if cancel is not None and cancel.is_set() and not cancelled:
                cancelled = True
                process.terminate()

            if process.poll() is not None:
                break

            now = time.monotonic()
            if tick is not None and now - last_tick >= 1.0:
                last_tick = now
                tick()
            time.sleep(_POLL_INTERVAL_SECONDS)

        # Reader threads may still be flushing the tail of the output
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if not drain_output():
                break
            time.sleep(_POLL_INTERVAL_SECONDS)
    except Exception:
        process.kill()
        raise

    returncode = process.poll()
    return returncode if returncode is not None else -1


def _stream_with_popen(
    command: Sequence[str],
    on_line: LineCallback,
    cancel: threading.Event | None,
    tick: Callable[[], None] | None,
) -> int:
    process = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        startupinfo=_startupinfo(),
    )

    line_q: queue.Queue[tuple[str, str] | None] = queue.Queue()

    def read_stream(pipe, stream_name: str) -> None:
        try:
            for raw_line in iter(pipe.readline, ""):
                line_q.put((raw_line.rstrip("\r\n"), stream_name))
        finally:
            line_q.put(None)

    readers = [
        threading.Thread(target=read_stream, args=(process.stdout, "stdout"), daemon=True),
        threading.Thread(target=read_stream, args=(process.stderr, "stderr"), daemon=True),
    ]
    for reader in readers:
        reader.start()

    open_streams = len(readers)
    cancelled = False
    last_tick = time.monotonic()
    try:
        while open_streams > 0:
            if cancel is not None and cancel.is_set() and not cancelled:
                cancelled = True
                process.terminate()

            now = time.monotonic()
            if tick is not None and now - last_tick >= 1.0:
                last_tick = now
                tick()

            try:
                item = line_q.get(timeout=_POLL_INTERVAL_SECONDS)
            except queue.Empty:
                continue
            if item is None:
                open_streams -= 1
                continue
            on_line(item[0], item[1])
    except Exception:
        process.kill()
        raise
    finally:
        for reader in readers:
            reader.join(timeout=5)

    return process.wait()


def stream_subprocess(
    command: Sequence[str],
    on_line: LineCallback | None = None,
    cancel: threading.Event | None = None,
    tick: Callable[[], None] | None = None,
) -> int:
    """Run *command*, streaming each output line to *on_line(line, stream)*.

    *tick* is invoked roughly once per second while the process runs.
    Setting *cancel* terminates the process; the (nonzero) exit code is
    returned rather than raised.
    """
    if on_line is None:
        on_line = _default_on_line

    if _use_running_process():
        return _stream_with_running_process(command, on_line, cancel, tick)
    return _stream_with_popen(command, on_line, cancel, tick)
