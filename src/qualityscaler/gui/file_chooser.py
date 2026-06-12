"""File-chooser directory state.

Toolkit-free module that tracks the initial directory for all file/folder
dialogs in QualityScaler.

Two responsibilities:
1. Capture the process launch cwd exactly once at module import time (before
   any code can call ``os.chdir``).  All dialogs default there on first use.
2. Maintain a shared, in-session *last-used directory* that is updated after
   every successful file/folder selection.  Subsequent dialogs open at the
   last-used directory so consecutive picks within one run feel natural.

No on-disk persistence; state is discarded when the process exits.
"""

from __future__ import annotations

import os
from pathlib import Path

# Captured once at import time.  Future-proof against any os.chdir call that
# might be introduced later in the startup path.
LAUNCH_CWD: str = os.getcwd()

# Shared last-used directory; None means "not yet set, use LAUNCH_CWD".
_last_used_dir: str | None = None


def get_initial_dir() -> str:
    """Return the directory that the next dialog should open at.

    Returns the last-used directory if one has been recorded in this session,
    otherwise returns the launch cwd.

    If the resolved directory no longer exists on disk, falls back to the
    launch cwd so tkinter receives a valid (or at least reasonable) path.
    """
    candidate = _last_used_dir if _last_used_dir is not None else LAUNCH_CWD
    if os.path.isdir(candidate):
        return candidate
    # Graceful fallback: the directory was deleted after the app started.
    return LAUNCH_CWD if os.path.isdir(LAUNCH_CWD) else str(Path.home())


def update_last_used_dir(selection: str | list[str] | tuple[str, ...]) -> None:
    """Record the directory from a successful file/folder selection.

    *selection* may be:
    - a single path string (from ``askdirectory`` or ``askopenfilename``),
    - a list/tuple of path strings (from ``askopenfilenames``).

    Empty strings and empty collections are silently ignored so callers can
    pass the raw dialog return value without pre-filtering.
    """
    global _last_used_dir

    if isinstance(selection, (list, tuple)):
        if not selection:
            return
        first = selection[0]
    else:
        first = selection

    if not first:
        return

    # If the selection itself is a directory (askdirectory result), use it
    # directly; otherwise take the parent of the first file.
    if os.path.isdir(first):
        _last_used_dir = first
    else:
        parent = os.path.dirname(first)
        if parent:
            _last_used_dir = parent
