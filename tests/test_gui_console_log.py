from __future__ import annotations

import logging
import queue
import time

from qualityscaler.gui.console_log import (
    MP_LOG_SENTINEL,
    ConsoleLogHandler,
    ConsoleSink,
    LineRing,
    MpLogBridge,
    MpQueueWriter,
    TkStreamRedirector,
    split_terminal_text,
    strip_ansi,
)


class TestSplitTerminalText:
    def test_newline_terminated_lines(self) -> None:
        lines, remainder = split_terminal_text("one\ntwo\n")
        assert lines == [("one", False), ("two", False)]
        assert remainder == ""

    def test_partial_line_kept_as_remainder(self) -> None:
        lines, remainder = split_terminal_text("one\npart")
        assert lines == [("one", False)]
        assert remainder == "part"

    def test_crlf_is_a_plain_newline(self) -> None:
        lines, remainder = split_terminal_text("one\r\ntwo\r\n")
        assert lines == [("one", False), ("two", False)]
        assert remainder == ""

    def test_lone_cr_flags_replace_last(self) -> None:
        lines, remainder = split_terminal_text("frame=10\rframe=20\r")
        assert lines == [("frame=10", True), ("frame=20", True)]
        assert remainder == ""


class TestStripAnsi:
    def test_removes_color_codes(self) -> None:
        assert strip_ansi("\x1b[31mred\x1b[0m") == "red"

    def test_plain_text_unchanged(self) -> None:
        assert strip_ansi("plain") == "plain"


class TestConsoleSink:
    def test_drain_returns_put_lines_in_order(self) -> None:
        sink = ConsoleSink()
        sink.put("a")
        sink.put("b", "stderr")

        lines = sink.drain()
        assert [(line.text, line.stream) for line in lines] == [("a", "stdout"), ("b", "stderr")]

    def test_drain_respects_max_items(self) -> None:
        sink = ConsoleSink()
        for i in range(10):
            sink.put(str(i))

        first = sink.drain(max_items=3)
        rest = sink.drain(max_items=100)
        assert len(first) == 3
        assert len(rest) == 7

    def test_drain_on_empty_sink(self) -> None:
        assert ConsoleSink().drain() == []

    def test_put_strips_ansi(self) -> None:
        sink = ConsoleSink()
        sink.put("\x1b[1mbold\x1b[0m")
        assert sink.drain()[0].text == "bold"


class TestTkStreamRedirector:
    def test_buffers_partial_writes(self) -> None:
        sink = ConsoleSink()
        writer = TkStreamRedirector(sink, "stdout")

        writer.write("hello ")
        assert sink.drain() == []
        writer.write("world\n")
        assert sink.drain()[0].text == "hello world"

    def test_flush_emits_pending_buffer(self) -> None:
        sink = ConsoleSink()
        writer = TkStreamRedirector(sink, "stdout")

        writer.write("pending")
        writer.flush()
        assert sink.drain()[0].text == "pending"

    def test_carriage_return_sets_replace_flag(self) -> None:
        sink = ConsoleSink()
        writer = TkStreamRedirector(sink, "stderr")

        writer.write("frame=1\rframe=2\r")
        lines = sink.drain()
        assert [(line.text, line.replace_last) for line in lines] == [("frame=1", True), ("frame=2", True)]

    def test_passthrough_receives_raw_writes(self) -> None:
        class Recorder:
            def __init__(self) -> None:
                self.data = ""

            def write(self, s: str) -> None:
                self.data += s

            def flush(self) -> None:
                pass

        recorder = Recorder()
        writer = TkStreamRedirector(ConsoleSink(), "stdout", passthrough=recorder)
        writer.write("raw\n")
        assert recorder.data == "raw\n"


class TestConsoleLogHandler:
    def test_routes_records_by_level(self) -> None:
        sink = ConsoleSink()
        handler = ConsoleLogHandler(sink)
        logger = logging.Logger("console-test")
        logger.addHandler(handler)

        logger.info("info message")
        logger.error("error message")

        lines = sink.drain()
        assert lines[0].stream == "info"
        assert lines[1].stream == "stderr"


class TestMpQueueWriterAndBridge:
    def test_lines_flow_from_writer_through_bridge_to_sink(self) -> None:
        log_q: queue.Queue = queue.Queue()
        sink = ConsoleSink()

        writer = MpQueueWriter(log_q, "stdout")
        writer.write("from child\n")

        bridge = MpLogBridge(log_q, sink)
        bridge.start()
        try:
            deadline = time.monotonic() + 5
            lines = []
            while not lines and time.monotonic() < deadline:
                lines = sink.drain()
                time.sleep(0.01)
        finally:
            bridge.stop()

        assert [(line.text, line.stream) for line in lines] == [("from child", "stdout")]

    def test_bridge_stops_on_sentinel(self) -> None:
        log_q: queue.Queue = queue.Queue()
        bridge = MpLogBridge(log_q, ConsoleSink())
        bridge.start()
        log_q.put(MP_LOG_SENTINEL)
        bridge._thread.join(timeout=5)
        assert not bridge._thread.is_alive()


class TestLineRing:
    def test_no_overflow_below_cap(self) -> None:
        ring = LineRing(max_lines=3)
        assert ring.add(2) == 0
        assert ring.count == 2

    def test_overflow_returns_lines_to_evict(self) -> None:
        ring = LineRing(max_lines=3)
        ring.add(3)
        assert ring.add(2) == 2
        assert ring.count == 3

    def test_clear_resets_count(self) -> None:
        ring = LineRing(max_lines=3)
        ring.add(3)
        ring.clear()
        assert ring.count == 0
        assert ring.add(1) == 0
