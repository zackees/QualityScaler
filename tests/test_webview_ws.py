"""WsServer integration tests (skipped when websockets is not installed)."""

from __future__ import annotations

import json
import time

import pytest

websockets = pytest.importorskip("websockets")

from websockets.sync.client import connect as ws_connect  # noqa: E402

from qualityscaler.app.console_log import ConsoleSink  # noqa: E402
from qualityscaler.app.events import KIND_UPSCALE  # noqa: E402
from qualityscaler.core import UpscaleProgress  # noqa: E402
from qualityscaler.webview.ws import WsServer  # noqa: E402

_RECV_TIMEOUT = 5.0


def _wait_for_client(server: WsServer, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while server.client_count < 1:
        if time.monotonic() > deadline:
            pytest.fail("client did not register with the server in time")
        time.sleep(0.01)


@pytest.fixture
def sink() -> ConsoleSink:
    return ConsoleSink(strip_ansi=False)


@pytest.fixture
def server(sink: ConsoleSink):
    server = WsServer(console_sink=sink, batch_interval=0.005)
    server.start()
    yield server
    server.stop()


def test_url_reports_loopback_with_assigned_port(server: WsServer) -> None:
    assert server.url.startswith("ws://127.0.0.1:")
    port = int(server.url.rsplit(":", 1)[1])
    assert 0 < port < 65536


def test_url_before_start_raises() -> None:
    with pytest.raises(RuntimeError):
        _ = WsServer().url


def test_broadcast_reaches_connected_client(server: WsServer) -> None:
    with ws_connect(server.url) as client:
        _wait_for_client(server)
        server.broadcast({"type": "engine_info", "text": "hello"})

        frame = json.loads(client.recv(timeout=_RECV_TIMEOUT))
        assert frame == {"type": "engine_info", "text": "hello"}


def test_broadcast_coalesces_multiple_frames_in_order(server: WsServer) -> None:
    with ws_connect(server.url) as client:
        _wait_for_client(server)
        for index in range(5):
            server.broadcast({"type": "progress", "kind": "upscale", "n": index})

        received = [json.loads(client.recv(timeout=_RECV_TIMEOUT)) for _ in range(5)]
        assert [frame["n"] for frame in received] == [0, 1, 2, 3, 4]


def test_event_forwarder_broadcasts_wire_event(server: WsServer) -> None:
    forward = server.event_forwarder(KIND_UPSCALE)
    with ws_connect(server.url) as client:
        _wait_for_client(server)
        forward(UpscaleProgress(message="Upscaling video", file_index=1, fraction=0.25))
        forward("a raw status string the wire schema does not know")  # must not raise

        frame = json.loads(client.recv(timeout=_RECV_TIMEOUT))
        assert frame["type"] == "progress"
        assert frame["kind"] == "upscale"
        assert frame["message"] == "Upscaling video"
        assert frame["file_index"] == 1
        assert frame["fraction"] == 0.25


def test_log_pump_forwards_console_sink_lines(server: WsServer, sink: ConsoleSink) -> None:
    with ws_connect(server.url) as client:
        _wait_for_client(server)
        sink.put("plain line", "stdout")
        sink.put("progress 42%", "stderr", replace_last=True)

        first = json.loads(client.recv(timeout=_RECV_TIMEOUT))
        second = json.loads(client.recv(timeout=_RECV_TIMEOUT))

        assert first == {"type": "log", "stream": "stdout", "text": "plain line\n"}
        # replace_last (lone \r) lines keep their carriage return for xterm.js.
        assert second == {"type": "log", "stream": "stderr", "text": "progress 42%\r"}


def test_log_pump_preserves_ansi_escapes(server: WsServer, sink: ConsoleSink) -> None:
    with ws_connect(server.url) as client:
        _wait_for_client(server)
        sink.put("\x1b[32mgreen\x1b[0m", "stdout")

        frame = json.loads(client.recv(timeout=_RECV_TIMEOUT))
        assert frame["text"] == "\x1b[32mgreen\x1b[0m\n"


def test_stop_is_idempotent_and_joins_threads(sink: ConsoleSink) -> None:
    server = WsServer(console_sink=sink)
    server.start()
    server.stop()
    server.stop()  # second stop must not raise
