"""Contract tests for the webview RPC bridge (qualityscaler.webview.js_api).

PyApi keeps its pywebview/cv2 imports lazy, so these tests run without
pywebview installed; the probe tests skip gracefully when OpenCV/numpy are
missing (mirroring how tests/test_core_proc.py skips on running-process).
"""

from __future__ import annotations

from dataclasses import asdict, fields
from pathlib import Path

import pytest

from qualityscaler.app import constants as app_constants
from qualityscaler.app import ff_constants
from qualityscaler.app.ff_preferences import load_ff_preferences
from qualityscaler.app.ff_state import FFUIState
from qualityscaler.app.preferences import load_preferences
from qualityscaler.app.state import UIState
from qualityscaler.core import UpscaleProgress, UpscaleSettings
from qualityscaler.fluidframes.settings import FrameGenSettings
from qualityscaler.webview.js_api import PyApi


class FakeController:
    def __init__(self) -> None:
        self.started_settings = None
        self.on_event = None
        self.stop_requested = False

    def start(self, settings, on_event) -> None:
        self.started_settings = settings
        self.on_event = on_event

    def request_stop(self) -> None:
        self.stop_requested = True


class FakeWs:
    url = "ws://127.0.0.1:12345"

    def __init__(self) -> None:
        self.frames: list[dict] = []

    def broadcast(self, frame: dict) -> None:
        self.frames.append(frame)


@pytest.fixture
def api(tmp_path: Path):
    upscale = FakeController()
    framegen = FakeController()
    ws = FakeWs()
    api = PyApi(
        upscale,
        framegen,
        ws=ws,
        pref_path=str(tmp_path / "prefs.json"),
        ff_pref_path=str(tmp_path / "ff_prefs.json"),
    )
    api._fake_upscale = upscale
    api._fake_framegen = framegen
    api._fake_ws = ws
    return api


# get_initial_state ---------------------------


def test_get_initial_state_shape(api) -> None:
    state = api.get_initial_state()

    assert set(state) == {"upscale", "framegen", "version"}
    assert state["version"] == app_constants.version
    assert set(state["upscale"]) == {f.name for f in fields(UIState)}
    assert set(state["framegen"]) == {f.name for f in fields(FFUIState)}
    assert state["upscale"]["ai_model"] == UIState().ai_model
    assert state["framegen"]["generation_option"] == FFUIState().generation_option


# get_menus / get_info_texts ---------------------------


def test_get_menus_matches_app_constants(api) -> None:
    menus = api.get_menus()

    assert set(menus) == {"upscale", "framegen"}
    for mode in ("upscale", "framegen"):
        for name, options in menus[mode].items():
            assert isinstance(options, list) and options, f"{mode}.{name} empty"
            assert all(isinstance(option, str) for option in options)

    assert menus["upscale"]["ai_model"] == app_constants.AI_models_list
    assert menus["upscale"]["blending"] == app_constants.blending_list
    assert menus["upscale"]["ai_multithreading"] == app_constants.AI_multithreading_list
    assert menus["upscale"]["gpu"] == app_constants.gpus_list
    assert menus["upscale"]["image_extension"] == app_constants.image_extension_list
    assert menus["upscale"]["video_extension"] == app_constants.video_extension_list
    assert menus["upscale"]["video_codec"] == app_constants.video_codec_list
    assert menus["upscale"]["keep_frames"] == app_constants.keep_frames_list
    assert menus["upscale"]["video_quality"] == app_constants.video_quality_list
    assert menus["upscale"]["app_zoom"] == app_constants.zoom_option_list

    assert menus["framegen"]["ai_model"] == ff_constants.FF_AI_models_list
    assert menus["framegen"]["generation_option"] == ff_constants.generation_options_list
    assert menus["framegen"]["video_output"] == ff_constants.FF_video_output_list


def test_get_info_texts_non_empty(api) -> None:
    texts = api.get_info_texts()

    assert set(texts) == {"upscale", "framegen"}
    for mode in ("upscale", "framegen"):
        assert texts[mode], f"no info texts for {mode}"
        for name, text in texts[mode].items():
            assert isinstance(text, str) and text.strip(), f"{mode}.{name} empty"
    assert "ai_model" in texts["upscale"]
    assert "output_path" in texts["framegen"]


# probe_files ---------------------------


def _write_tiny_image(path: Path):
    cv2 = pytest.importorskip("cv2")
    numpy = pytest.importorskip("numpy")
    image = numpy.full((24, 32, 3), 128, dtype=numpy.uint8)
    assert cv2.imwrite(str(path), image)
    return path


def _write_tiny_video(path: Path):
    cv2 = pytest.importorskip("cv2")
    numpy = pytest.importorskip("numpy")
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10.0, (32, 24))
    if not writer.isOpened():
        pytest.skip("cv2 VideoWriter cannot encode mp4v on this platform")
    frame = numpy.zeros((24, 32, 3), dtype=numpy.uint8)
    for _ in range(10):
        writer.write(frame)
    writer.release()
    return path


def _labels(result: dict) -> list[str]:
    return [line["label"] for line in result["lines"]]


def test_probe_files_image_has_info_reveal_lines(api, tmp_path: Path) -> None:
    image_path = _write_tiny_image(tmp_path / "tiny.png")

    settings = {"ai_model": "BSRGANx2", "input_resize_factor": "50", "output_resize_factor": "100"}
    (result,) = api.probe_files([str(image_path)], settings)

    assert result["path"] == str(image_path)
    assert result["title"] == "tiny.png"
    labels = _labels(result)
    assert "resolution" in labels
    assert "AI input (50%)" in labels
    assert "AI output (x2)" in labels
    assert "File output (100%)" in labels

    by_label = {line["label"]: line["value"] for line in result["lines"]}
    assert by_label["resolution"] == "32x24"
    assert by_label["AI input (50%)"] == "16x12"      # 32x24 @ 50%
    assert by_label["AI output (x2)"] == "32x24"      # x2 model
    assert by_label["File output (100%)"] == "32x24"  # 100% output

    assert result["thumb_data_url"] is None or result["thumb_data_url"].startswith("data:image/jpeg;base64,")


def test_probe_files_video_has_time_frames_resolution(api, tmp_path: Path) -> None:
    video_path = _write_tiny_video(tmp_path / "tiny.mp4")

    settings = {"ai_model": "RealESR_Gx4", "input_resize_factor": "100", "output_resize_factor": "50"}
    (result,) = api.probe_files([str(video_path)], settings)

    labels = _labels(result)
    assert "time" in labels
    assert "frames" in labels
    assert "resolution" in labels
    assert "AI input (100%)" in labels
    assert "AI output (x4)" in labels
    assert "File output (50%)" in labels


def test_probe_files_separator_model_omits_projection(api, tmp_path: Path) -> None:
    image_path = _write_tiny_image(tmp_path / "tiny2.png")

    settings = {"ai_model": "----", "input_resize_factor": "50", "output_resize_factor": "100"}
    (result,) = api.probe_files([str(image_path)], settings)

    labels = _labels(result)
    assert labels == ["resolution"]


def test_probe_files_missing_file_reports_error_line(api, tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    missing = tmp_path / "nope.png"

    settings = {"ai_model": "BSRGANx2", "input_resize_factor": "50", "output_resize_factor": "100"}
    (result,) = api.probe_files([str(missing)], settings)

    assert result["thumb_data_url"] is None
    assert _labels(result) == ["error"]


# start/stop ---------------------------


def test_start_upscale_builds_settings_on_controller(api, tmp_path: Path) -> None:
    input_file = tmp_path / "input.png"
    input_file.write_bytes(b"not really a png")

    state = UIState(file_list=[str(input_file)])
    assert api.start_upscale(asdict(state)) is True

    settings = api._fake_upscale.started_settings
    assert isinstance(settings, UpscaleSettings)
    assert settings.input_paths == [str(input_file)]
    assert settings.ai_model == state.ai_model
    assert settings.output_path is None  # OUTPUT_PATH_CODED maps to None
    assert settings.input_resize_factor == pytest.approx(0.5)
    assert settings.output_resize_factor == pytest.approx(1.0)
    assert settings.vram_gb == pytest.approx(4.0)
    assert settings.multithreading == 1  # "OFF"
    assert settings.keep_frames is True  # default label "ON"

    # Pipeline events flow through the on_event callback to the WS broadcast.
    api._fake_upscale.on_event(UpscaleProgress(message="Upscaling", file_index=1, fraction=0.5))
    frames = api._fake_ws.frames
    assert frames[-1]["type"] == "progress"
    assert frames[-1]["kind"] == "upscale"
    assert frames[-1]["fraction"] == pytest.approx(0.5)


def test_start_upscale_validation_error_broadcasts_and_returns_false(api) -> None:
    state = UIState(file_list=[])
    assert api.start_upscale(asdict(state)) is False
    assert api._fake_upscale.started_settings is None

    frames = api._fake_ws.frames
    assert frames and frames[-1]["type"] == "error"
    assert frames[-1]["kind"] == "upscale"
    assert frames[-1]["message"] == "Please select a file"


def test_start_framegen_builds_settings_on_controller(api, tmp_path: Path) -> None:
    input_file = tmp_path / "input.mp4"
    input_file.write_bytes(b"not really an mp4")

    state = FFUIState(file_list=[str(input_file)], generation_option="Slowmotion x4")
    assert api.start_framegen(asdict(state)) is True

    settings = api._fake_framegen.started_settings
    assert isinstance(settings, FrameGenSettings)
    assert settings.input_paths == [str(input_file)]
    assert settings.frame_gen_factor == 4
    assert settings.slowmotion is True
    assert settings.video_extension == ".mp4"
    assert settings.video_codec == "x264"


def test_start_framegen_rejects_non_video(api, tmp_path: Path) -> None:
    state = FFUIState(file_list=[str(tmp_path / "photo.png")])
    assert api.start_framegen(asdict(state)) is False
    assert api._fake_framegen.started_settings is None
    assert api._fake_ws.frames[-1]["kind"] == "framegen"


def test_stop_methods_request_stop(api) -> None:
    assert api.stop_upscale() is True
    assert api.stop_framegen() is True
    assert api._fake_upscale.stop_requested is True
    assert api._fake_framegen.stop_requested is True


# preferences ---------------------------


def test_save_preferences_round_trip(api, tmp_path: Path) -> None:
    state = UIState(ai_model="BSRGANx4", input_resize_factor="75")
    assert api.save_preferences("upscale", asdict(state)) is True
    loaded = load_preferences(str(tmp_path / "prefs.json"))
    assert loaded.ai_model == "BSRGANx4"
    assert loaded.input_resize_factor == "75"

    ff_state = FFUIState(generation_option="x8", cpu_number="2")
    assert api.save_preferences("framegen", asdict(ff_state)) is True
    ff_loaded = load_ff_preferences(str(tmp_path / "ff_prefs.json"))
    assert ff_loaded.generation_option == "x8"
    assert ff_loaded.cpu_number == "2"


def test_save_preferences_unknown_kind_returns_false(api) -> None:
    assert api.save_preferences("bogus", {}) is False


# misc ---------------------------


def test_get_ws_url(api) -> None:
    assert api.get_ws_url() == FakeWs.url


def test_open_external_rejects_non_http(api) -> None:
    with pytest.raises(ValueError):
        api.open_external("file:///C:/Windows/system32")
    with pytest.raises(ValueError):
        api.open_external("javascript:alert(1)")


def test_report_renderer_error_logs_to_stderr(api, capsys) -> None:
    api.report_renderer_error("TypeError: boom (index.js:1:1)")
    captured = capsys.readouterr()
    assert "[renderer-error] TypeError: boom (index.js:1:1)" in captured.err


def test_open_external_opens_http(api, monkeypatch) -> None:
    opened: list[str] = []
    import qualityscaler.webview.js_api as js_api_module

    monkeypatch.setattr(js_api_module.webbrowser, "open", lambda url, new=0: opened.append(url))
    api.open_external("https://example.com")
    assert opened == ["https://example.com"]
