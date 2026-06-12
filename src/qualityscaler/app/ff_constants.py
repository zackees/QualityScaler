"""Static constants for the Fluid Frames mode: branding and menu option lists.

This module must stay free of third-party imports so it can be loaded in the
headless unit-test environment.
"""

from __future__ import annotations

ff_mode_name = "FluidFrames"
ff_githubme  = "https://github.com/zackees/FluidFrames.RIFE"

FF_AI_models_list = ["RIFE", "RIFE_Lite"]

generation_options_list = [
    "x2", "x4", "x8",
    "Slowmotion x2", "Slowmotion x4", "Slowmotion x8",
]

FF_image_extension_list = [".jpg", ".png"]
FF_video_output_list    = [".mp4 (x264)", ".mp4 (x265)", ".avi"]
