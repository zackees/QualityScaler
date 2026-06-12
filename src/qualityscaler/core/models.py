from __future__ import annotations

import hashlib
import os

MODEL_MANIFEST_BASE_URL = "https://raw.githubusercontent.com/zackees/ai-image-video-models/main/assets/qualityscaler/onnx"


def _package_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_model_path(model_name: str) -> str:
    return os.path.join(_package_dir(), "AI-onnx", f"{model_name}_fp16.onnx")


def get_model_manifest_entry(model_name: str) -> dict:
    import requests

    model_key = model_name.removesuffix("_fp16.onnx")
    response = requests.get(f"{MODEL_MANIFEST_BASE_URL}/{model_key}/manifest.json", timeout=60)
    response.raise_for_status()
    manifest = response.json()
    return manifest[manifest["latest"]]


def ensure_model_file(model_path: str) -> None:
    if os.path.exists(model_path):
        return

    from download import download
    from zstandard import ZstdDecompressor

    model_name = os.path.basename(model_path)
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    entry = get_model_manifest_entry(model_name)
    zst_path = f"{model_path}.zst"
    download(entry["href"], zst_path, replace=False, timeout=60 * 5)

    file_hash = hashlib.sha256()
    with open(zst_path, "rb") as compressed:
        for chunk in iter(lambda: compressed.read(1 << 20), b""):
            file_hash.update(chunk)
    if file_hash.hexdigest() != entry["sha256"]:
        os.remove(zst_path)
        raise ValueError(f"sha256 mismatch for {model_name}, download corrupted")

    temp_path = f"{model_path}.tmp"
    with open(zst_path, "rb") as compressed, open(temp_path, "wb") as decompressed:
        ZstdDecompressor().copy_stream(compressed, decompressed)
    os.replace(temp_path, model_path)
    os.remove(zst_path)
