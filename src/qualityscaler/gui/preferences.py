"""Load/save of user preferences as JSON.

JSON key names and fallback values must stay identical to the historical
inline implementation so existing preference files keep working.
Toolkit-free so it can be unit tested headlessly.
"""

from __future__ import annotations

from json import dumps as json_dumps, load as json_load
from os.path import exists as os_path_exists

from qualityscaler.gui.state import UIState


def load_preferences(preference_path: str) -> UIState:
    if not os_path_exists(preference_path):
        return UIState()

    with open(preference_path, "r") as json_file:
        json_data = json_load(json_file)

    defaults = UIState()
    return UIState(
        app_zoom             = json_data.get("default_app_zoom",             defaults.app_zoom),
        ai_model             = json_data.get("default_AI_model",             defaults.ai_model),
        ai_multithreading    = json_data.get("default_AI_multithreading",    defaults.ai_multithreading),
        gpu                  = json_data.get("default_gpu",                  defaults.gpu),
        keep_frames          = json_data.get("default_keep_frames",          defaults.keep_frames),
        image_extension      = json_data.get("default_image_extension",      defaults.image_extension),
        video_extension      = json_data.get("default_video_extension",      defaults.video_extension),
        video_codec          = json_data.get("default_video_codec",          defaults.video_codec),
        video_quality        = json_data.get("default_video_quality",        defaults.video_quality),
        blending             = json_data.get("default_blending",             defaults.blending),
        output_path          = json_data.get("default_output_path",          defaults.output_path),
        input_resize_factor  = json_data.get("default_input_resize_factor",  defaults.input_resize_factor),
        output_resize_factor = json_data.get("default_output_resize_factor", defaults.output_resize_factor),
        vram_limiter         = json_data.get("default_VRAM_limiter",         defaults.vram_limiter),
    )


def save_preferences(state: UIState, preference_path: str) -> None:
    user_preference = {
        "default_app_zoom":             state.app_zoom,
        "default_AI_model":             state.ai_model,
        "default_AI_multithreading":    state.ai_multithreading,
        "default_gpu":                  state.gpu,
        "default_keep_frames":          state.keep_frames,
        "default_image_extension":      state.image_extension,
        "default_video_extension":      state.video_extension,
        "default_video_codec":          state.video_codec,
        "default_video_quality":        state.video_quality,
        "default_blending":             state.blending,
        "default_output_path":          state.output_path,
        "default_input_resize_factor":  str(state.input_resize_factor),
        "default_output_resize_factor": str(state.output_resize_factor),
        "default_VRAM_limiter":         str(state.vram_limiter),
    }
    user_preference_json = json_dumps(user_preference)
    with open(preference_path, "w") as preference_file:
        preference_file.write(user_preference_json)
