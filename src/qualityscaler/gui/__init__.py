"""Toolkit-free GUI support modules for QualityScaler.

Modules in this package must stay importable without customtkinter so they
can be exercised by the headless unit-test environment. ``media_info`` is the
one exception: it needs cv2/numpy and must not be imported from here.
"""
