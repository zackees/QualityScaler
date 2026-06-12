"""GUI package for QualityScaler.

The toolkit layer (customtkinter/tkinter) is confined to ``widgets`` and
``app``; every other module must stay importable without customtkinter so it
can be exercised by the headless unit-test environment (``media_info`` and
``widgets`` additionally need cv2/numpy). For that reason this package does
not import anything eagerly — use ``qualityscaler.gui.app.main`` to launch.
"""
