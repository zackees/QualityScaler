"""Log transport for the in-app console, kept free of any GUI toolkit imports.

Producers (stdout/stderr redirectors, logging handlers, worker-process
bridges) only ever enqueue onto a :class:`ConsoleSink`; the Tk main loop is
the single consumer and drains the sink on a timer.
"""

from __future__ import annotations

import io
import logging
import queue
import re
import sys
import threading
from dataclasses import dataclass

_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")

STREAM_STDOUT = "stdout"
STREAM_STDERR = "stderr"
STREAM_INFO = "info"

MP_LOG_SENTINEL = None


@dataclass(frozen=True)
class ConsoleLine:
    text: str
    stream: str = STREAM_STDOUT
    replace_last: bool = False

    def as_tuple(self) -> tuple[str, str, bool]:
        return (self.text, self.stream, self.replace_last)


def strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


def split_terminal_text(text: str) -> tuple[list[tuple[str, bool]], str]:
    """Split *text* into completed lines plus the unterminated remainder.

    Returns ``([(line, replace_last), ...], remainder)``. A line terminated
    by a lone ``\\r`` (ffmpeg-style progress) is flagged ``replace_last``.
    """
    lines: list[tuple[str, bool]] = []
    start = 0
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char == "\n":
            lines.append((text[start:index], False))
            index += 1
            start = index
        elif char == "\r":
            if index + 1 < length and text[index + 1] == "\n":
                lines.append((text[start:index], False))
                index += 2
            else:
                lines.append((text[start:index], True))
                index += 1
            start = index
        else:
            index += 1
    return lines, text[start:]


class ConsoleSink:
    """Thread-safe, unbounded line queue between producers and the GUI."""

    def __init__(self, strip_ansi: bool = True) -> None:
        self._queue: queue.Queue[ConsoleLine] = queue.Queue()
        self._strip_ansi = strip_ansi

    def put(self, text: str, stream: str = STREAM_STDOUT, replace_last: bool = False) -> None:
        if self._strip_ansi:
            text = strip_ansi(text)
        self._queue.put(ConsoleLine(text, stream, replace_last))

    def drain(self, max_items: int = 200) -> list[ConsoleLine]:
        items: list[ConsoleLine] = []
        for _ in range(max_items):
            try:
                items.append(self._queue.get_nowait())
            except queue.Empty:
                break
        return items

    def drain_blocking(self, timeout: float, max_items: int = 200) -> list[ConsoleLine]:
        """Block up to *timeout* seconds for the first line, then drain the rest.

        Returns at most *max_items* lines; returns ``[]`` if nothing arrives
        before the timeout. Friendly to a polling WebSocket server loop —
        no asyncio involved.
        """
        try:
            first = self._queue.get(timeout=timeout)
        except queue.Empty:
            return []
        items = [first]
        items.extend(self.drain(max_items=max_items - 1))
        return items


class LineBufferingWriter(io.TextIOBase):
    """Buffers writes and emits complete lines via :meth:`_emit_line`."""

    def __init__(self, stream_name: str) -> None:
        self._stream_name = stream_name
        self._buffer = ""
        self._lock = threading.Lock()

    def _emit_line(self, text: str, replace_last: bool) -> None:
        raise NotImplementedError

    def writable(self) -> bool:
        return True

    def write(self, s: str) -> int:
        with self._lock:
            lines, self._buffer = split_terminal_text(self._buffer + str(s))
        for text, replace_last in lines:
            self._emit_line(text, replace_last)
        return len(s)

    def flush(self) -> None:
        with self._lock:
            pending, self._buffer = self._buffer, ""
        if pending:
            self._emit_line(pending, False)


class TkStreamRedirector(LineBufferingWriter):
    """Replaces ``sys.stdout``/``sys.stderr``; forwards lines to a sink.

    Also forwards raw writes to *passthrough* (the original stream) so
    crash output still reaches the real stderr when one exists.
    """

    def __init__(self, sink: ConsoleSink, stream_name: str, passthrough=None) -> None:
        super().__init__(stream_name)
        self._sink = sink
        self._passthrough = passthrough

    def _emit_line(self, text: str, replace_last: bool) -> None:
        self._sink.put(text, self._stream_name, replace_last)

    def write(self, s: str) -> int:
        if self._passthrough is not None:
            try:
                self._passthrough.write(s)
            except Exception:
                pass
        return super().write(s)

    def flush(self) -> None:
        super().flush()
        if self._passthrough is not None:
            try:
                self._passthrough.flush()
            except Exception:
                pass


class MpQueueWriter(LineBufferingWriter):
    """Child-process side: forwards lines onto a multiprocessing queue."""

    def __init__(self, log_q, stream_name: str) -> None:
        super().__init__(stream_name)
        self._log_q = log_q

    def _emit_line(self, text: str, replace_last: bool) -> None:
        try:
            self._log_q.put((text, self._stream_name, replace_last))
        except Exception:
            pass


class ConsoleLogHandler(logging.Handler):
    def __init__(self, sink: ConsoleSink) -> None:
        super().__init__()
        self._sink = sink

    def emit(self, record: logging.LogRecord) -> None:
        try:
            stream = STREAM_STDERR if record.levelno >= logging.WARNING else STREAM_INFO
            self._sink.put(self.format(record), stream)
        except Exception:
            pass


class MpLogBridge:
    """Drains a multiprocessing log queue into a :class:`ConsoleSink`."""

    def __init__(self, log_q, sink: ConsoleSink) -> None:
        self._log_q = log_q
        self._sink = sink
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        try:
            self._log_q.put(MP_LOG_SENTINEL)
        except Exception:
            pass

    def _run(self) -> None:
        while True:
            try:
                item = self._log_q.get()
            except Exception:
                break
            if item is MP_LOG_SENTINEL:
                break
            try:
                text, stream, replace_last = item
                self._sink.put(str(text), str(stream), bool(replace_last))
            except Exception:
                continue


def redirect_child_process_output(log_q) -> None:
    """Install ``sys.stdout``/``sys.stderr`` writers in a worker process."""
    sys.stdout = MpQueueWriter(log_q, STREAM_STDOUT)
    sys.stderr = MpQueueWriter(log_q, STREAM_STDERR)


def install_console_redirectors(sink: ConsoleSink) -> None:
    """Redirect this process's stdout/stderr and root logging into *sink*."""
    sys.stdout = TkStreamRedirector(sink, STREAM_STDOUT, passthrough=sys.stdout)
    sys.stderr = TkStreamRedirector(sink, STREAM_STDERR, passthrough=sys.stderr)

    handler = ConsoleLogHandler(sink)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(handler)


class LineRing:
    """Tracks console line count against a cap; reports lines to evict."""

    def __init__(self, max_lines: int = 5000) -> None:
        if max_lines <= 0:
            raise ValueError("max_lines must be positive")
        self.max_lines = max_lines
        self.count = 0

    def add(self, added: int = 1) -> int:
        """Record *added* lines; return how many oldest lines to delete."""
        self.count += added
        overflow = max(0, self.count - self.max_lines)
        self.count -= overflow
        return overflow

    def replace_last(self) -> None:
        """A replace-last line keeps the count unchanged."""

    def clear(self) -> None:
        self.count = 0
