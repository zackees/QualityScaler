from __future__ import annotations

import pytest

from qualityscaler.core.encoding import VIDEO_QUALITY_ARGS, video_quality_args
from qualityscaler.core.settings import VIDEO_QUALITIES

ALL_ENCODERS = [
    "libx264",
    "libx265",
    "h264_nvenc",
    "hevc_nvenc",
    "h264_amf",
    "hevc_amf",
    "h264_qsv",
    "hevc_qsv",
]


def test_quality_args_cover_all_encoders_and_tiers() -> None:
    assert set(VIDEO_QUALITY_ARGS) == set(ALL_ENCODERS)
    for encoder in ALL_ENCODERS:
        assert set(VIDEO_QUALITY_ARGS[encoder]) == set(VIDEO_QUALITIES)


def test_high_x264_maps_to_crf_18() -> None:
    assert video_quality_args("x264", "HIGH") == ["-crf", "18"]
    assert video_quality_args("libx264", "HIGH") == ["-crf", "18"]


def test_gui_codec_names_alias_to_lib_encoders() -> None:
    assert video_quality_args("x265", "MEDIUM") == video_quality_args("libx265", "MEDIUM")


@pytest.mark.parametrize("encoder", ["h264_nvenc", "hevc_nvenc"])
@pytest.mark.parametrize("tier", ["LOW", "MEDIUM", "HIGH"])
def test_nvenc_args_include_zero_bitrate(encoder: str, tier: str) -> None:
    args = video_quality_args(encoder, tier)
    assert args[args.index("-b:v") + 1] == "0"
    assert "-cq" in args


@pytest.mark.parametrize("encoder", ["h264_amf", "hevc_amf"])
def test_amf_uses_constant_qp(encoder: str) -> None:
    args = video_quality_args(encoder, "HIGH")
    assert args[:2] == ["-rc", "cqp"]
    assert "-qp_i" in args and "-qp_p" in args


@pytest.mark.parametrize("encoder", ["h264_qsv", "hevc_qsv"])
def test_qsv_uses_global_quality(encoder: str) -> None:
    assert video_quality_args(encoder, "LOW")[0] == "-global_quality"


@pytest.mark.parametrize("encoder", ALL_ENCODERS)
def test_lower_tiers_use_higher_quantizer_values(encoder: str) -> None:
    def quantizer(args: list[str]) -> int:
        numbers = [int(a) for a in args if a.lstrip("-").isdigit() and a != "0"]
        return max(numbers)

    low = quantizer(video_quality_args(encoder, "LOW"))
    medium = quantizer(video_quality_args(encoder, "MEDIUM"))
    high = quantizer(video_quality_args(encoder, "HIGH"))
    assert low > medium > high


def test_unknown_codec_raises_key_error() -> None:
    with pytest.raises(KeyError):
        video_quality_args("av1_magic", "HIGH")
