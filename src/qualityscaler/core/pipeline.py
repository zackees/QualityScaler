from __future__ import annotations

import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .events import UpscaleEvent, UpscaleProgress
from .settings import UpscaleSettings

SUPPORTED_VIDEO_EXTENSIONS = [
    ".mp4", ".webm", ".mkv", ".flv", ".gif", ".m4v",
    ".avi", ".mov", ".qt", ".3gp", ".mpg", ".mpeg", ".vob",
]


def check_if_file_is_video(file_path: str) -> bool:
    extension = os.path.splitext(file_path)[1].lower()
    return extension in SUPPORTED_VIDEO_EXTENSIONS


def _upscale_factor(ai_model: str) -> int:
    if "x1" in ai_model:
        return 1
    if "x2" in ai_model:
        return 2
    if "x3" in ai_model:
        return 3
    if "x4" in ai_model:
        return 4
    raise ValueError(f"Cannot derive upscale factor from model name: {ai_model}")


def _output_base(input_path: str, output_dir: str | None) -> str:
    if output_dir is None:
        return os.path.splitext(input_path)[0]
    file_name_no_extension = os.path.splitext(os.path.basename(input_path))[0]
    return os.path.join(output_dir, file_name_no_extension)


def _filename_suffix(settings: UpscaleSettings) -> str:
    suffix = f"_{settings.ai_model}"
    suffix += f"_InputR-{int(settings.input_resize_factor * 100)}"
    suffix += f"_OutputR-{int(settings.output_resize_factor * 100)}"
    if settings.blending != "OFF":
        suffix += f"_Blending-{settings.blending}"
    return suffix


def prepare_output_image_filename(image_path: str, settings: UpscaleSettings) -> str:
    return _output_base(image_path, settings.output_path) + _filename_suffix(settings) + settings.image_extension


def prepare_output_video_filename(video_path: str, settings: UpscaleSettings) -> str:
    return _output_base(video_path, settings.output_path) + _filename_suffix(settings) + settings.video_extension


def prepare_output_video_directory_name(video_path: str, settings: UpscaleSettings) -> str:
    return _output_base(video_path, settings.output_path) + _filename_suffix(settings)


def prepare_upscaled_frame_filename(frame_path: str, settings: UpscaleSettings) -> str:
    return os.path.splitext(frame_path)[0] + _filename_suffix(settings) + ".jpg"


def _calculate_input_resolution(original_height: int, original_width: int, input_resize_factor: float) -> tuple[int, int]:
    aspect_ratio = original_width / original_height
    input_width = round((original_width * input_resize_factor) / 2) * 2
    input_height = round((input_width / aspect_ratio) / 2) * 2
    return input_height, input_width


def _calculate_output_resolution(input_height: int, input_width: int, upscale_factor: int, output_resize_factor: float) -> tuple[int, int]:
    aspect_ratio = input_width / input_height
    target_width = round((input_width * upscale_factor * output_resize_factor) / 2) * 2
    target_height = round((target_width / aspect_ratio) / 2) * 2
    return target_height, target_width


def _calculate_optimal_threads_number(tiles_resolution: int, input_pixels: int, multithreading: int) -> int:
    max_supported_pixels = tiles_resolution * tiles_resolution
    max_simultaneous_frames = int(max_supported_pixels // input_pixels)
    return max(1, min(max_simultaneous_frames, multithreading))


def _split_into_chunks(items: list, chunk_count: int) -> list[list]:
    chunk_count = max(1, min(chunk_count, len(items)))
    base_size, remainder = divmod(len(items), chunk_count)
    chunks = []
    start = 0
    for index in range(chunk_count):
        size = base_size + (1 if index < remainder else 0)
        chunks.append(items[start:start + size])
        start += size
    return chunks


def _can_resume_video(target_directory: str, ai_model: str) -> bool:
    if not os.path.exists(target_directory):
        return False
    upscaled_frames = [f for f in os.listdir(target_directory) if ai_model in f]
    return len(upscaled_frames) > 1


def _frames_for_resume(target_directory: str, ai_model: str) -> list[str]:
    from natsort import natsorted

    directory_files = os.listdir(target_directory)
    original_frames = [f for f in directory_files if f.endswith(".jpg") and ai_model not in f]
    return natsorted([os.path.join(target_directory, f) for f in original_frames])


def upscale_image_file(
    settings: UpscaleSettings,
    image_path: str,
    file_index: int,
    file_count: int,
    emit: Callable[[UpscaleEvent], None],
    upscaler,
) -> str:
    from . import media

    emit(UpscaleProgress(message=f"{file_index}. Upscaling image", file_index=file_index, file_count=file_count, phase="image"))

    starting_image = media.image_read(image_path)
    upscaled_image_path = prepare_output_image_filename(image_path, settings)

    upscaled_image = upscaler.AI_orchestration(starting_image)
    upscaled_image = media.resize_with_output_factor(upscaled_image, settings.output_resize_factor)

    if settings.blending_factor > 0:
        media.blend_images_and_save(
            target_path=upscaled_image_path,
            starting_image=starting_image,
            upscaled_image=upscaled_image,
            starting_image_importance=settings.blending_factor,
            file_extension=settings.image_extension,
        )
    else:
        media.image_write(upscaled_image_path, upscaled_image, settings.image_extension)

    media.copy_file_metadata(image_path, upscaled_image_path)
    return upscaled_image_path


def upscale_video_file(
    settings: UpscaleSettings,
    video_path: str,
    file_index: int,
    file_count: int,
    emit: Callable[[UpscaleEvent], None],
    cancel: threading.Event,
) -> str | None:
    from . import media
    from .ai import AIUpscaler

    target_directory = prepare_output_video_directory_name(video_path, settings)
    video_output_path = prepare_output_video_filename(video_path, settings)
    video_fps = media.get_video_fps(video_path)

    if _can_resume_video(target_directory, settings.ai_model):
        emit(UpscaleProgress(message=f"{file_index}. Resume video upscaling", file_index=file_index, file_count=file_count, phase="video_extract"))
        extracted_frames_paths = _frames_for_resume(target_directory, settings.ai_model)
    else:
        emit(UpscaleProgress(message=f"{file_index}. Extracting video frames", file_index=file_index, file_count=file_count, phase="video_extract"))
        extracted_frames_paths = media.extract_video_frames(
            video_path=video_path,
            target_directory=target_directory,
            cancel=cancel,
            on_progress=lambda fraction: emit(
                UpscaleProgress(
                    message=f"{file_index}. Extracting video frames {int(fraction * 100)}%",
                    file_index=file_index,
                    file_count=file_count,
                    fraction=fraction,
                    phase="video_extract",
                )
            ),
        )

    if cancel.is_set():
        return None
    if not extracted_frames_paths:
        raise RuntimeError(f"No frames extracted from {video_path}")

    first_frame = media.image_read(extracted_frames_paths[0])
    original_height, original_width = first_frame.shape[0], first_frame.shape[1]
    input_height, input_width = _calculate_input_resolution(original_height, original_width, settings.input_resize_factor)
    target_height, target_width = _calculate_output_resolution(input_height, input_width, _upscale_factor(settings.ai_model), settings.output_resize_factor)

    upscaled_frame_paths = [prepare_upscaled_frame_filename(f, settings) for f in extracted_frames_paths]
    frames_to_upscale = [(i, o) for i, o in zip(extracted_frames_paths, upscaled_frame_paths) if not os.path.exists(o)]

    total_frames = len(extracted_frames_paths)
    completed_counter = total_frames - len(frames_to_upscale)
    counter_lock = threading.Lock()

    threads_number = _calculate_optimal_threads_number(settings.tiles_resolution, input_height * input_width, settings.multithreading)

    emit(
        UpscaleProgress(
            message=f"{file_index}. Upscaling video ({threads_number} threads)",
            file_index=file_index,
            file_count=file_count,
            fraction=completed_counter / total_frames,
            phase="video_upscale",
        )
    )

    def upscale_frame_chunk(frame_chunk: list[tuple[str, str]]) -> None:
        nonlocal completed_counter
        upscaler = AIUpscaler(settings.ai_model, settings.gpu, settings.input_resize_factor, settings.tiles_resolution)

        for input_path, output_path in frame_chunk:
            if cancel.is_set():
                return

            starting_frame = media.image_read(input_path)
            upscaled_frame = upscaler.AI_orchestration(starting_frame)

            if settings.blending_factor > 0:
                media.blend_images_and_save(output_path, starting_frame, upscaled_frame, settings.blending_factor)
            else:
                media.image_write(output_path, upscaled_frame)

            with counter_lock:
                completed_counter += 1
                current_count = completed_counter

            if current_count % 10 == 0 or current_count == total_frames:
                fraction = current_count / total_frames
                emit(
                    UpscaleProgress(
                        message=f"{file_index}. Upscaling video {int(fraction * 100)}%",
                        file_index=file_index,
                        file_count=file_count,
                        fraction=fraction,
                        phase="video_upscale",
                    )
                )

    if frames_to_upscale:
        frame_chunks = _split_into_chunks(frames_to_upscale, threads_number)
        with ThreadPoolExecutor(max_workers=len(frame_chunks)) as executor:
            futures = [executor.submit(upscale_frame_chunk, chunk) for chunk in frame_chunks]
            for future in futures:
                future.result()

    if cancel.is_set():
        return None

    emit(UpscaleProgress(message=f"{file_index}. Encoding upscaled video", file_index=file_index, file_count=file_count, phase="video_encode"))
    media.encode_video(
        video_path=video_path,
        video_output_path=video_output_path,
        upscaled_frame_paths=upscaled_frame_paths,
        video_fps=video_fps,
        video_codec=settings.video_codec,
        video_quality=settings.video_quality,
        target_width=target_width,
        target_height=target_height,
    )
    media.copy_file_metadata(video_path, video_output_path)

    if not settings.keep_frames and os.path.exists(target_directory):
        shutil.rmtree(target_directory)

    return video_output_path


def run_pipeline(
    settings: UpscaleSettings,
    emit: Callable[[UpscaleEvent], None],
    cancel: threading.Event,
) -> list[str]:
    settings.validate()
    if not settings.input_paths:
        raise ValueError("No input files provided")

    output_paths: list[str] = []
    upscaler_for_images = None
    file_count = len(settings.input_paths)

    for file_index, file_path in enumerate(settings.input_paths, start=1):
        if cancel.is_set():
            return output_paths

        if check_if_file_is_video(file_path):
            output_path = upscale_video_file(settings, file_path, file_index, file_count, emit, cancel)
        else:
            if upscaler_for_images is None:
                from .ai import AIUpscaler

                emit(UpscaleProgress(message="Loading AI model", file_index=file_index, file_count=file_count, phase="model"))
                upscaler_for_images = AIUpscaler(settings.ai_model, settings.gpu, settings.input_resize_factor, settings.tiles_resolution)
            output_path = upscale_image_file(settings, file_path, file_index, file_count, emit, upscaler_for_images)

        if output_path is not None:
            output_paths.append(output_path)

    return output_paths
