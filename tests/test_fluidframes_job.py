from __future__ import annotations

import threading

import pytest

import qualityscaler.fluidframes.pipeline as pipeline_module
from qualityscaler.core import UpscaleCompleted, UpscaleError, UpscaleProgress, UpscaleStopped
from qualityscaler.fluidframes import FrameGenJob, FrameGenSettings


def make_settings() -> FrameGenSettings:
    return FrameGenSettings(input_paths=["input.mp4"])


def test_job_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_pipeline(settings, emit, cancel):
        emit(UpscaleProgress(message="1. Generating frames", file_index=1, file_count=1, phase="video"))
        return ["output.mp4"]

    monkeypatch.setattr(pipeline_module, "run_frame_generation_pipeline", fake_run_pipeline)

    job = FrameGenJob(make_settings())
    job.start()
    events = list(job.events())

    assert events[0] == UpscaleProgress(message="1. Generating frames", file_index=1, file_count=1, phase="video")
    assert events[-1] == UpscaleCompleted(("output.mp4",))
    assert job.wait(timeout=5) == UpscaleCompleted(("output.mp4",))
    assert job.done


def test_job_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_pipeline(settings, emit, cancel):
        raise ValueError("boom")

    monkeypatch.setattr(pipeline_module, "run_frame_generation_pipeline", fake_run_pipeline)

    job = FrameGenJob(make_settings())
    job.start()
    events = list(job.events())

    assert events == [UpscaleError("boom")]
    assert job.wait(timeout=5) == UpscaleError("boom")
    assert job.done


def test_job_cancel(monkeypatch: pytest.MonkeyPatch) -> None:
    started = threading.Event()

    def fake_run_pipeline(settings, emit, cancel):
        started.set()
        assert cancel.wait(timeout=5)
        return []

    monkeypatch.setattr(pipeline_module, "run_frame_generation_pipeline", fake_run_pipeline)

    job = FrameGenJob(make_settings())
    job.start()
    assert started.wait(timeout=5)
    job.cancel()
    events = list(job.events())

    assert events == [UpscaleStopped()]
    assert job.wait(timeout=5) == UpscaleStopped()
    assert job.done


def test_job_exception_after_cancel_reports_stopped(monkeypatch: pytest.MonkeyPatch) -> None:
    started = threading.Event()

    def fake_run_pipeline(settings, emit, cancel):
        started.set()
        assert cancel.wait(timeout=5)
        raise RuntimeError("interrupted mid-flight")

    monkeypatch.setattr(pipeline_module, "run_frame_generation_pipeline", fake_run_pipeline)

    job = FrameGenJob(make_settings())
    job.start()
    assert started.wait(timeout=5)
    job.cancel()
    events = list(job.events())

    assert events == [UpscaleStopped()]
    assert job.wait(timeout=5) == UpscaleStopped()


def test_job_start_twice_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline_module, "run_frame_generation_pipeline", lambda settings, emit, cancel: [])

    job = FrameGenJob(make_settings())
    job.start()
    with pytest.raises(RuntimeError):
        job.start()
    job.wait(timeout=5)


def test_job_wait_before_start_returns_none() -> None:
    job = FrameGenJob(make_settings())
    assert job.wait(timeout=0) is None
    assert not job.done
