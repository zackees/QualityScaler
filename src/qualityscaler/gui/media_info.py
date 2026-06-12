"""Image/video file helpers used by the file widget.

Requires cv2/numpy, so this module must not be imported by the headless
test targets (constants, state, preferences, info_texts).
"""

from __future__ import annotations

from cv2 import IMREAD_UNCHANGED, imdecode as opencv_imdecode
from numpy import frombuffer as numpy_frombuffer, ndarray as numpy_ndarray, uint8

from qualityscaler.gui.constants import supported_video_extensions


def image_read(file_path: str) -> numpy_ndarray:
    with open(file_path, 'rb') as file:
        return opencv_imdecode(
            numpy_frombuffer(file.read(), uint8),
            IMREAD_UNCHANGED
        )

def check_if_file_is_video(file: str) -> bool:
    return any(video_extension in file for video_extension in supported_video_extensions)

def get_image_resolution(image: numpy_ndarray) -> tuple:
    # Return height x width
    return image.shape[0], image.shape[1]
