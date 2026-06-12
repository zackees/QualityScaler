"""RPC bridge exposed to the TypeScript frontend via pywebview's ``js_api``.

Every public method of :class:`PyApi` is callable from JS as
``window.pywebview.api.<method>(...)``. The class is toolkit-free and only
imports pywebview lazily inside the native-dialog methods, so it can be
instantiated and unit tested without pywebview installed.

High-frequency events (logs, progress) do NOT go through this class; they
stream over the loopback WebSocket (see :mod:`qualityscaler.webview.ws`).
"""

from __future__ import annotations

import sys
import webbrowser
from dataclasses import asdict, fields
from os.path import basename as os_path_basename
from typing import Any, Optional
from urllib.parse import urlparse

from qualityscaler.app import constants as app_constants
from qualityscaler.app import ff_constants, ff_info_texts, info_texts
from qualityscaler.app.controllers.framegen import (
    build_settings as ff_build_settings,
    validate as ff_validate,
)
from qualityscaler.app.controllers.upscale import (
    build_settings as upscale_build_settings,
    validate as upscale_validate,
)
from qualityscaler.app.events import KIND_FRAMEGEN, KIND_UPSCALE, event_to_wire
from qualityscaler.app.ff_preferences import (
    FF_USER_PREFERENCE_PATH,
    load_ff_preferences,
    save_ff_preferences,
)
from qualityscaler.app.ff_state import FFUIState
from qualityscaler.app.file_chooser import get_initial_dir, update_last_used_dir
from qualityscaler.app.media_info import (
    check_if_file_is_video,
    format_resolution_projection,
    get_image_resolution,
    image_read,
)
from qualityscaler.app.preferences import (
    USER_PREFERENCE_PATH,
    load_preferences,
    save_preferences,
)
from qualityscaler.app.state import UIState, upscale_factor_for_model

_THUMBNAIL_MAX_EDGE_PX = 96
_THUMBNAIL_JPEG_QUALITY = 70

_UPSCALE_MENUS: dict[str, list[str]] = {
    "app_zoom": app_constants.zoom_option_list,
    "ai_model": app_constants.AI_models_list,
    "blending": app_constants.blending_list,
    "ai_multithreading": app_constants.AI_multithreading_list,
    "gpu": app_constants.gpus_list,
    "keep_frames": app_constants.keep_frames_list,
    "image_extension": app_constants.image_extension_list,
    "video_extension": app_constants.video_extension_list,
    "video_codec": app_constants.video_codec_list,
    "video_quality": app_constants.video_quality_list,
}

_FRAMEGEN_MENUS: dict[str, list[str]] = {
    "ai_model": ff_constants.FF_AI_models_list,
    "generation_option": ff_constants.generation_options_list,
    "gpu": app_constants.gpus_list,
    "keep_frames": app_constants.keep_frames_list,
    "image_extension": ff_constants.FF_image_extension_list,
    "video_output": ff_constants.FF_video_output_list,
}

_UPSCALE_INFO_TEXTS: dict[str, list[str]] = {
    "ai_model": info_texts.AI_MODEL_INFO,
    "blending": info_texts.AI_BLENDING_INFO,
    "ai_multithreading": info_texts.AI_MULTITHREADING_INFO,
    "input_resolution": info_texts.INPUT_RESOLUTION_INFO,
    "output_resolution": info_texts.OUTPUT_RESOLUTION_INFO,
    "gpu": info_texts.GPU_INFO,
    "vram_limiter": info_texts.VRAM_LIMITER_INFO,
    "image_extension": info_texts.IMAGE_OUTPUT_INFO,
    "video_extension": info_texts.VIDEO_EXTENSION_INFO,
    "video_codec": info_texts.VIDEO_CODEC_INFO,
    "keep_frames": info_texts.KEEP_FRAMES_INFO,
    "video_quality": info_texts.VIDEO_QUALITY_INFO,
    "output_path": info_texts.OUTPUT_PATH_INFO,
}

_FRAMEGEN_INFO_TEXTS: dict[str, list[str]] = {
    "ai_model": ff_info_texts.FF_AI_MODEL_INFO,
    "generation_option": ff_info_texts.FF_GENERATION_OPTION_INFO,
    "gpu": info_texts.GPU_INFO,
    "image_extension": ff_info_texts.FF_IMAGE_OUTPUT_INFO,
    "video_output": ff_info_texts.FF_VIDEO_OUTPUT_INFO,
    "keep_frames": ff_info_texts.FF_KEEP_FRAMES_INFO,
    "input_resolution": ff_info_texts.FF_INPUT_RESOLUTION_INFO,
    "cpu_number": ff_info_texts.FF_CPU_INFO,
    "output_path": info_texts.OUTPUT_PATH_INFO,
}


def _dataclass_from_dict(cls, data: dict):
    """Build *cls* from a JS dict, ignoring unknown keys."""
    known = {f.name for f in fields(cls)}
    return cls(**{key: value for key, value in dict(data).items() if key in known})


def _to_int_factor(value: Any) -> int:
    """Mirror the CTk GUI's lenient percentage parsing (0 on bad input)."""
    try:
        return int(float(str(value)))
    except Exception:
        return 0


class PyApi:
    """RPC surface for the webview frontend.

    ``ws`` is anything exposing ``url: str`` and ``broadcast(frame: dict)``
    (a :class:`qualityscaler.webview.ws.WsServer` in production, a fake in
    tests); it may be ``None`` for fully offline testing.
    """

    def __init__(
        self,
        upscale_controller,
        framegen_controller,
        ws=None,
        pref_path: str = USER_PREFERENCE_PATH,
        ff_pref_path: str = FF_USER_PREFERENCE_PATH,
    ) -> None:
        self._upscale_controller = upscale_controller
        self._framegen_controller = framegen_controller
        self._ws = ws
        self._pref_path = pref_path
        self._ff_pref_path = ff_pref_path
        self._window = None

    # Host-side plumbing (underscore-prefixed: NOT exposed to JS) ----------

    def _set_window(self, window) -> None:
        self._window = window

    def _require_window(self):
        if self._window is None:
            raise RuntimeError("pywebview window not attached (call _set_window first)")
        return self._window

    def _broadcast(self, frame: dict) -> None:
        if self._ws is not None:
            self._ws.broadcast(frame)

    def _forward_event(self, event: object, kind: str) -> None:
        try:
            self._broadcast(event_to_wire(event, kind))
        except ValueError:
            # Raw status strings and other unknown objects: not wire events.
            pass

    # State / static data ---------------------------

    def get_initial_state(self) -> dict:
        return {
            "upscale": asdict(load_preferences(self._pref_path)),
            "framegen": asdict(load_ff_preferences(self._ff_pref_path)),
            "version": app_constants.version,
        }

    def get_menus(self) -> dict:
        return {
            "upscale": {name: list(options) for name, options in _UPSCALE_MENUS.items()},
            "framegen": {name: list(options) for name, options in _FRAMEGEN_MENUS.items()},
        }

    def get_info_texts(self) -> dict:
        return {
            "upscale": {name: "".join(text) for name, text in _UPSCALE_INFO_TEXTS.items()},
            "framegen": {name: "".join(text) for name, text in _FRAMEGEN_INFO_TEXTS.items()},
        }

    # Native dialogs ---------------------------

    def pick_input_files(self) -> list[str]:
        import webview  # Lazy: only the dialog methods need pywebview.

        dialog_kind = getattr(getattr(webview, "FileDialog", None), "OPEN", None)
        if dialog_kind is None:
            dialog_kind = webview.OPEN_DIALOG

        result = self._require_window().create_file_dialog(
            dialog_kind,
            allow_multiple=True,
            directory=get_initial_dir(),
        )
        if not result:
            return []

        paths = [str(path) for path in result]
        update_last_used_dir(paths)
        supported = [
            path for path in paths
            if any(extension in path for extension in app_constants.supported_file_extensions)
        ]
        print(f"> Uploaded files: {len(paths)} => Supported files: {len(supported)}")
        return supported

    def pick_output_dir(self) -> Optional[str]:
        import webview  # Lazy: only the dialog methods need pywebview.

        dialog_kind = getattr(getattr(webview, "FileDialog", None), "FOLDER", None)
        if dialog_kind is None:
            dialog_kind = webview.FOLDER_DIALOG

        result = self._require_window().create_file_dialog(
            dialog_kind,
            directory=get_initial_dir(),
        )
        if not result:
            return None
        selected = str(result[0]) if isinstance(result, (list, tuple)) else str(result)
        update_last_used_dir(selected)
        return selected

    # File probing (left-hand info reveal) ---------------------------

    def probe_files(self, paths: list[str], settings: dict) -> list[dict]:
        settings = dict(settings or {})
        if "upscale_factor" in settings:
            upscale_factor = _to_int_factor(settings.get("upscale_factor"))
        else:
            upscale_factor = upscale_factor_for_model(str(settings.get("ai_model", "")))
        input_resize_factor = _to_int_factor(settings.get("input_resize_factor"))
        output_resize_factor = _to_int_factor(settings.get("output_resize_factor"))

        results: list[dict] = []
        for path in paths:
            results.append(
                self._probe_one(str(path), upscale_factor, input_resize_factor, output_resize_factor)
            )
        return results

    def _probe_one(
        self,
        path: str,
        upscale_factor: int,
        input_resize_factor: int,
        output_resize_factor: int,
    ) -> dict:
        title = os_path_basename(path)
        lines: list[dict] = []
        thumb_frame = None
        try:
            if check_if_file_is_video(path):
                width, height, video_lines, thumb_frame = _probe_video(path)
                lines.extend(video_lines)
            else:
                image = image_read(path)
                height, width = get_image_resolution(image)
                thumb_frame = image
                lines.append({"label": "resolution", "value": f"{width}x{height}"})
        except Exception as exc:
            return {
                "path": path,
                "title": title,
                "lines": [{"label": "error", "value": str(exc)}],
                "thumb_data_url": None,
            }

        # Recompute the AI input / AI output / File output projection with
        # the exact arithmetic + labels the CTk file widget uses.
        projection = format_resolution_projection(
            width, height, upscale_factor, input_resize_factor, output_resize_factor
        )
        if projection:
            for row in projection.split("\n"):
                label, _, value = row.partition("\t= ")
                lines.append({"label": label, "value": value})

        return {
            "path": path,
            "title": title,
            "lines": lines,
            "thumb_data_url": _thumb_data_url(thumb_frame),
        }

    # Preferences ---------------------------

    def save_preferences(self, kind: str, state: dict) -> bool:
        try:
            if kind == "upscale":
                save_preferences(_dataclass_from_dict(UIState, state), self._pref_path)
            elif kind == "framegen":
                save_ff_preferences(_dataclass_from_dict(FFUIState, state), self._ff_pref_path)
            else:
                return False
            return True
        except Exception as exc:
            print(f"[{app_constants.app_name}] save_preferences({kind!r}) failed: {exc}")
            return False

    # Pipeline control ---------------------------

    def start_upscale(self, settings: dict) -> bool:
        state = _dataclass_from_dict(UIState, settings)

        error = upscale_validate(state)
        if error is not None:
            self._broadcast({"type": "error", "kind": KIND_UPSCALE, "message": error})
            return False

        try:
            job_settings = upscale_build_settings(state)
            job_settings.validate()
        except (ValueError, KeyError) as exc:
            self._broadcast({"type": "error", "kind": KIND_UPSCALE, "message": str(exc)})
            return False

        self._upscale_controller.start(
            job_settings, lambda event: self._forward_event(event, KIND_UPSCALE)
        )
        return True

    def stop_upscale(self) -> bool:
        self._upscale_controller.request_stop()
        return True

    def start_framegen(self, settings: dict) -> bool:
        state = _dataclass_from_dict(FFUIState, settings)

        error = ff_validate(state)
        if error is not None:
            self._broadcast({"type": "error", "kind": KIND_FRAMEGEN, "message": error})
            return False

        try:
            job_settings = ff_build_settings(state)
            job_settings.validate()
        except (ValueError, KeyError) as exc:
            self._broadcast({"type": "error", "kind": KIND_FRAMEGEN, "message": str(exc)})
            return False

        self._framegen_controller.start(
            job_settings, lambda event: self._forward_event(event, KIND_FRAMEGEN)
        )
        return True

    def stop_framegen(self) -> bool:
        self._framegen_controller.request_stop()
        return True

    # Misc ---------------------------

    def report_renderer_error(self, message: str) -> None:
        print(f"[renderer-error] {message}", file=sys.stderr)

    def get_ws_url(self) -> str:
        if self._ws is None:
            raise RuntimeError("WebSocket server not configured")
        return self._ws.url

    def open_external(self, url: str) -> None:
        scheme = urlparse(str(url)).scheme.lower()
        if scheme not in ("http", "https"):
            raise ValueError(f"refusing to open non-http(s) url: {url!r}")
        webbrowser.open(str(url), new=1)


def _probe_video(path: str) -> tuple[int, int, list[dict], Any]:
    """Return (width, height, metadata lines, first frame or None)."""
    from cv2 import (
        CAP_PROP_FPS,
        CAP_PROP_FRAME_COUNT,
        CAP_PROP_FRAME_HEIGHT,
        CAP_PROP_FRAME_WIDTH,
        VideoCapture as opencv_VideoCapture,
    )

    cap = opencv_VideoCapture(path)
    try:
        width = round(cap.get(CAP_PROP_FRAME_WIDTH))
        height = round(cap.get(CAP_PROP_FRAME_HEIGHT))
        num_frames = int(cap.get(CAP_PROP_FRAME_COUNT))
        frame_rate = cap.get(CAP_PROP_FPS)
        frame_ok, first_frame = cap.read()
    finally:
        cap.release()

    lines: list[dict] = []
    if frame_rate > 0:
        duration = num_frames / frame_rate
        minutes = int(duration / 60)
        seconds = duration % 60
        lines.append({"label": "time", "value": f"{minutes}m:{round(seconds)}s"})
    lines.append({"label": "frames", "value": str(num_frames)})
    lines.append({"label": "resolution", "value": f"{width}x{height}"})

    return width, height, lines, (first_frame if frame_ok else None)


def _thumb_data_url(frame: Any) -> Optional[str]:
    """Encode a small JPEG data URL from a cv2 BGR(A) frame, or None."""
    if frame is None:
        return None
    try:
        from base64 import b64encode

        import cv2

        height, width = frame.shape[:2]
        if height <= 0 or width <= 0:
            return None

        scale = _THUMBNAIL_MAX_EDGE_PX / max(height, width)
        if scale < 1.0:
            frame = cv2.resize(
                frame,
                (max(1, int(width * scale)), max(1, int(height * scale))),
                interpolation=cv2.INTER_AREA,
            )
        if frame.ndim == 3 and frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), _THUMBNAIL_JPEG_QUALITY])
        if not ok:
            return None
        return "data:image/jpeg;base64," + b64encode(buffer.tobytes()).decode("ascii")
    except Exception:
        return None
