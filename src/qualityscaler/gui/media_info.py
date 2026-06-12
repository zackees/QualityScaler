"""Image/video file helpers used by the file widget.

cv2/numpy are imported lazily inside the probing functions so the module
itself stays importable in headless test environments (no OpenCV/numpy),
keeping the pure formatting helpers unit-testable.
"""

from __future__ import annotations

from typing import Any

from qualityscaler.gui.constants import supported_video_extensions


def image_read(file_path: str) -> Any:
    from cv2 import IMREAD_UNCHANGED, imdecode as opencv_imdecode
    from numpy import frombuffer as numpy_frombuffer, uint8

    with open(file_path, 'rb') as file:
        return opencv_imdecode(
            numpy_frombuffer(file.read(), uint8),
            IMREAD_UNCHANGED
        )

def check_if_file_is_video(file: str) -> bool:
    return any(video_extension in file for video_extension in supported_video_extensions)

def get_image_resolution(image: Any) -> tuple:
    # Return height x width
    return image.shape[0], image.shape[1]


def format_resolution_projection(
        width: int,
        height: int,
        upscale_factor: int,
        input_resize_factor: int,
        output_resize_factor: int,
    ) -> str:
    """Pure arithmetic behind the file widget's resolution preview.

    Returns the three "AI input / AI output / File output" lines, or an
    empty string when any factor is unset (0).
    """
    if input_resize_factor == 0 or output_resize_factor == 0 or upscale_factor == 0:
        return ""

    input_resized_height = int(height * (input_resize_factor/100))
    input_resized_width  = int(width * (input_resize_factor/100))

    upscaled_height = int(input_resized_height * upscale_factor)
    upscaled_width  = int(input_resized_width * upscale_factor)

    output_resized_height = int(upscaled_height * (output_resize_factor/100))
    output_resized_width  = int(upscaled_width * (output_resize_factor/100))

    label_in  = f"AI input ({input_resize_factor}%)"
    label_ups = f"AI output (x{upscale_factor})"
    label_out = f"File output ({output_resize_factor}%)"

    return (
        f"{label_in}\t= {input_resized_width}x{input_resized_height}\n"
        f"{label_ups}\t= {upscaled_width}x{upscaled_height}\n"
        f"{label_out}\t= {output_resized_width}x{output_resized_height}"
    )


def describe_file(
        file_path: str,
        upscale_factor: int,
        input_resize_factor: int,
        output_resize_factor: int,
    ) -> str:
    """Build the info text shown next to a loaded file in the file widget."""
    if check_if_file_is_video(file_path):
        from cv2 import (
            CAP_PROP_FPS,
            CAP_PROP_FRAME_COUNT,
            CAP_PROP_FRAME_HEIGHT,
            CAP_PROP_FRAME_WIDTH,
            VideoCapture as opencv_VideoCapture,
        )

        cap        = opencv_VideoCapture(file_path)
        width      = round(cap.get(CAP_PROP_FRAME_WIDTH))
        height     = round(cap.get(CAP_PROP_FRAME_HEIGHT))
        num_frames = int(cap.get(CAP_PROP_FRAME_COUNT))
        frame_rate = cap.get(CAP_PROP_FPS)
        duration   = num_frames/frame_rate
        minutes    = int(duration/60)
        seconds    = duration % 60
        cap.release()

        file_infos = f"{minutes}m:{round(seconds)}s - {num_frames}frames - {width}x{height} \n"
    else:
        height, width = get_image_resolution(image_read(file_path))
        file_infos    = f"{width}x{height}\n"

    return file_infos + format_resolution_projection(
        width, height, upscale_factor, input_resize_factor, output_resize_factor
    )
