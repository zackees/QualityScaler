"""``python -m qualityscaler.webview [--dev-url URL]`` entry point."""

from __future__ import annotations

import sys

from qualityscaler.webview.host import main

if __name__ == "__main__":
    sys.exit(main())
