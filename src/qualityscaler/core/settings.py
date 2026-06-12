from __future__ import annotations

from dataclasses import dataclass, field

AI_MODELS: list[str] = [
    "LVAx2",
    "RealESR_Gx4",
    "RealESR_Ax4",
    "BSRGANx2",
    "BSRGANx4",
    "RealESRGANx4",
    "MSharpx4",
    "IRCNN_Mx1",
    "IRCNN_Lx1",
]

VRAM_MODEL_USAGE: dict[str, float] = {
    "LVAx2": 2,
    "RealESR_Gx4": 2.5,
    "RealESR_Ax4": 2.5,
    "BSRGANx2": 0.8,
    "BSRGANx4": 0.75,
    "RealESRGANx4": 0.75,
    "MSharpx4": 1.5,
    "IRCNN_Mx1": 4,
    "IRCNN_Lx1": 4,
}

BLENDING_FACTORS: dict[str, float] = {
    "OFF": 0,
    "Low": 0.3,
    "Medium": 0.5,
    "High": 0.7,
}


def tiles_resolution_for(model: str, vram_gb: float) -> int:
    return int(VRAM_MODEL_USAGE[model] * vram_gb * 100)


@dataclass
class UpscaleSettings:
    input_paths: list[str] = field(default_factory=list)
    output_path: str | None = None
    ai_model: str = "RealESR_Gx4"
    gpu: str = "Auto"
    vram_gb: float = 4.0
    multithreading: int = 1
    input_resize_factor: float = 1.0
    output_resize_factor: float = 1.0
    blending: str = "OFF"
    keep_frames: bool = False
    image_extension: str = ".png"
    video_extension: str = ".mp4"
    video_codec: str = "x264"

    @property
    def tiles_resolution(self) -> int:
        return tiles_resolution_for(self.ai_model, self.vram_gb)

    @property
    def blending_factor(self) -> float:
        return BLENDING_FACTORS[self.blending]

    def validate(self) -> None:
        if self.ai_model not in AI_MODELS:
            raise ValueError(f"Unknown AI model: {self.ai_model!r} (expected one of {AI_MODELS})")
        if self.blending not in BLENDING_FACTORS:
            raise ValueError(f"Unknown blending level: {self.blending!r} (expected one of {list(BLENDING_FACTORS)})")
        if self.input_resize_factor <= 0:
            raise ValueError(f"input_resize_factor must be > 0, got {self.input_resize_factor}")
        if self.output_resize_factor <= 0:
            raise ValueError(f"output_resize_factor must be > 0, got {self.output_resize_factor}")
        if self.vram_gb <= 0:
            raise ValueError(f"vram_gb must be > 0, got {self.vram_gb}")
        if self.multithreading < 1:
            raise ValueError(f"multithreading must be >= 1, got {self.multithreading}")
