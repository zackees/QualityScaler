"""UI selection state and label/value conversion helpers.

Holds the user-facing label form of every persisted GUI choice, plus the
conversions between menu labels and the values the pipeline consumes.
Toolkit-free so it can be unit tested headlessly.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from qualityscaler.core import BLENDING_FACTORS
from qualityscaler.app.constants import (
    AI_models_list,
    AI_multithreading_list,
    MENU_LIST_SEPARATOR,
    OUTPUT_PATH_CODED,
    blending_list,
    gpus_list,
    image_extension_list,
    keep_frames_list,
    video_codec_list,
    video_extension_list,
)


# Single source of truth is qualityscaler.core.settings.BLENDING_FACTORS.
_BLENDING_LABEL_BY_FACTOR = {factor: label for label, factor in BLENDING_FACTORS.items()}


@dataclass
class UIState:
    """Persisted GUI selections, stored in their menu-label form."""

    app_zoom: str = "100%"
    ai_model: str = field(default_factory=lambda: AI_models_list[0])
    ai_multithreading: str = field(default_factory=lambda: AI_multithreading_list[0])
    gpu: str = field(default_factory=lambda: gpus_list[0])
    keep_frames: str = field(default_factory=lambda: keep_frames_list[1])
    image_extension: str = field(default_factory=lambda: image_extension_list[0])
    video_extension: str = field(default_factory=lambda: video_extension_list[0])
    video_codec: str = field(default_factory=lambda: video_codec_list[0])
    video_quality: str = "HIGH"
    blending: str = field(default_factory=lambda: blending_list[1])
    output_path: str = OUTPUT_PATH_CODED
    input_resize_factor: str = "50"
    output_resize_factor: str = "100"
    vram_limiter: str = "4"
    file_list: list = field(default_factory=list)


def multithreading_from_label(label: str) -> int:
    if label == "OFF":
        return 1
    return int(label.split()[0])


def multithreading_to_label(threads: int) -> str:
    if threads == 1:
        return "OFF"
    return f"{threads} threads"


def keep_frames_from_label(label: str) -> bool:
    return label == "ON"


def keep_frames_to_label(keep_frames: bool) -> str:
    return "ON" if keep_frames else "OFF"


def blending_from_label(label: str):
    return BLENDING_FACTORS.get(label)


def blending_to_label(factor) -> str:
    return _BLENDING_LABEL_BY_FACTOR.get(factor, "OFF")


def upscale_factor_for_model(ai_model: str) -> int:
    if MENU_LIST_SEPARATOR[0] in ai_model:
        return 0
    for suffix, factor in (('x1', 1), ('x2', 2), ('x3', 3), ('x4', 4)):
        if suffix in ai_model:
            return factor
    return 0
