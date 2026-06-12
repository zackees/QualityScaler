from __future__ import annotations

import threading

import pytest

import qualityscaler.core.pipeline as pipeline_module
from qualityscaler.core import UpscaleCompleted, UpscaleError, UpscaleJob, UpscaleProgress, UpscaleSettings, UpscaleStopped


def make_settings() -> UpscaleSettings:
    return UpscaleSettings(input_paths=["input.png"])


def test_job_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_pipeline(settings, emit, cancel):
        emit(UpscaleProgress(message="1. Upscaling image", file_index=1, file_count=1, phase="image"))
        return ["output.png"]

    monkeypatch.setattr(pipeline_module, "run_pipeline", fake_run_pipeline)

    job = UpscaleJob(make_settings())
    job.start()
    events = list(job.events())

    assert events[0] == UpscaleProgress(message="1. Upscaling image", file_index=1, file_count=1, phase="image")
    assert events[-1] == UpscaleCompleted(("output.png",))
    assert job.wait(timeout=5) == UpscaleCompleted(("output.png",))
    assert job.done


def test_job_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_pipeline(settings, emit, cancel):
        raise ValueError("boom")

    monkeypatch.setattr(pipeline_module, "run_pipeline", fake_run_pipeline)

    job = UpscaleJob(make_settings())
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

    monkeypatch.setattr(pipeline_module, "run_pipeline", fake_run_pipeline)

    job = UpscaleJob(make_settings())
    job.start()
    assert started.wait(timeout=5)
    job.cancel()
    events = list(job.events())

    assert events == [UpscaleStopped()]
    assert job.wait(timeout=5) == UpscaleStopped()
    assert job.done


def test_job_start_twice_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline_module, "run_pipeline", lambda settings, emit, cancel: [])

    job = UpscaleJob(make_settings())
    job.start()
    with pytest.raises(RuntimeError):
        job.start()
    job.wait(timeout=5)


def test_job_wait_before_start_returns_none() -> None:
    job = UpscaleJob(make_settings())
    assert job.wait(timeout=0) is None
    assert not job.done
