"""System-webview host for QualityScaler (opt-in; the CTk GUI stays default).

Submodules:

- :mod:`qualityscaler.webview.ws` -- loopback WebSocket server that streams
  log + pipeline event frames to the frontend.
- :mod:`qualityscaler.webview.js_api` -- ``PyApi`` RPC class exposed to the
  TypeScript frontend through pywebview's ``js_api`` bridge.
- :mod:`qualityscaler.webview.host` -- window/process entry point
  (``python -m qualityscaler.webview``).

pywebview and websockets are imported lazily so this package (and its
submodules) can be imported in test environments without them installed.
"""
