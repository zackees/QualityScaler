"""In-app console panel showing live stdout/stderr from app, workers and ffmpeg."""

from __future__ import annotations

from typing import Callable, Sequence

from customtkinter import CTkButton, CTkFrame, CTkLabel, CTkTextbox

from qualityscaler.app.console_log import (
    STREAM_INFO,
    STREAM_STDERR,
    ConsoleLine,
    LineRing,
)
from qualityscaler.gui.widgets import AppFonts

_CONSOLE_BACKGROUND = "#101010"
_HEADER_BACKGROUND = "#181818"
_TEXT_COLORS = {
    STREAM_STDERR: "#FF6B6B",
    STREAM_INFO: "#4DD0E1",
}
_DEFAULT_TEXT_COLOR = "#D0D0D0"


class ConsoleWidget(CTkFrame):

    def __init__(
        self,
        master,
        fonts: AppFonts,
        on_close: Callable[[], None] | None = None,
        max_lines: int = 5000,
        height: int = 180,
    ) -> None:
        super().__init__(master, fg_color=_CONSOLE_BACKGROUND, corner_radius=0, border_width=0, height=height)
        self.pack_propagate(False)

        self._ring = LineRing(max_lines)
        self._autoscroll = True
        self._last_line_replaceable = False

        header = CTkFrame(self, fg_color=_HEADER_BACKGROUND, corner_radius=0, border_width=0, height=26)
        header.pack(side="top", fill="x")

        title = CTkLabel(header, text="Console", font=fonts.bold11, text_color=_DEFAULT_TEXT_COLOR, anchor="w")
        title.pack(side="left", padx=8)

        def make_header_button(text: str, command: Callable[[], None]) -> CTkButton:
            button = CTkButton(
                header,
                text=text,
                command=command,
                width=70,
                height=20,
                font=fonts.bold10,
                corner_radius=1,
                border_width=1,
                fg_color="transparent",
                text_color=_DEFAULT_TEXT_COLOR,
                border_color="#404040",
            )
            button.pack(side="right", padx=3, pady=3)
            return button

        if on_close is not None:
            make_header_button("CLOSE", on_close)
        self._autoscroll_button = make_header_button("SCROLL: ON", self._toggle_autoscroll)
        make_header_button("CLEAR", self.clear)

        self._textbox = CTkTextbox(
            self,
            fg_color=_CONSOLE_BACKGROUND,
            text_color=_DEFAULT_TEXT_COLOR,
            font=("Consolas", 11),
            corner_radius=0,
            border_width=0,
            wrap="none",
            state="disabled",
        )
        self._textbox.pack(side="top", fill="both", expand=True)
        for stream, color in _TEXT_COLORS.items():
            self._textbox.tag_config(stream, foreground=color)

    def _toggle_autoscroll(self) -> None:
        self._autoscroll = not self._autoscroll
        self._autoscroll_button.configure(text="SCROLL: ON" if self._autoscroll else "SCROLL: OFF")

    def append_batch(self, lines: Sequence[ConsoleLine]) -> None:
        if not lines:
            return

        self._textbox.configure(state="normal")
        try:
            for line in lines:
                if line.replace_last and self._last_line_replaceable:
                    self._textbox.delete("end-2l", "end-1l")
                    self._ring.replace_last()
                else:
                    overflow = self._ring.add(1)
                    if overflow > 0:
                        self._textbox.delete("1.0", f"{overflow + 1}.0")

                tags = (line.stream,) if line.stream in _TEXT_COLORS else ()
                self._textbox.insert("end", line.text + "\n", tags)
                self._last_line_replaceable = line.replace_last
        finally:
            self._textbox.configure(state="disabled")

        if self._autoscroll:
            self._textbox.see("end")

    def clear(self) -> None:
        self._textbox.configure(state="normal")
        try:
            self._textbox.delete("1.0", "end")
        finally:
            self._textbox.configure(state="disabled")
        self._ring.clear()
        self._last_line_replaceable = False
