"""Thin launcher shim kept for entry-point compatibility.

The GUI implementation lives in :mod:`qualityscaler.gui`. This file must keep
existing so ``python -m qualityscaler.QualityScaler`` (used by cli.py) and the
checkout-root detection keep working.
"""

from qualityscaler.gui.app import main

if __name__ == "__main__":
    main()
