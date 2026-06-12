from __future__ import annotations

# LOW/MEDIUM/HIGH per encoder, anchored at HIGH = libx264 crf 18 (see issue #42).
# NVENC needs -b:v 0 or -cq is ignored; AMF has no CRF analogue so constant QP
# plus the "quality" preset is the closest; QSV uses ICQ via -global_quality.
VIDEO_QUALITY_ARGS: dict[str, dict[str, list[str]]] = {
    "libx264": {
        "LOW": ["-crf", "28"],
        "MEDIUM": ["-crf", "23"],
        "HIGH": ["-crf", "18"],
    },
    "libx265": {
        "LOW": ["-crf", "30"],
        "MEDIUM": ["-crf", "25"],
        "HIGH": ["-crf", "20"],
    },
    "h264_nvenc": {
        "LOW": ["-rc", "vbr", "-cq", "29", "-b:v", "0"],
        "MEDIUM": ["-rc", "vbr", "-cq", "24", "-b:v", "0"],
        "HIGH": ["-rc", "vbr", "-cq", "19", "-b:v", "0"],
    },
    "hevc_nvenc": {
        "LOW": ["-rc", "vbr", "-cq", "31", "-b:v", "0"],
        "MEDIUM": ["-rc", "vbr", "-cq", "26", "-b:v", "0"],
        "HIGH": ["-rc", "vbr", "-cq", "21", "-b:v", "0"],
    },
    "h264_amf": {
        "LOW": ["-rc", "cqp", "-qp_i", "28", "-qp_p", "28", "-quality", "quality"],
        "MEDIUM": ["-rc", "cqp", "-qp_i", "23", "-qp_p", "23", "-quality", "quality"],
        "HIGH": ["-rc", "cqp", "-qp_i", "18", "-qp_p", "18", "-quality", "quality"],
    },
    "hevc_amf": {
        "LOW": ["-rc", "cqp", "-qp_i", "28", "-qp_p", "28", "-quality", "quality"],
        "MEDIUM": ["-rc", "cqp", "-qp_i", "23", "-qp_p", "23", "-quality", "quality"],
        "HIGH": ["-rc", "cqp", "-qp_i", "18", "-qp_p", "18", "-quality", "quality"],
    },
    "h264_qsv": {
        "LOW": ["-global_quality", "30"],
        "MEDIUM": ["-global_quality", "25"],
        "HIGH": ["-global_quality", "20"],
    },
    "hevc_qsv": {
        "LOW": ["-global_quality", "32"],
        "MEDIUM": ["-global_quality", "27"],
        "HIGH": ["-global_quality", "22"],
    },
}


def video_quality_args(codec: str, video_quality: str) -> list[str]:
    effective_codec = {"x264": "libx264", "x265": "libx265"}.get(codec, codec)
    return VIDEO_QUALITY_ARGS[effective_codec][video_quality]
