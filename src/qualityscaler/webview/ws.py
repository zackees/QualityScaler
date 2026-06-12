"""Loopback WebSocket server streaming log + pipeline event frames.

Runs the ``websockets`` asyncio server in a daemon thread with its own event
loop, bound to ``127.0.0.1`` on an OS-assigned port. Producers call
:meth:`WsServer.broadcast` from any thread; frames are queued and flushed in
coalesced batches (~16ms) so high-frequency ffmpeg output never floods the
loop with one wakeup per line.

The ``websockets`` import is deferred to :meth:`WsServer.start` so this
module stays importable when the dependency is missing.
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from typing import Any, Callable, Optional

from qualityscaler.app.console_log import ConsoleSink
from qualityscaler.app.events import event_to_wire, log_to_wire, to_json

_SENTINEL = object()

_START_TIMEOUT_SECONDS = 10.0
_BATCH_INTERVAL_SECONDS = 0.016


class WsServer:
    """Thread-safe WebSocket broadcast server on ``ws://127.0.0.1:<port>``."""

    def __init__(
        self,
        console_sink: Optional[ConsoleSink] = None,
        batch_interval: float = _BATCH_INTERVAL_SECONDS,
    ) -> None:
        self._console_sink = console_sink
        self._batch_interval = batch_interval

        self._out_q: queue.Queue[Any] = queue.Queue()
        self._clients: set = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._shutdown_event: Optional[asyncio.Event] = None
        self._port: Optional[int] = None
        self._started = threading.Event()
        self._stopped = threading.Event()
        self._start_error: Optional[BaseException] = None
        self._threads: list[threading.Thread] = []

    # Public API ---------------------------

    def start(self) -> None:
        """Start the server loop and the background pump threads."""
        if self._threads:
            raise RuntimeError("WsServer.start() called twice")

        server_thread = threading.Thread(target=self._run_loop, name="ws-server", daemon=True)
        server_thread.start()
        self._threads.append(server_thread)

        if not self._started.wait(timeout=_START_TIMEOUT_SECONDS):
            raise RuntimeError("WebSocket server did not start in time")
        if self._start_error is not None:
            raise RuntimeError(f"WebSocket server failed to start: {self._start_error}") from self._start_error

        sender_thread = threading.Thread(target=self._sender_pump, name="ws-sender", daemon=True)
        sender_thread.start()
        self._threads.append(sender_thread)

        if self._console_sink is not None:
            log_thread = threading.Thread(target=self._log_pump, name="ws-log-pump", daemon=True)
            log_thread.start()
            self._threads.append(log_thread)

    @property
    def url(self) -> str:
        if self._port is None:
            raise RuntimeError("WebSocket server is not running (call start() first)")
        return f"ws://127.0.0.1:{self._port}"

    @property
    def client_count(self) -> int:
        return len(self._clients)

    def broadcast(self, frame: dict) -> None:
        """Queue a wire frame for delivery to all connected clients.

        Thread-safe and non-blocking; frames queued before any client
        connects are delivered only to clients connected at flush time.
        """
        self._out_q.put(to_json(frame))

    def event_forwarder(self, kind: str) -> Callable[[object], None]:
        """Return an ``on_event`` callback that broadcasts pipeline events."""

        def forward(event: object) -> None:
            try:
                self.broadcast(event_to_wire(event, kind))
            except ValueError:
                # Unknown event object (e.g. raw status strings): ignore.
                pass

        return forward

    def stop(self) -> None:
        """Stop the server and the pump threads."""
        self._stopped.set()
        self._out_q.put(_SENTINEL)

        loop = self._loop
        shutdown_event = self._shutdown_event
        if loop is not None and shutdown_event is not None and loop.is_running():
            try:
                loop.call_soon_threadsafe(shutdown_event.set)
            except RuntimeError:
                pass

        for thread in self._threads:
            thread.join(timeout=5.0)

    # Server loop ---------------------------

    def _run_loop(self) -> None:
        try:
            from websockets.asyncio.server import serve
        except ImportError as exc:
            self._start_error = exc
            self._started.set()
            return

        async def main() -> None:
            self._loop = asyncio.get_running_loop()
            self._shutdown_event = asyncio.Event()
            async with serve(self._handler, "127.0.0.1", 0) as server:
                self._port = server.sockets[0].getsockname()[1]
                self._started.set()
                await self._shutdown_event.wait()

        try:
            asyncio.run(main())
        except BaseException as exc:  # noqa: BLE001 - report any startup failure
            if not self._started.is_set():
                self._start_error = exc
                self._started.set()

    async def _handler(self, connection) -> None:
        self._clients.add(connection)
        try:
            async for _message in connection:
                pass  # The frontend never sends; RPC goes through js_api.
        finally:
            self._clients.discard(connection)

    async def _send_batch(self, payloads: list[str]) -> None:
        from websockets.asyncio.server import broadcast

        clients = list(self._clients)
        if not clients:
            return
        for payload in payloads:
            broadcast(clients, payload)

    # Pump threads ---------------------------

    def _sender_pump(self) -> None:
        while not self._stopped.is_set():
            try:
                first = self._out_q.get(timeout=0.1)
            except queue.Empty:
                continue
            if first is _SENTINEL:
                break

            # Coalesce: wait one batch interval, then drain whatever piled up.
            time.sleep(self._batch_interval)
            batch = [first]
            while True:
                try:
                    item = self._out_q.get_nowait()
                except queue.Empty:
                    break
                if item is _SENTINEL:
                    self._stopped.set()
                    break
                batch.append(item)

            loop = self._loop
            if loop is None or not loop.is_running():
                continue
            try:
                future = asyncio.run_coroutine_threadsafe(self._send_batch(batch), loop)
                future.result(timeout=5.0)
            except Exception:
                # Loop shut down or a client misbehaved; keep pumping.
                continue

    def _log_pump(self) -> None:
        assert self._console_sink is not None
        while not self._stopped.is_set():
            lines = self._console_sink.drain_blocking(timeout=0.1)
            for line in lines:
                # ConsoleSink strips the terminators while splitting; restore
                # them so xterm.js sees real newlines and \r progress updates.
                text = line.text + ("\r" if line.replace_last else "\n")
                self.broadcast(log_to_wire(text, line.stream))
