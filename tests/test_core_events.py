from __future__ import annotations

import dataclasses

import pytest

from qualityscaler.core import UpscaleCompleted, UpscaleError, UpscaleEvent, UpscaleProgress, UpscaleStopped


def test_all_events_subclass_upscale_event() -> None:
    for event_type in (UpscaleProgress, UpscaleCompleted, UpscaleError, UpscaleStopped):
        assert issubclass(event_type, UpscaleEvent)


def test_progress_defaults() -> None:
    event = UpscaleProgress(message="working")
    assert event.message == "working"
    assert event.file_index == 0
    assert event.file_count == 0
    assert event.fraction is None
    assert event.phase == ""


def test_progress_full_fields() -> None:
    event = UpscaleProgress(message="upscaling", file_index=2, file_count=3, fraction=0.5, phase="video_upscale")
    assert event.file_index == 2
    assert event.file_count == 3
    assert event.fraction == 0.5
    assert event.phase == "video_upscale"


def test_completed_defaults_and_paths() -> None:
    assert UpscaleCompleted().output_paths == ()
    assert UpscaleCompleted(("a.png", "b.mp4")).output_paths == ("a.png", "b.mp4")


def test_error_default_message() -> None:
    assert UpscaleError().message == ""
    assert UpscaleError("boom").message == "boom"


def test_events_are_frozen() -> None:
    event = UpscaleProgress(message="working")
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.message = "changed"


def test_events_are_value_comparable() -> None:
    assert UpscaleStopped() == UpscaleStopped()
    assert UpscaleCompleted(("x",)) == UpscaleCompleted(("x",))
    assert UpscaleProgress(message="a") != UpscaleProgress(message="b")
