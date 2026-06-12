from __future__ import annotations

from pathlib import Path

from qualityscaler.gui.ff_preferences import load_ff_preferences, save_ff_preferences
from qualityscaler.gui.ff_state import FFUIState


def test_load_missing_file_returns_defaults(tmp_path: Path) -> None:
    state = load_ff_preferences(str(tmp_path / "missing.json"))
    assert state == FFUIState()


def test_round_trip(tmp_path: Path) -> None:
    preference_path = str(tmp_path / "ff_prefs.json")
    state = FFUIState(
        ai_model            = "RIFE_Lite",
        generation_option   = "Slowmotion x8",
        gpu                 = "GPU 2",
        keep_frames         = "OFF",
        image_extension     = ".png",
        video_output        = ".avi",
        output_path         = "C:/output",
        input_resize_factor = "80",
        cpu_number          = "8",
    )

    save_ff_preferences(state, preference_path)
    loaded = load_ff_preferences(preference_path)

    assert loaded == state


def test_load_partial_file_fills_defaults(tmp_path: Path) -> None:
    preference_path = tmp_path / "ff_prefs.json"
    preference_path.write_text('{"default_AI_model": "RIFE_Lite"}', encoding="utf-8")

    loaded = load_ff_preferences(str(preference_path))
    defaults = FFUIState()

    assert loaded.ai_model == "RIFE_Lite"
    assert loaded.generation_option == defaults.generation_option
    assert loaded.cpu_number == defaults.cpu_number
