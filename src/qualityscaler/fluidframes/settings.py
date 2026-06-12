from __future__ import annotations

from dataclasses import dataclass, field

FF_AI_MODELS: list[str] = ["RIFE", "RIFE_Lite"]

FF_FRAME_GEN_FACTORS: tuple[int, ...] = (2, 4, 8)

FF_VIDEO_QUALITIES: list[str] = ["LOW", "MEDIUM", "HIGH"]


@dataclass
class FrameGenSettings:
    input_paths: list[str] = field(default_factory=list)
    output_path: str | None = None
    ai_model: str = "RIFE"
    gpu: str = "Auto"
    frame_gen_factor: int = 2
    slowmotion: bool = False
    keep_frames: bool = False
    image_extension: str = ".jpg"
    video_extension: str = ".mp4"
    video_codec: str = "x264"
    video_quality: str = "HIGH"
    input_resize_factor: float = 0.5
    cpu_number: int = 4

    def validate(self) -> None:
        if self.ai_model not in FF_AI_MODELS:
            raise ValueError(f"Unknown AI model: {self.ai_model!r} (expected one of {FF_AI_MODELS})")
        if self.frame_gen_factor not in FF_FRAME_GEN_FACTORS:
            raise ValueError(f"frame_gen_factor must be one of {FF_FRAME_GEN_FACTORS}, got {self.frame_gen_factor}")
        if self.video_quality not in FF_VIDEO_QUALITIES:
            raise ValueError(f"Unknown video quality: {self.video_quality!r} (expected one of {FF_VIDEO_QUALITIES})")
        if self.input_resize_factor <= 0:
            raise ValueError(f"input_resize_factor must be > 0, got {self.input_resize_factor}")
        if self.cpu_number < 1:
            raise ValueError(f"cpu_number must be >= 1, got {self.cpu_number}")
