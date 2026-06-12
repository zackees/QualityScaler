from __future__ import annotations

import json
from pathlib import Path

from qualityscaler.app.preferences import load_preferences, save_preferences
from qualityscaler.app.state import UIState


EXPECTED_JSON_KEYS = {
    "default_app_zoom",
    "default_AI_model",
    "default_AI_multithreading",
    "default_gpu",
    "default_keep_frames",
    "default_image_extension",
    "default_video_extension",
    "default_video_codec",
    "default_video_quality",
    "default_blending",
    "default_output_path",
    "default_input_resize_factor",
    "default_output_resize_factor",
    "default_VRAM_limiter",
}


def test_missing_file_returns_defaults(tmp_path: Path) -> None:
    state = load_preferences(str(tmp_path / "missing.json"))
    assert state == UIState()


def test_save_writes_exact_historical_json_keys(tmp_path: Path) -> None:
    preference_path = tmp_path / "prefs.json"
    save_preferences(UIState(), str(preference_path))

    json_data = json.loads(preference_path.read_text())
    assert set(json_data) == EXPECTED_JSON_KEYS


def test_round_trip_preserves_all_fields(tmp_path: Path) -> None:
    preference_path = tmp_path / "prefs.json"
    state = UIState(
        app_zoom             = "125%",
        ai_model             = "BSRGANx4",
        ai_multithreading    = "4 threads",
        gpu                  = "GPU 2",
        keep_frames          = "OFF",
        image_extension      = ".jpg",
        video_extension      = ".mkv",
        video_codec          = "hevc_nvenc",
        video_quality        = "LOW",
        blending             = "Medium",
        output_path          = "C:/output",
        input_resize_factor  = "75",
        output_resize_factor = "150",
        vram_limiter         = "8",
    )

    save_preferences(state, str(preference_path))
    assert load_preferences(str(preference_path)) == state


def test_partial_file_falls_back_to_defaults_per_key(tmp_path: Path) -> None:
    preference_path = tmp_path / "prefs.json"
    preference_path.write_text(json.dumps({"default_AI_model": "RealESR_Ax4"}))

    state = load_preferences(str(preference_path))
    defaults = UIState()

    assert state.ai_model == "RealESR_Ax4"
    assert state.app_zoom == defaults.app_zoom
    assert state.video_quality == defaults.video_quality
    assert state.vram_limiter == defaults.vram_limiter
