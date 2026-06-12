from __future__ import annotations

import os
import subprocess
import threading
import time
from typing import Callable

import cv2
import numpy
from natsort import natsorted

from .models import _package_dir

EXIFTOOL_ASSET_NAMES = ("exiftool.exe", "exiftool_12.70.exe", "exiftool_12.68.exe")


def image_read(file_path: str) -> numpy.ndarray:
    with open(file_path, "rb") as file:
        return cv2.imdecode(numpy.frombuffer(file.read(), numpy.uint8), cv2.IMREAD_UNCHANGED)


def image_write(file_path: str, file_data: numpy.ndarray, file_extension: str = ".jpg") -> None:
    cv2.imencode(file_extension, file_data)[1].tofile(file_path)


def get_ffmpeg_exe() -> str:
    try:
        from static_ffmpeg import run as static_ffmpeg_run
    except ImportError:
        static_ffmpeg_run = None

    if static_ffmpeg_run is not None:
        ffmpeg_path, _ffprobe_path = static_ffmpeg_run.get_or_fetch_platform_executables_else_raise()
        return str(ffmpeg_path)

    bundled_path = os.path.join(_package_dir(), "Assets", "ffmpeg.exe")
    if os.path.exists(bundled_path):
        return bundled_path

    raise RuntimeError(
        "ffmpeg not found: install the 'static-ffmpeg' package or place ffmpeg.exe in the qualityscaler Assets directory"
    )


def _find_exiftool() -> str | None:
    assets_dir = os.path.join(_package_dir(), "Assets")
    for asset_name in EXIFTOOL_ASSET_NAMES:
        asset_path = os.path.join(assets_dir, asset_name)
        if os.path.exists(asset_path):
            return asset_path
    return None


def copy_file_metadata(original_file_path: str, upscaled_file_path: str) -> None:
    exiftool_path = _find_exiftool()
    if exiftool_path is None:
        return

    exiftool_cmd = [
        exiftool_path,
        "-fast",
        "-TagsFromFile",
        original_file_path,
        "-overwrite_original",
        "-all:all",
        "-unsafe",
        "-largetags",
        upscaled_file_path,
    ]
    try:
        subprocess.run(exiftool_cmd, check=True)
    except Exception:
        pass


def get_video_fps(video_path: str) -> float:
    video_capture = cv2.VideoCapture(video_path)
    frame_rate = video_capture.get(cv2.CAP_PROP_FPS)
    video_capture.release()
    return frame_rate


def get_video_frame_count(video_path: str) -> int:
    video_capture = cv2.VideoCapture(video_path)
    frame_count = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
    video_capture.release()
    return frame_count


def resize_with_output_factor(image: numpy.ndarray, output_resize_factor: float) -> numpy.ndarray:
    old_height, old_width = image.shape[0], image.shape[1]

    new_width = int(old_width * output_resize_factor)
    new_height = int(old_height * output_resize_factor)

    new_width = new_width if new_width % 2 == 0 else new_width + 1
    new_height = new_height if new_height % 2 == 0 else new_height + 1

    return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)


def blend_images_and_save(
    target_path: str,
    starting_image: numpy.ndarray,
    upscaled_image: numpy.ndarray,
    starting_image_importance: float,
    file_extension: str = ".jpg",
) -> None:
    def add_alpha_channel(image: numpy.ndarray) -> numpy.ndarray:
        if image.shape[2] == 3:
            alpha = numpy.full((image.shape[0], image.shape[1], 1), 255, dtype=numpy.uint8)
            image = numpy.concatenate((image, alpha), axis=2)
        return image

    def get_image_mode(image: numpy.ndarray) -> str:
        shape = image.shape
        if len(shape) == 2:
            return "Grayscale"
        if len(shape) == 3 and shape[2] == 3:
            return "RGB"
        if len(shape) == 3 and shape[2] == 4:
            return "RGBA"
        return "Unknown"

    target_height, target_width = upscaled_image.shape[0], upscaled_image.shape[1]
    starting_image = cv2.resize(starting_image, (target_width, target_height), interpolation=cv2.INTER_LINEAR)

    try:
        if get_image_mode(starting_image) == "RGBA":
            starting_image = add_alpha_channel(starting_image)
            upscaled_image = add_alpha_channel(upscaled_image)

        interpolated_image = cv2.addWeighted(starting_image, starting_image_importance, upscaled_image, (1 - starting_image_importance), 0)
        image_write(target_path, interpolated_image, file_extension)
    except Exception:
        image_write(target_path, upscaled_image, file_extension)


def _startupinfo():
    if os.name == "nt":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return startupinfo
    return None


def extract_video_frames(
    video_path: str,
    target_directory: str,
    cancel: threading.Event,
    on_progress: Callable[[float], None] | None = None,
) -> list[str]:
    import shutil

    total_frames = get_video_frame_count(video_path)
    video_fps = get_video_fps(video_path)

    if os.path.exists(target_directory):
        shutil.rmtree(target_directory)
    os.makedirs(target_directory, exist_ok=True)

    output_pattern = os.path.join(target_directory, "frame_%03d.jpg")
    extraction_command = [
        get_ffmpeg_exe(),
        "-y",
        "-loglevel", "error",
        "-err_detect", "ignore_err",
        "-i", video_path,
        "-vf", f"fps={video_fps}",
        "-qscale:v", "1",
        output_pattern,
    ]

    ffmpeg_process = subprocess.Popen(extraction_command, startupinfo=_startupinfo())
    last_report = time.monotonic()
    try:
        while ffmpeg_process.poll() is None:
            if cancel.is_set():
                ffmpeg_process.terminate()
                ffmpeg_process.wait()
                return []
            now = time.monotonic()
            if on_progress is not None and total_frames > 0 and now - last_report >= 1.0:
                last_report = now
                extracted = len([f for f in os.listdir(target_directory) if f.startswith("frame_")])
                on_progress(min(extracted / total_frames, 1.0))
            time.sleep(0.1)
    except Exception:
        ffmpeg_process.kill()
        raise

    if ffmpeg_process.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed with exit code {ffmpeg_process.returncode}")

    return [
        os.path.join(target_directory, f)
        for f in natsorted(os.listdir(target_directory))
        if f.endswith(".jpg") and f.startswith("frame_")
    ]


def encode_video(
    video_path: str,
    video_output_path: str,
    upscaled_frame_paths: list[str],
    video_fps: float,
    video_codec: str,
    target_width: int,
    target_height: int,
) -> None:
    ffmpeg_txt_file_path = f"{os.path.splitext(video_output_path)[0]}.txt"
    if os.path.exists(ffmpeg_txt_file_path):
        os.remove(ffmpeg_txt_file_path)

    with open(ffmpeg_txt_file_path, "w", encoding="utf-8") as txt:
        for frame_path in upscaled_frame_paths:
            if os.path.exists(frame_path):
                normalized_path = os.path.abspath(frame_path).replace("\\", "/")
                txt.write(f"file '{normalized_path}' \n")

    effective_codec = {"x264": "libx264", "x265": "libx265"}.get(video_codec, video_codec)
    codecs_to_try = [effective_codec, "libx264"] if effective_codec != "libx264" else ["libx264"]

    last_error: Exception | None = None
    for current_codec in codecs_to_try:
        encoding_command = [
            get_ffmpeg_exe(),
            "-y",
            "-loglevel", "error",
            "-f", "concat",
            "-safe", "0",
            "-r", str(video_fps),
            "-i", ffmpeg_txt_file_path,
            "-i", video_path,
            "-map", "0:v:0",
            "-map", "1:a?",
            "-c:v", str(current_codec),
            "-c:a", "copy",
            "-g", str(video_fps),
            "-vf", f"scale={target_width}:{target_height},format=yuv420p",
            "-color_range", "tv",
            "-movflags", "+faststart",
            "-b:v", "50000k",
            video_output_path,
        ]
        try:
            subprocess.run(encoding_command, check=True, startupinfo=_startupinfo())
            if os.path.exists(ffmpeg_txt_file_path):
                os.remove(ffmpeg_txt_file_path)
            return
        except Exception as exc:
            last_error = exc
            if os.path.exists(video_output_path):
                os.remove(video_output_path)

    raise RuntimeError(f"video encoding failed for {video_path}: {last_error}")
