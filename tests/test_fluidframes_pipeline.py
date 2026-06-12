from __future__ import annotations

import os

import pytest

from qualityscaler.fluidframes.pipeline import (
    build_total_frame_sequence,
    prepare_generated_frame_paths,
    prepare_output_video_directory_name,
    prepare_output_video_filename,
)
from qualityscaler.fluidframes.settings import FrameGenSettings


def test_output_video_filename_default_x2() -> None:
    settings = FrameGenSettings(input_paths=["video.mp4"])
    result = prepare_output_video_filename(os.path.join("some", "dir", "video.mp4"), settings)
    assert result == os.path.join("some", "dir", "video") + "_RIFE_x2_InputR-50.mp4"


def test_output_video_filename_slowmotion() -> None:
    settings = FrameGenSettings(input_paths=["video.mp4"], slowmotion=True, frame_gen_factor=4, input_resize_factor=1.0)
    result = prepare_output_video_filename(os.path.join("some", "dir", "video.mp4"), settings)
    assert result == os.path.join("some", "dir", "video") + "_RIFE_Slowmo-x4_InputR-100.mp4"


def test_output_video_filename_with_output_dir() -> None:
    settings = FrameGenSettings(input_paths=["video.mkv"], output_path=os.path.join("out", "dir"), ai_model="RIFE_Lite", frame_gen_factor=8, video_extension=".avi")
    result = prepare_output_video_filename(os.path.join("some", "dir", "video.mkv"), settings)
    assert result == os.path.join("out", "dir", "video") + "_RIFE_Lite_x8_InputR-50.avi"


def test_output_video_directory_name_default() -> None:
    settings = FrameGenSettings(input_paths=["video.mp4"])
    result = prepare_output_video_directory_name(os.path.join("some", "dir", "video.mp4"), settings)
    assert result == os.path.join("some", "dir", "video") + "_RIFE_x2_InputR-50"


def test_output_video_directory_name_with_output_dir() -> None:
    settings = FrameGenSettings(input_paths=["video.mp4"], output_path="elsewhere", slowmotion=True)
    result = prepare_output_video_directory_name(os.path.join("some", "dir", "video.mp4"), settings)
    assert result == os.path.join("elsewhere", "video") + "_RIFE_Slowmo-x2_InputR-50"


def test_prepare_generated_frame_paths_x2() -> None:
    assert prepare_generated_frame_paths("frame_001.jpg", 2) == ["frame_001_gen1.jpg"]


def test_prepare_generated_frame_paths_x4() -> None:
    assert prepare_generated_frame_paths("frame_001.png", 4) == [
        "frame_001_gen1.png",
        "frame_001_gen2.png",
        "frame_001_gen3.png",
    ]


def test_build_total_frame_sequence_empty() -> None:
    assert build_total_frame_sequence([], 2) == []


def test_build_total_frame_sequence_single_frame() -> None:
    assert build_total_frame_sequence(["frame_001.jpg"], 2) == ["frame_001.jpg"]


def test_build_total_frame_sequence_x2() -> None:
    frames = ["frame_001.jpg", "frame_002.jpg", "frame_003.jpg"]
    assert build_total_frame_sequence(frames, 2) == [
        "frame_001.jpg",
        "frame_001_gen1.jpg",
        "frame_002.jpg",
        "frame_002_gen1.jpg",
        "frame_003.jpg",
    ]


def test_build_total_frame_sequence_x4() -> None:
    frames = ["frame_001.jpg", "frame_002.jpg"]
    assert build_total_frame_sequence(frames, 4) == [
        "frame_001.jpg",
        "frame_001_gen1.jpg",
        "frame_001_gen2.jpg",
        "frame_001_gen3.jpg",
        "frame_002.jpg",
    ]


def test_build_total_frame_sequence_x8() -> None:
    frames = ["frame_001.jpg", "frame_002.jpg"]
    result = build_total_frame_sequence(frames, 8)
    assert len(result) == 9
    assert result[0] == "frame_001.jpg"
    assert result[-1] == "frame_002.jpg"
    assert result[1:8] == [f"frame_001_gen{i}.jpg" for i in range(1, 8)]


@pytest.mark.parametrize("factor", [2, 4, 8])
def test_build_total_frame_sequence_length(factor: int) -> None:
    frames = [f"frame_{i:03d}.jpg" for i in range(1, 6)]
    result = build_total_frame_sequence(frames, factor)
    assert len(result) == (len(frames) - 1) * factor + 1


def test_run_frame_generation_pipeline_rejects_non_video() -> None:
    import threading

    from qualityscaler.fluidframes.pipeline import run_frame_generation_pipeline

    settings = FrameGenSettings(input_paths=["picture.png"])
    with pytest.raises(ValueError, match="only supports video"):
        run_frame_generation_pipeline(settings, emit=lambda event: None, cancel=threading.Event())


def test_run_frame_generation_pipeline_rejects_empty_inputs() -> None:
    import threading

    from qualityscaler.fluidframes.pipeline import run_frame_generation_pipeline

    settings = FrameGenSettings()
    with pytest.raises(ValueError, match="No input files"):
        run_frame_generation_pipeline(settings, emit=lambda event: None, cancel=threading.Event())
