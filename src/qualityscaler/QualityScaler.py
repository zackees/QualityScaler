"""Thin launcher shim kept for entry-point compatibility.

The GUI implementation lives in :mod:`qualityscaler.webview`. This file must
keep existing so ``python -m qualityscaler.QualityScaler`` (historical launch
module) and the checkout-root detection in cli.py keep working.
"""

import sys

from qualityscaler.webview.host import main

if __name__ == "__main__":
    sys.exit(main())
