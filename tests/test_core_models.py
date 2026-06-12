from __future__ import annotations

import pytest

from qualityscaler.core.models import ModelManifestEntry, parse_manifest_entry


def test_parse_manifest_entry_returns_typed_struct() -> None:
    manifest = {
        "latest": "v2",
        "v1": {"href": "https://example.com/old.zst", "sha256": "aaa"},
        "v2": {"href": "https://example.com/new.zst", "sha256": "bbb"},
    }
    entry = parse_manifest_entry(manifest, "BSRGANx4")
    assert entry == ModelManifestEntry(href="https://example.com/new.zst", sha256="bbb")


def test_parse_manifest_entry_is_frozen() -> None:
    entry = ModelManifestEntry(href="https://example.com/m.zst", sha256="abc")
    with pytest.raises(AttributeError):
        entry.sha256 = "tampered"  # type: ignore[misc]


@pytest.mark.parametrize(
    "manifest",
    [
        {},
        {"latest": "v1"},
        {"latest": "v1", "v1": {"href": "https://example.com/m.zst"}},
        {"latest": "v1", "v1": {"sha256": "abc"}},
    ],
)
def test_parse_manifest_entry_missing_key_raises_value_error(manifest: dict) -> None:
    with pytest.raises(ValueError, match="Model manifest entry for 'BSRGANx4' is missing key"):
        parse_manifest_entry(manifest, "BSRGANx4")
