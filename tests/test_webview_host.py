"""Tests for the webview host entry point (qualityscaler.webview.host).

host.py imports pywebview lazily inside main(), so these tests run without
pywebview installed (regression guards for issue #70: Windows registry maps
``.js`` to ``text/plain`` and WebView2 then rejects the ES module bundle).
"""

from __future__ import annotations

import inspect
import mimetypes

from qualityscaler.webview import host


def test_register_mime_types_overrides_polluted_registry() -> None:
    original_js = mimetypes.guess_type("x.js")[0]
    original_mjs = mimetypes.guess_type("x.mjs")[0]
    original_css = mimetypes.guess_type("x.css")[0]
    try:
        # Simulate the Windows registry pollution from issue #70.
        mimetypes.add_type("text/plain", ".js")
        assert mimetypes.guess_type("x.js") == ("text/plain", None)

        host._register_mime_types()

        assert mimetypes.guess_type("x.js") == ("text/javascript", None)
        assert mimetypes.guess_type("x.mjs") == ("text/javascript", None)
        assert mimetypes.guess_type("x.css") == ("text/css", None)
    finally:
        # mimetypes state is process-global; put back what we found.
        mimetypes.add_type(original_js or "text/javascript", ".js")
        mimetypes.add_type(original_mjs or "text/javascript", ".mjs")
        mimetypes.add_type(original_css or "text/css", ".css")


def test_main_registers_mime_types_before_webview_start() -> None:
    source = inspect.getsource(host.main)
    register_pos = source.find("_register_mime_types()")
    start_pos = source.find("webview.start(")
    assert register_pos != -1, "main() must call _register_mime_types()"
    assert start_pos != -1, "main() must call webview.start()"
    assert register_pos < start_pos, "MIME types must be registered before webview.start()"


def test_debug_flag_parsing() -> None:
    assert host._parse_args([]).debug is False
    assert host._parse_args(["--debug"]).debug is True
