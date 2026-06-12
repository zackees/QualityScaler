from __future__ import annotations

import json
from pathlib import Path

import pytest

from qualityscaler.app.events import event_to_wire, info_to_wire, log_to_wire, to_json
from qualityscaler.core.events import (
    UpscaleCompleted,
    UpscaleError,
    UpscaleProgress,
    UpscaleStopped,
)


class TestEventToWire:
    def test_progress(self) -> None:
        event = UpscaleProgress(message="Upscaling frame 3/10", file_index=2, file_count=5, fraction=0.3)
        assert event_to_wire(event, "upscale") == {
            "type": "progress",
            "kind": "upscale",
            "message": "Upscaling frame 3/10",
            "file_index": 2,
            "fraction": 0.3,
        }

    def test_progress_defaults_map_fraction_none(self) -> None:
        event = UpscaleProgress(message="Resizing")
        assert event_to_wire(event, "framegen") == {
            "type": "progress",
            "kind": "framegen",
            "message": "Resizing",
            "file_index": 0,
            "fraction": None,
        }

    def test_completed(self) -> None:
        event = UpscaleCompleted(output_paths=("a.mp4", "b.png"))
        assert event_to_wire(event, "upscale") == {
            "type": "completed",
            "kind": "upscale",
            "output_paths": ["a.mp4", "b.png"],
        }

    def test_completed_path_objects_become_strings(self) -> None:
        path = Path("out") / "video.mp4"
        event = UpscaleCompleted(output_paths=(path,))  # type: ignore[arg-type]
        wire = event_to_wire(event, "framegen")
        assert wire["output_paths"] == [str(path)]
        assert all(isinstance(item, str) for item in wire["output_paths"])

    def test_error(self) -> None:
        event = UpscaleError(message="GPU not found")
        assert event_to_wire(event, "upscale") == {
            "type": "error",
            "kind": "upscale",
            "message": "GPU not found",
        }

    def test_stopped(self) -> None:
        assert event_to_wire(UpscaleStopped(), "framegen") == {
            "type": "stopped",
            "kind": "framegen",
        }

    def test_unknown_object_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="unknown event type"):
            event_to_wire(object(), "upscale")

    def test_unknown_string_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            event_to_wire("APP_CLOSE", "upscale")


class TestLogAndInfoToWire:
    def test_log_to_wire(self) -> None:
        assert log_to_wire("hello", "stderr") == {"type": "log", "stream": "stderr", "text": "hello"}

    def test_info_to_wire(self) -> None:
        assert info_to_wire("AI engine ready") == {"type": "engine_info", "text": "AI engine ready"}


class TestToJson:
    def test_round_trips_via_json_loads(self) -> None:
        frame = event_to_wire(UpscaleProgress(message="msg", fraction=0.5), "upscale")
        assert json.loads(to_json(frame)) == frame

    def test_compact_output(self) -> None:
        text = to_json({"type": "stopped", "kind": "upscale"})
        assert ": " not in text and ", " not in text

    def test_non_ascii_preserved(self) -> None:
        frame = log_to_wire("héllo ✓", "stdout")
        text = to_json(frame)
        assert "héllo ✓" in text
        assert json.loads(text) == frame
