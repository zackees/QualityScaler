"""Webview host entry point: native window + WebSocket + RPC bridge.

Wires up the console sink + redirectors and the controllers with a log sink
(``freeze_support`` first), then renders the UI in a system webview
(pywebview / WebView2 on Windows).

Run with ``python -m qualityscaler.webview`` for the bundled frontend, or
``python -m qualityscaler.webview --dev-url http://localhost:5173`` against a
running Vite dev server.
"""

from __future__ import annotations

import argparse
import mimetypes
import sys
from importlib.resources import files as importlib_resources_files
from multiprocessing import freeze_support as multiprocessing_freeze_support
from os import devnull as os_devnull

from qualityscaler.app.constants import app_name, version

WEBVIEW2_HELP_URL = "https://developer.microsoft.com/en-us/microsoft-edge/webview2/"

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 860


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="qualityscaler.webview",
        description="QualityScaler system-webview GUI host.",
    )
    parser.add_argument(
        "--dev-url",
        default=None,
        metavar="URL",
        help="Load the frontend from a Vite dev server (e.g. http://localhost:5173) "
        "instead of the bundled assets.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable pywebview debug mode (devtools) even with the bundled assets.",
    )
    return parser.parse_args(argv)


def _register_mime_types() -> None:
    """Force correct MIME types for the bundled frontend (see issue #70).

    On Windows, ``mimetypes`` reads the registry, where ``.js`` is often
    mapped to ``text/plain``; WebView2 then rejects the ES module bundle and
    the window stays blank. ``add_type`` overrides any registry value.
    """
    mimetypes.add_type("text/javascript", ".js")
    mimetypes.add_type("text/javascript", ".mjs")
    mimetypes.add_type("text/css", ".css")


def _bundled_index_path() -> str | None:
    """Absolute path of the built frontend's index.html, or None if missing."""
    try:
        index = importlib_resources_files("qualityscaler.webview") / "assets" / "index.html"
        if index.is_file():
            return str(index)
    except (ModuleNotFoundError, FileNotFoundError, OSError):
        pass
    return None


def _print_webview_start_failure(exc: BaseException) -> None:
    print(f"[{app_name}] Failed to start the webview window: {exc}", file=sys.stderr)
    print(
        f"[{app_name}] On Windows this usually means the Microsoft Edge WebView2 "
        "runtime is missing.\n"
        f"[{app_name}] Install it from: {WEBVIEW2_HELP_URL}",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    multiprocessing_freeze_support()

    args = _parse_args(list(sys.argv[1:]) if argv is None else list(argv))

    # Frozen/no-console launches can have None std streams (same guard as gui/app.py).
    if sys.stdout is None:
        sys.stdout = open(os_devnull, "w", encoding="utf-8", errors="replace")
    if sys.stderr is None:
        sys.stderr = open(os_devnull, "w", encoding="utf-8", errors="replace")

    try:
        import webview
    except ImportError as exc:
        print(
            f"[{app_name}] pywebview is not installed ({exc}). "
            "Install it with: pip install pywebview",
            file=sys.stderr,
        )
        return 1

    if args.dev_url is not None:
        frontend_url = args.dev_url
    else:
        frontend_url = _bundled_index_path()
        if frontend_url is None:
            print(
                f"[{app_name}] Bundled frontend assets not found "
                "(qualityscaler/webview/assets/index.html).\n"
                f"[{app_name}] Build the frontend first (see frontend/) or pass "
                "--dev-url http://localhost:5173",
                file=sys.stderr,
            )
            return 1

    from qualityscaler.app.assets import ensure_assets
    from qualityscaler.app.console_log import ConsoleSink, install_console_redirectors
    from qualityscaler.app.controllers.framegen import FrameGenController
    from qualityscaler.app.controllers.upscale import UpscaleController
    from qualityscaler.webview.js_api import PyApi
    from qualityscaler.webview.ws import WsServer

    ensure_assets()

    # Raw text (ANSI + \r progress) goes straight to xterm.js in the frontend.
    console_sink = ConsoleSink()
    install_console_redirectors(console_sink)

    upscale_controller = UpscaleController(log_sink=console_sink)
    framegen_controller = FrameGenController(log_sink=console_sink)

    ws_server = WsServer(console_sink=console_sink)
    try:
        ws_server.start()
    except RuntimeError as exc:
        print(f"[{app_name}] {exc}", file=sys.stderr)
        upscale_controller.notify_close()
        framegen_controller.notify_close()
        return 1

    api = PyApi(upscale_controller, framegen_controller, ws=ws_server)

    window = webview.create_window(
        title=f"{app_name} {version}",
        url=frontend_url,
        js_api=api,
        width=WINDOW_WIDTH,
        height=WINDOW_HEIGHT,
        min_size=(960, 640),
    )
    api._set_window(window)

    _register_mime_types()

    exit_code = 0
    try:
        webview.start(http_server=True, debug=args.debug or args.dev_url is not None)
    except Exception as exc:  # WebView2 runtime missing, GTK/Qt deps missing, ...
        _print_webview_start_failure(exc)
        exit_code = 1
    finally:
        upscale_controller.notify_close()
        framegen_controller.notify_close()
        ws_server.stop()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
