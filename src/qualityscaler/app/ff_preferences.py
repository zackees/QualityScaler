"""Load/save of Fluid Frames user preferences as JSON.

Stored in a separate file from the Quality Scaler preferences so the two
modes stay independent. Toolkit-free.
"""

from __future__ import annotations

from json import dumps as json_dumps, load as json_load
from os import sep as os_separator
from os.path import exists as os_path_exists

from qualityscaler.app.constants import app_name, version
from qualityscaler.app.ff_state import FFUIState
from qualityscaler.app.preferences import DOCUMENT_PATH

FF_USER_PREFERENCE_PATH = f"{DOCUMENT_PATH}{os_separator}{app_name}_{version}_fluidframes_userpreference.json"


def load_ff_preferences(preference_path: str) -> FFUIState:
    if not os_path_exists(preference_path):
        return FFUIState()

    with open(preference_path, "r") as json_file:
        json_data = json_load(json_file)

    defaults = FFUIState()
    return FFUIState(
        ai_model            = json_data.get("default_AI_model",            defaults.ai_model),
        generation_option   = json_data.get("default_generation_option",   defaults.generation_option),
        gpu                 = json_data.get("default_gpu",                 defaults.gpu),
        keep_frames         = json_data.get("default_keep_frames",         defaults.keep_frames),
        image_extension     = json_data.get("default_image_extension",     defaults.image_extension),
        video_output        = json_data.get("default_video_output",        defaults.video_output),
        output_path         = json_data.get("default_output_path",         defaults.output_path),
        input_resize_factor = json_data.get("default_input_resize_factor", defaults.input_resize_factor),
        cpu_number          = json_data.get("default_cpu_number",          defaults.cpu_number),
    )


def save_ff_preferences(state: FFUIState, preference_path: str) -> None:
    user_preference = {
        "default_AI_model":            state.ai_model,
        "default_generation_option":   state.generation_option,
        "default_gpu":                 state.gpu,
        "default_keep_frames":         state.keep_frames,
        "default_image_extension":     state.image_extension,
        "default_video_output":        state.video_output,
        "default_output_path":         state.output_path,
        "default_input_resize_factor": str(state.input_resize_factor),
        "default_cpu_number":          str(state.cpu_number),
    }
    with open(preference_path, "w") as preference_file:
        preference_file.write(json_dumps(user_preference))
