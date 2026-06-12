"""Unit tests for qualityscaler.gui.file_chooser.

The module is toolkit-free and can be exercised headlessly.
"""

from __future__ import annotations

import os
import importlib
from pathlib import Path


def _fresh_module():
    """Re-import file_chooser with a clean module state so each test starts
    with _last_used_dir = None.  We do this by reloading the module."""
    import qualityscaler.gui.file_chooser as m
    importlib.reload(m)
    return m


def test_launch_cwd_captured_as_string():
    """LAUNCH_CWD must be a non-empty string."""
    m = _fresh_module()
    assert isinstance(m.LAUNCH_CWD, str)
    assert m.LAUNCH_CWD != ""


def test_launch_cwd_is_a_directory():
    """LAUNCH_CWD must point to an existing directory (cwd always exists)."""
    m = _fresh_module()
    assert os.path.isdir(m.LAUNCH_CWD)


def test_get_initial_dir_defaults_to_launch_cwd(tmp_path):
    """Before any selection, get_initial_dir() returns LAUNCH_CWD."""
    m = _fresh_module()
    # Override LAUNCH_CWD to a known existing directory.
    m.LAUNCH_CWD = str(tmp_path)
    assert m.get_initial_dir() == str(tmp_path)


def test_update_with_file_path_sets_parent(tmp_path):
    """update_last_used_dir with a file path records its parent directory."""
    m = _fresh_module()
    m.LAUNCH_CWD = str(tmp_path)

    fake_file = str(tmp_path / "video.mp4")
    m.update_last_used_dir(fake_file)
    assert m.get_initial_dir() == str(tmp_path)


def test_update_with_directory_path(tmp_path):
    """update_last_used_dir with a directory path records that directory."""
    m = _fresh_module()
    m.LAUNCH_CWD = str(tmp_path)

    sub = tmp_path / "subdir"
    sub.mkdir()
    m.update_last_used_dir(str(sub))
    assert m.get_initial_dir() == str(sub)


def test_update_with_list_of_files(tmp_path):
    """update_last_used_dir with a list of files uses the first file's parent."""
    m = _fresh_module()
    m.LAUNCH_CWD = str(tmp_path)

    files = [str(tmp_path / "a.png"), str(tmp_path / "b.png")]
    m.update_last_used_dir(files)
    assert m.get_initial_dir() == str(tmp_path)


def test_update_with_empty_list_is_ignored(tmp_path):
    """update_last_used_dir with an empty list does not change state."""
    m = _fresh_module()
    m.LAUNCH_CWD = str(tmp_path)

    m.update_last_used_dir([])
    # Should still return LAUNCH_CWD, not crash.
    assert m.get_initial_dir() == str(tmp_path)


def test_update_with_empty_string_is_ignored(tmp_path):
    """update_last_used_dir with an empty string does not change state."""
    m = _fresh_module()
    m.LAUNCH_CWD = str(tmp_path)

    m.update_last_used_dir("")
    assert m.get_initial_dir() == str(tmp_path)


def test_last_used_dir_survives_across_calls(tmp_path):
    """The last-used directory persists across multiple get_initial_dir calls."""
    m = _fresh_module()
    m.LAUNCH_CWD = str(tmp_path)

    sub = tmp_path / "project"
    sub.mkdir()
    m.update_last_used_dir(str(sub))

    assert m.get_initial_dir() == str(sub)
    assert m.get_initial_dir() == str(sub)  # stable on repeated calls


def test_subsequent_update_overrides_previous(tmp_path):
    """A second update replaces the previously remembered directory."""
    m = _fresh_module()
    m.LAUNCH_CWD = str(tmp_path)

    first = tmp_path / "first"
    first.mkdir()
    second = tmp_path / "second"
    second.mkdir()

    m.update_last_used_dir(str(first))
    m.update_last_used_dir(str(second))
    assert m.get_initial_dir() == str(second)


def test_fallback_when_last_used_dir_no_longer_exists(tmp_path):
    """If the last-used directory is deleted, get_initial_dir falls back to LAUNCH_CWD."""
    m = _fresh_module()
    m.LAUNCH_CWD = str(tmp_path)

    vanished = tmp_path / "gone"
    vanished.mkdir()
    m.update_last_used_dir(str(vanished))
    vanished.rmdir()  # delete it

    # Should fall back gracefully, not crash.
    result = m.get_initial_dir()
    assert os.path.isdir(result)
    assert result == str(tmp_path)


def test_fallback_home_when_launch_cwd_also_missing(tmp_path, monkeypatch):
    """If both last-used and launch cwd are gone, falls back to home dir."""
    m = _fresh_module()

    # Point LAUNCH_CWD at a non-existent path.
    m.LAUNCH_CWD = str(tmp_path / "nonexistent")
    # _last_used_dir is None (fresh reload).

    result = m.get_initial_dir()
    assert os.path.isdir(result)
    assert result == str(Path.home())
