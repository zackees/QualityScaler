from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpscaleEvent:
    pass


@dataclass(frozen=True)
class UpscaleProgress(UpscaleEvent):
    message: str
    file_index: int = 0
    file_count: int = 0
    fraction: float | None = None
    phase: str = ""


@dataclass(frozen=True)
class UpscaleCompleted(UpscaleEvent):
    output_paths: tuple[str, ...] = ()


@dataclass(frozen=True)
class UpscaleError(UpscaleEvent):
    message: str = ""


@dataclass(frozen=True)
class UpscaleStopped(UpscaleEvent):
    pass
