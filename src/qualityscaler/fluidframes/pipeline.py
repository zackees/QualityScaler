from __future__ import annotations

import os
import shutil
import threading
from typing import Callable

from qualityscaler.core.events import UpscaleEvent, UpscaleProgress
from qualityscaler.core.pipeline import _output_base, check_if_file_is_video

from .settings import FrameGenSettings


def _filename_suffix(settings: FrameGenSettings) -> str:
    if settings.slowmotion:
        suffix = f"_{settings.ai_model}_Slowmo-x{settings.frame_gen_factor}"
    else:
        suffix = f"_{settings.ai_model}_x{settings.frame_gen_factor}"
    suffix += f"_InputR-{int(settings.input_resize_factor * 100)}"
    return suffix


def prepare_output_video_filename(video_path: str, settings: FrameGenSettings) -> str:
    return _output_base(video_path, settings.output_path) + _filename_suffix(settings) + settings.video_extension


def prepare_output_video_directory_name(video_path: str, settings: FrameGenSettings) -> str:
    return _output_base(video_path, settings.output_path) + _filename_suffix(settings)


def prepare_generated_frame_paths(frame_path: str, frame_gen_factor: int) -> list[str]:
    base_path, extension = os.path.splitext(frame_path)
    return [f"{base_path}_gen{index}{extension}" for index in range(1, frame_gen_factor)]


def build_total_frame_sequence(frame_paths: list[str], frame_gen_factor: int) -> list[str]:
    if not frame_paths:
        return []

    total_frames_paths: list[str] = []
    for frame_path in frame_paths[:-1]:
        total_frames_paths.append(frame_path)
        total_frames_paths.extend(prepare_generated_frame_paths(frame_path, frame_gen_factor))
    total_frames_paths.append(frame_paths[-1])
    return total_frames_paths


def _generate_frames_for_video_file(
    settings: FrameGenSettings,
    video_path: str,
    file_index: int,
    file_count: int,
    emit: Callable[[UpscaleEvent], None],
    cancel: threading.Event,
) -> str | None:
    from qualityscaler.core import media

    from .ai import AIFrameGenerator

    target_directory = prepare_output_video_directory_name(video_path, settings)
    video_output_path = prepare_output_video_filename(video_path, settings)
    video_fps = media.get_video_fps(video_path)

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

    interpolator = AIFrameGenerator(settings.ai_model, settings.gpu, settings.frame_gen_factor)

    emit(UpscaleProgress(message=f"{file_index}. Resizing video frames", file_index=file_index, file_count=file_count, phase="video_resize"))
    target_height = target_width = 0
    for frame_path in extracted_frames_paths:
        if cancel.is_set():
            return None
        frame = media.image_read(frame_path)
        resized_frame = interpolator.resize_image(frame, settings.input_resize_factor)
        if resized_frame is not frame:
            media.image_write(frame_path, resized_frame, settings.image_extension)
        target_height, target_width = resized_frame.shape[0], resized_frame.shape[1]

    total_pairs = len(extracted_frames_paths) - 1
    emit(UpscaleProgress(message=f"{file_index}. Generating video frames", file_index=file_index, file_count=file_count, fraction=0.0, phase="video_frame_generation"))

    for pair_index in range(total_pairs):
        if cancel.is_set():
            return None

        frame_1_path = extracted_frames_paths[pair_index]
        frame_2_path = extracted_frames_paths[pair_index + 1]
        generated_frame_paths = prepare_generated_frame_paths(frame_1_path, settings.frame_gen_factor)

        frame_1 = media.image_read(frame_1_path)
        frame_2 = media.image_read(frame_2_path)
        generated_frames = interpolator.AI_orchestration(frame_1, frame_2)

        for generated_frame_path, generated_frame in zip(generated_frame_paths, generated_frames):
            media.image_write(generated_frame_path, generated_frame, settings.image_extension)

        completed = pair_index + 1
        if completed % 10 == 0 or completed == total_pairs:
            fraction = completed / total_pairs
            emit(
                UpscaleProgress(
                    message=f"{file_index}. Generating video frames {int(fraction * 100)}%",
                    file_index=file_index,
                    file_count=file_count,
                    fraction=fraction,
                    phase="video_frame_generation",
                )
            )

    if cancel.is_set():
        return None

    total_frames_paths = build_total_frame_sequence(extracted_frames_paths, settings.frame_gen_factor)
    output_fps = video_fps if settings.slowmotion else video_fps * settings.frame_gen_factor

    emit(UpscaleProgress(message=f"{file_index}. Encoding frame-generated video", file_index=file_index, file_count=file_count, phase="video_encode"))
    media.encode_video(
        video_path=video_path,
        video_output_path=video_output_path,
        upscaled_frame_paths=total_frames_paths,
        video_fps=output_fps,
        video_codec=settings.video_codec,
        video_quality=settings.video_quality,
        target_width=target_width,
        target_height=target_height,
        include_audio=not settings.slowmotion,
    )
    media.copy_file_metadata(video_path, video_output_path)

    if not settings.keep_frames and os.path.exists(target_directory):
        shutil.rmtree(target_directory)

    return video_output_path


def run_frame_generation_pipeline(
    settings: FrameGenSettings,
    emit: Callable[[UpscaleEvent], None],
    cancel: threading.Event,
) -> list[str]:
    settings.validate()
    if not settings.input_paths:
        raise ValueError("No input files provided")
    for file_path in settings.input_paths:
        if not check_if_file_is_video(file_path):
            raise ValueError(f"Frame generation only supports video files, got: {file_path}")

    output_paths: list[str] = []
    file_count = len(settings.input_paths)

    for file_index, file_path in enumerate(settings.input_paths, start=1):
        if cancel.is_set():
            return output_paths

        output_path = _generate_frames_for_video_file(settings, file_path, file_index, file_count, emit, cancel)
        if output_path is not None:
            output_paths.append(output_path)

    return output_paths
