from __future__ import annotations

import importlib
import sys
import types
from dataclasses import dataclass, field
from typing import Any, Iterator

import pytest

FAKE_MODELS = ["FakeModelA", "FakeModelB", "RealESR_Gx4"]


def _make_fake_core(events: list[Any], created_jobs: list[Any]) -> types.ModuleType:
    core = types.ModuleType("qualityscaler.core")

    @dataclass
    class UpscaleSettings:
        input_paths: list[str] = field(default_factory=list)
        output_path: str | None = None
        ai_model: str = "RealESR_Gx4"
        gpu: str = "Auto"
        vram_gb: float = 4.0
        multithreading: int = 1
        input_resize_factor: float = 1.0
        output_resize_factor: float = 1.0
        blending: str = "OFF"
        keep_frames: bool = False
        image_extension: str = ".png"
        video_extension: str = ".mp4"
        video_codec: str = "x264"
        video_quality: str = "HIGH"

        def validate(self) -> None:
            if not self.input_paths:
                raise ValueError("at least one input path is required")
            if self.input_paths == ["invalid.png"]:
                raise ValueError("invalid input file")

    class UpscaleEvent:
        pass

    @dataclass
    class UpscaleProgress(UpscaleEvent):
        message: str
        file_index: int
        file_count: int
        fraction: float | None
        phase: str

    @dataclass
    class UpscaleCompleted(UpscaleEvent):
        output_paths: tuple[str, ...]

    @dataclass
    class UpscaleError(UpscaleEvent):
        message: str

    @dataclass
    class UpscaleStopped(UpscaleEvent):
        pass

    class UpscaleJob:
        def __init__(self, settings: Any) -> None:
            self.settings = settings
            self.started = False
            self.cancelled = False
            created_jobs.append(self)

        def start(self) -> None:
            self.started = True

        def cancel(self) -> None:
            self.cancelled = True

        def events(self) -> Iterator[Any]:
            yield from events

        def wait(self) -> None:
            pass

    core.UpscaleSettings = UpscaleSettings
    core.UpscaleEvent = UpscaleEvent
    core.UpscaleProgress = UpscaleProgress
    core.UpscaleCompleted = UpscaleCompleted
    core.UpscaleError = UpscaleError
    core.UpscaleStopped = UpscaleStopped
    core.UpscaleJob = UpscaleJob
    core.AI_MODELS = list(FAKE_MODELS)
    core.VIDEO_QUALITIES = ["LOW", "MEDIUM", "HIGH"]
    core.app_version = lambda: "9.9.9"
    return core


@pytest.fixture()
def runtime_env(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Import qualityscaler.cli_runtime against a scripted fake core module."""
    events: list[Any] = []
    created_jobs: list[Any] = []
    core = _make_fake_core(events, created_jobs)
    monkeypatch.setitem(sys.modules, "qualityscaler.core", core)
    sys.modules.pop("qualityscaler.cli_runtime", None)
    module = importlib.import_module("qualityscaler.cli_runtime")
    yield types.SimpleNamespace(module=module, core=core, events=events, jobs=created_jobs)
    sys.modules.pop("qualityscaler.cli_runtime", None)


def test_upscale_maps_args_to_settings(runtime_env: Any) -> None:
    runtime_env.events.append(runtime_env.core.UpscaleCompleted(output_paths=("out.png",)))

    exit_code = runtime_env.module.main(
        [
            "upscale",
            "a.png",
            "b.mp4",
            "--model",
            "FakeModelB",
            "--output",
            "outdir",
            "--gpu",
            "GPU 2",
            "--vram",
            "8",
            "--threads",
            "3",
            "--input-resize",
            "50",
            "--output-resize",
            "75",
            "--blending",
            "High",
            "--image-ext",
            ".jpg",
            "--video-ext",
            ".mkv",
            "--codec",
            "x265",
            "--video-quality",
            "MEDIUM",
            "--keep-frames",
            "--quiet",
        ]
    )

    assert exit_code == 0
    assert len(runtime_env.jobs) == 1
    job = runtime_env.jobs[0]
    assert job.started
    settings = job.settings
    assert settings.input_paths == ["a.png", "b.mp4"]
    assert settings.output_path == "outdir"
    assert settings.ai_model == "FakeModelB"
    assert settings.gpu == "GPU 2"
    assert settings.vram_gb == 8.0
    assert settings.multithreading == 3
    assert settings.input_resize_factor == 0.5
    assert settings.output_resize_factor == 0.75
    assert settings.blending == "High"
    assert settings.keep_frames is True
    assert settings.image_extension == ".jpg"
    assert settings.video_extension == ".mkv"
    assert settings.video_codec == "x265"
    assert settings.video_quality == "MEDIUM"


def test_upscale_defaults(runtime_env: Any) -> None:
    runtime_env.events.append(runtime_env.core.UpscaleCompleted(output_paths=()))

    assert runtime_env.module.main(["upscale", "a.png", "-q"]) == 0

    settings = runtime_env.jobs[0].settings
    assert settings.output_path is None
    assert settings.ai_model == "RealESR_Gx4"
    assert settings.gpu == "Auto"
    assert settings.vram_gb == 4.0
    assert settings.multithreading == 1
    assert settings.input_resize_factor == 1.0
    assert settings.output_resize_factor == 1.0
    assert settings.blending == "OFF"
    assert settings.keep_frames is False
    assert settings.video_quality == "HIGH"


def test_upscale_rejects_unknown_video_quality(runtime_env: Any) -> None:
    with pytest.raises(SystemExit) as excinfo:
        runtime_env.module.main(["upscale", "a.png", "--video-quality", "ULTRA"])

    assert excinfo.value.code == 2


def test_upscale_completed_prints_output_paths_to_stdout(
    runtime_env: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_env.events.append(runtime_env.core.UpscaleCompleted(output_paths=("one.png", "two.png")))

    assert runtime_env.module.main(["upscale", "a.png"]) == 0

    captured = capsys.readouterr()
    assert captured.out == "one.png\ntwo.png\n"


def test_upscale_progress_goes_to_stderr_with_percentage(
    runtime_env: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_env.events.extend(
        [
            runtime_env.core.UpscaleProgress(message="Upscaling frames", file_index=1, file_count=2, fraction=0.42, phase="upscale"),
            runtime_env.core.UpscaleProgress(message="Loading model", file_index=2, file_count=2, fraction=None, phase="setup"),
            runtime_env.core.UpscaleCompleted(output_paths=("done.png",)),
        ]
    )

    assert runtime_env.module.main(["upscale", "a.png"]) == 0

    captured = capsys.readouterr()
    assert "[1/2] Upscaling frames (42%)" in captured.err
    assert "[2/2] Loading model" in captured.err
    assert "(42%)" not in captured.out


def test_upscale_quiet_suppresses_progress(
    runtime_env: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_env.events.extend(
        [
            runtime_env.core.UpscaleProgress(message="Upscaling", file_index=1, file_count=1, fraction=0.5, phase="upscale"),
            runtime_env.core.UpscaleCompleted(output_paths=("done.png",)),
        ]
    )

    assert runtime_env.module.main(["upscale", "a.png", "--quiet"]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == "done.png\n"


def test_upscale_error_exits_1_and_prints_message(
    runtime_env: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runtime_env.events.append(runtime_env.core.UpscaleError(message="GPU exploded"))

    assert runtime_env.module.main(["upscale", "a.png"]) == 1

    assert "GPU exploded" in capsys.readouterr().err


def test_upscale_stopped_exits_130(runtime_env: Any) -> None:
    runtime_env.events.append(runtime_env.core.UpscaleStopped())

    assert runtime_env.module.main(["upscale", "a.png"]) == 130


def test_upscale_invalid_settings_is_argparse_error(
    runtime_env: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        runtime_env.module.main(["upscale", "invalid.png"])

    assert excinfo.value.code == 2
    assert "invalid input file" in capsys.readouterr().err
    assert runtime_env.jobs == []


def test_upscale_rejects_unknown_model(runtime_env: Any) -> None:
    with pytest.raises(SystemExit) as excinfo:
        runtime_env.module.main(["upscale", "a.png", "--model", "NotAModel"])

    assert excinfo.value.code == 2


def test_models_lists_models_one_per_line(
    runtime_env: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert runtime_env.module.main(["models"]) == 0

    assert capsys.readouterr().out == "".join(f"{model}\n" for model in FAKE_MODELS)


def test_version_prints_app_version(
    runtime_env: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        runtime_env.module.main(["--version"])

    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == "9.9.9"


def test_no_subcommand_prints_help_and_exits_2(
    runtime_env: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert runtime_env.module.main([]) == 2

    assert "usage: qualityscaler" in capsys.readouterr().out
