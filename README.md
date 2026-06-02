# QualityScaler

[![Build](../../actions/workflows/build.yml/badge.svg)](../../actions/workflows/build.yml)
[![Unit Tests](../../actions/workflows/unit-tests.yml/badge.svg)](../../actions/workflows/unit-tests.yml)
[![Linting](../../actions/workflows/lint.yml/badge.svg)](../../actions/workflows/lint.yml)

QualityScaler is an image and video upscaling GUI. This package is the lightweight launcher for that GUI: it installs small launcher dependencies, creates or reuses an isolated Python 3.10 runtime, installs the locked runtime dependencies there, and starts the GUI with `python -m qualityscaler.QualityScaler`.

The installed commands are:

```sh
quality-scaler
qualityscaler
```

Both commands call `qualityscaler.cli:main`.

## Runtime Environment

The launcher keeps the heavy AI and GUI runtime separate from the outer package environment. The first launch can take longer because the managed runtime is created and populated from `src/qualityscaler/requirements.runtime.lock.txt`. Later launches reuse the same runtime.

Runtime controls:

* `QUALITYSCALER_RUNTIME_ENV` overrides the managed runtime directory.
* `QUALITYSCALER_LAUNCH_TIMEOUT_SECONDS` limits the child GUI process lifetime for automation and tests.

Without an override, the runtime is stored under the platform cache directory:

* Windows: `%LOCALAPPDATA%\QualityScaler\runtime-py310`
* Linux/macOS: `$XDG_CACHE_HOME/QualityScaler/runtime-py310` or `~/.cache/QualityScaler/runtime-py310`

## Development

Install the lightweight launcher package and test tools:

```sh
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r requirements.testing.txt
```

Run the focused unit tests:

```sh
pytest tests -vv
```

These tests validate the launcher contract without importing the AI runtime dependencies or opening the GUI.

Run linting for the lightweight launcher and tests:

```sh
ruff check src/qualityscaler/cli.py tests
```

## Versions

* `3.4.0` - Updated to upstream 3.4 with AI multithreading and selectable output paths.
* `3.2.0` - Updated to upstream 3.2 with multi-GPU selection and video frame overwrite fixes.
* `3.1.0` - Updated to upstream 3.1 with FFMPEG 6.1.1 support and UI/file information improvements.
* `3.0.0` - Updated to upstream 3.0.0 ONNX/DirectML engine while preserving isolated runtime and lazy ONNX model downloads.
* `2.13.0` - Updated to upstream 2.13 version while preserving isolated runtime and lazy model downloads.
* `2.12.0` - Updated to upstream 2.12.0 version.
