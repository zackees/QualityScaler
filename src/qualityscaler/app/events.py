"""Transport-neutral JSON wire schema for pipeline events and console logs.

Both the upscale pipeline (:mod:`qualityscaler.core.job`) and the frame
generation pipeline (:class:`qualityscaler.app.controllers.framegen.FrameGenController`)
emit the same :mod:`qualityscaler.core.events` dataclasses; the ``kind``
argument ("upscale" or "framegen") tags which pipeline a frame came from.

This module is pure Python (no toolkit, no asyncio) and is consumed by the
future webview/WebSocket bridge. The CTk GUI does not use it.
"""

from __future__ import annotations

import json
from typing import Any

from qualityscaler.core.events import (
    UpscaleCompleted,
    UpscaleError,
    UpscaleProgress,
    UpscaleStopped,
)

KIND_UPSCALE = "upscale"
KIND_FRAMEGEN = "framegen"


def event_to_wire(event: object, kind: str) -> dict[str, Any]:
    """Map a pipeline event dataclass to a JSON-safe wire dict.

    Raises :class:`ValueError` for objects that are not known event types.
    """
    if isinstance(event, UpscaleProgress):
        return {
            "type": "progress",
            "kind": kind,
            "message": str(event.message),
            "file_index": int(event.file_index) if event.file_index is not None else None,
            "fraction": float(event.fraction) if event.fraction is not None else None,
        }
    if isinstance(event, UpscaleCompleted):
        return {
            "type": "completed",
            "kind": kind,
            "output_paths": [str(path) for path in event.output_paths],
        }
    if isinstance(event, UpscaleError):
        return {
            "type": "error",
            "kind": kind,
            "message": str(event.message),
        }
    if isinstance(event, UpscaleStopped):
        return {
            "type": "stopped",
            "kind": kind,
        }
    raise ValueError(f"unknown event type: {type(event).__name__}")


def log_to_wire(text: str, stream: str) -> dict[str, Any]:
    """Wire frame for a console log line."""
    return {"type": "log", "stream": str(stream), "text": str(text)}


def info_to_wire(text: str) -> dict[str, Any]:
    """Wire frame for engine/info-bar text."""
    return {"type": "engine_info", "text": str(text)}


def to_json(frame: dict[str, Any]) -> str:
    """Serialize a wire frame to a compact JSON string."""
    return json.dumps(frame, ensure_ascii=False, separators=(",", ":"))
