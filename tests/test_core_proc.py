from __future__ import annotations

import sys
import threading
import time

import pytest

from qualityscaler.core import proc
from qualityscaler.core.proc import stream_subprocess

_PRINT_SCRIPT = (
    "import sys; "
    "print('out line 1'); "
    "print('out line 2'); "
    "sys.stderr.write('err line 1\\n')"
)

_SLEEP_SCRIPT = "import time; print('started', flush=True); time.sleep(30)"


def _python_command(script: str) -> list[str]:
    return [sys.executable, "-c", script]


@pytest.fixture(params=["fallback", "running_process"])
def force_backend(request, monkeypatch):
    if request.param == "fallback":
        monkeypatch.setattr(proc, "_use_running_process", lambda: False)
    else:
        if not proc._use_running_process():
            pytest.skip("running_process not installed")
    return request.param


class TestStreamSubprocess:
    def test_captures_stdout_and_stderr_lines(self, force_backend) -> None:
        lines: list[tuple[str, str]] = []

        returncode = stream_subprocess(
            _python_command(_PRINT_SCRIPT),
            on_line=lambda line, stream: lines.append((line, stream)),
        )

        assert returncode == 0
        assert ("out line 1", "stdout") in lines
        assert ("out line 2", "stdout") in lines
        assert ("err line 1", "stderr") in lines

    def test_nonzero_exit_code_is_returned(self, force_backend) -> None:
        returncode = stream_subprocess(_python_command("import sys; sys.exit(3)"))
        assert returncode == 3

    def test_cancel_terminates_process(self, force_backend) -> None:
        cancel = threading.Event()
        lines: list[str] = []

        def on_line(line: str, stream: str) -> None:
            lines.append(line)
            cancel.set()

        start = time.monotonic()
        returncode = stream_subprocess(_python_command(_SLEEP_SCRIPT), on_line=on_line, cancel=cancel)
        elapsed = time.monotonic() - start

        assert "started" in lines
        assert returncode != 0
        assert elapsed < 25

    def test_default_on_line_writes_to_stdio(self, force_backend, capsys) -> None:
        returncode = stream_subprocess(_python_command(_PRINT_SCRIPT))
        assert returncode == 0

        captured = capsys.readouterr()
        assert "out line 1" in captured.out
        assert "err line 1" in captured.err
