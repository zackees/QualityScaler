"""QualityScaler command line interface, executed inside the managed runtime environment."""

from __future__ import annotations

import argparse
import signal
import sys

from qualityscaler.core import (
    AI_MODELS,
    UpscaleCompleted,
    UpscaleError,
    UpscaleJob,
    UpscaleProgress,
    UpscaleSettings,
    UpscaleStopped,
    app_version,
)

GPU_CHOICES = ["Auto", "GPU 1", "GPU 2", "GPU 3", "GPU 4"]
BLENDING_CHOICES = ["OFF", "Low", "Medium", "High"]
IMAGE_EXTENSIONS = [".png", ".jpg", ".bmp", ".tiff"]
VIDEO_EXTENSIONS = [".mp4", ".mkv", ".avi", ".mov"]
VIDEO_CODECS = ["x264", "x265", "h264_nvenc", "hevc_nvenc", "h264_amf", "hevc_amf", "h264_qsv", "hevc_qsv"]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="qualityscaler", description="AI image and video upscaler.")
    parser.add_argument("--version", action="version", version=app_version())
    subparsers = parser.add_subparsers(dest="command")

    upscale = subparsers.add_parser("upscale", help="Upscale one or more images or videos.")
    upscale.add_argument("inputs", nargs="+", metavar="INPUT", help="Input image or video file paths.")
    upscale.add_argument("--model", "-m", choices=AI_MODELS, default="RealESR_Gx4", help="AI model to use (default: %(default)s).")
    upscale.add_argument("--output", "-o", default=None, metavar="DIR", help="Output directory (default: alongside each input).")
    upscale.add_argument("--gpu", choices=GPU_CHOICES, default="Auto", help="GPU to use (default: %(default)s).")
    upscale.add_argument("--vram", type=float, default=4.0, metavar="GB", help="GPU VRAM budget in gigabytes (default: %(default)s).")
    upscale.add_argument("--threads", type=int, default=1, metavar="N", help="Number of parallel upscale threads (default: %(default)s).")
    upscale.add_argument("--input-resize", type=float, default=100.0, metavar="PERCENT", help="Resize inputs to this percentage before upscaling (default: %(default)s).")
    upscale.add_argument("--output-resize", type=float, default=100.0, metavar="PERCENT", help="Resize outputs to this percentage after upscaling (default: %(default)s).")
    upscale.add_argument("--blending", choices=BLENDING_CHOICES, default="OFF", help="Blend the upscaled result with the original (default: %(default)s).")
    upscale.add_argument("--image-ext", choices=IMAGE_EXTENSIONS, default=".png", help="Output image extension (default: %(default)s).")
    upscale.add_argument("--video-ext", choices=VIDEO_EXTENSIONS, default=".mp4", help="Output video extension (default: %(default)s).")
    upscale.add_argument("--codec", choices=VIDEO_CODECS, default="x264", help="Video codec for encoded outputs (default: %(default)s).")
    upscale.add_argument("--keep-frames", action="store_true", help="Keep extracted video frames after upscaling.")
    upscale.add_argument("--quiet", "-q", action="store_true", help="Suppress progress output.")

    subparsers.add_parser("models", help="List the available AI models.")
    return parser


def _format_progress(event: UpscaleProgress) -> str:
    line = f"[{event.file_index}/{event.file_count}] {event.message}"
    if event.fraction is not None:
        line += f" ({event.fraction * 100.0:.0f}%)"
    return line


def _run_upscale(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    settings = UpscaleSettings(
        input_paths=list(args.inputs),
        output_path=args.output,
        ai_model=args.model,
        gpu=args.gpu,
        vram_gb=args.vram,
        multithreading=args.threads,
        input_resize_factor=args.input_resize / 100.0,
        output_resize_factor=args.output_resize / 100.0,
        blending=args.blending,
        keep_frames=args.keep_frames,
        image_extension=args.image_ext,
        video_extension=args.video_ext,
        video_codec=args.codec,
    )
    try:
        settings.validate()
    except ValueError as exc:
        parser.error(str(exc))

    job = UpscaleJob(settings)
    job.start()
    previous_handler = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, lambda _signum, _frame: job.cancel())

    exit_code = 1
    try:
        for event in job.events():
            if isinstance(event, UpscaleProgress):
                if not args.quiet:
                    sys.stderr.write(_format_progress(event) + "\n")
                    sys.stderr.flush()
            elif isinstance(event, UpscaleCompleted):
                for output_path in event.output_paths:
                    sys.stdout.write(output_path + "\n")
                sys.stdout.flush()
                exit_code = 0
            elif isinstance(event, UpscaleStopped):
                exit_code = 130
            elif isinstance(event, UpscaleError):
                sys.stderr.write(event.message + "\n")
                sys.stderr.flush()
                exit_code = 1
    finally:
        signal.signal(signal.SIGINT, previous_handler)
    return exit_code


def _run_models() -> int:
    for model in AI_MODELS:
        sys.stdout.write(model + "\n")
    sys.stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "upscale":
        return _run_upscale(parser, args)
    if args.command == "models":
        return _run_models()
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
