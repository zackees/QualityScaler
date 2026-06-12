"""Fluid Frames UI selection state and label/value conversion helpers.

Toolkit-free so it can be unit tested headlessly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from qualityscaler.gui.constants import OUTPUT_PATH_CODED, gpus_list, keep_frames_list
from qualityscaler.gui.ff_constants import (
    FF_AI_models_list,
    FF_image_extension_list,
    FF_video_output_list,
    generation_options_list,
)

_VIDEO_OUTPUT_BY_LABEL = {
    ".mp4 (x264)": (".mp4", "x264"),
    ".mp4 (x265)": (".mp4", "x265"),
    ".avi":        (".avi", "x264"),
}


@dataclass
class FFUIState:
    """Persisted Fluid Frames selections, stored in their menu-label form."""

    ai_model: str = field(default_factory=lambda: FF_AI_models_list[0])
    generation_option: str = field(default_factory=lambda: generation_options_list[0])
    gpu: str = field(default_factory=lambda: gpus_list[0])
    keep_frames: str = field(default_factory=lambda: keep_frames_list[1])
    image_extension: str = field(default_factory=lambda: FF_image_extension_list[0])
    video_output: str = field(default_factory=lambda: FF_video_output_list[0])
    output_path: str = OUTPUT_PATH_CODED
    input_resize_factor: str = "50"
    cpu_number: str = "4"
    file_list: list = field(default_factory=list)


def generation_factor_from_label(label: str) -> tuple[int, bool]:
    """Return (frame_gen_factor, slowmotion) for a generation menu label."""
    slowmotion = "Slowmotion" in label
    factor = int(label.rsplit("x", 1)[1])
    return factor, slowmotion


def video_output_from_label(label: str) -> tuple[str, str]:
    """Return (video_extension, video_codec) for a video output menu label."""
    return _VIDEO_OUTPUT_BY_LABEL[label]
