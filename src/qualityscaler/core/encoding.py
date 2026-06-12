from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityTierArgs:
    """ffmpeg quality arguments for one encoder, one field per quality tier."""

    low: tuple[str, ...]
    medium: tuple[str, ...]
    high: tuple[str, ...]

    def for_quality(self, video_quality: str) -> list[str]:
        tiers = {"LOW": self.low, "MEDIUM": self.medium, "HIGH": self.high}
        return list(tiers[video_quality])


# LOW/MEDIUM/HIGH per encoder, anchored at HIGH = libx264 crf 18 (see issue #42).
# NVENC needs -b:v 0 or -cq is ignored; AMF has no CRF analogue so constant QP
# plus the "quality" preset is the closest; QSV uses ICQ via -global_quality.
VIDEO_QUALITY_ARGS: dict[str, QualityTierArgs] = {
    "libx264": QualityTierArgs(
        low=("-crf", "28"),
        medium=("-crf", "23"),
        high=("-crf", "18"),
    ),
    "libx265": QualityTierArgs(
        low=("-crf", "30"),
        medium=("-crf", "25"),
        high=("-crf", "20"),
    ),
    "h264_nvenc": QualityTierArgs(
        low=("-rc", "vbr", "-cq", "29", "-b:v", "0"),
        medium=("-rc", "vbr", "-cq", "24", "-b:v", "0"),
        high=("-rc", "vbr", "-cq", "19", "-b:v", "0"),
    ),
    "hevc_nvenc": QualityTierArgs(
        low=("-rc", "vbr", "-cq", "31", "-b:v", "0"),
        medium=("-rc", "vbr", "-cq", "26", "-b:v", "0"),
        high=("-rc", "vbr", "-cq", "21", "-b:v", "0"),
    ),
    "h264_amf": QualityTierArgs(
        low=("-rc", "cqp", "-qp_i", "28", "-qp_p", "28", "-quality", "quality"),
        medium=("-rc", "cqp", "-qp_i", "23", "-qp_p", "23", "-quality", "quality"),
        high=("-rc", "cqp", "-qp_i", "18", "-qp_p", "18", "-quality", "quality"),
    ),
    "hevc_amf": QualityTierArgs(
        low=("-rc", "cqp", "-qp_i", "28", "-qp_p", "28", "-quality", "quality"),
        medium=("-rc", "cqp", "-qp_i", "23", "-qp_p", "23", "-quality", "quality"),
        high=("-rc", "cqp", "-qp_i", "18", "-qp_p", "18", "-quality", "quality"),
    ),
    "h264_qsv": QualityTierArgs(
        low=("-global_quality", "30"),
        medium=("-global_quality", "25"),
        high=("-global_quality", "20"),
    ),
    "hevc_qsv": QualityTierArgs(
        low=("-global_quality", "32"),
        medium=("-global_quality", "27"),
        high=("-global_quality", "22"),
    ),
}


def video_quality_args(codec: str, video_quality: str) -> list[str]:
    effective_codec = {"x264": "libx264", "x265": "libx265"}.get(codec, codec)
    return VIDEO_QUALITY_ARGS[effective_codec].for_quality(video_quality)
