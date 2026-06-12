"""Reusable customtkinter widgets and widget factories.

This is the toolkit layer: customtkinter/tkinter imports are confined to this
module and to :mod:`qualityscaler.gui.app`. Widgets are parameterized on
master, fonts and icons instead of reading module globals.
"""

from dataclasses import dataclass
from functools import cache
from os import sep as os_separator
from os.path import basename as os_path_basename
from tkinter import StringVar, DISABLED
from typing import Callable

from PIL.Image import open as pillow_image_open, fromarray as pillow_image_fromarray

from cv2 import (
    CAP_PROP_FPS,
    CAP_PROP_FRAME_COUNT,
    CAP_PROP_FRAME_HEIGHT,
    CAP_PROP_FRAME_WIDTH,
    COLOR_BGR2RGB,
    VideoCapture as opencv_VideoCapture,
    cvtColor as opencv_cvtColor,
    resize as opencv_resize,
)

from customtkinter import (
    CTkButton,
    CTkEntry,
    CTkFont,
    CTkFrame,
    CTkImage,
    CTkLabel,
    CTkOptionMenu,
    CTkScrollableFrame,
    CTkToplevel,
)

from qualityscaler.gui.assets import find_by_relative_path
from qualityscaler.gui.constants import background_color, text_color, widget_background_color
from qualityscaler.gui.media_info import check_if_file_is_video, get_image_resolution, image_read


@dataclass
class AppFonts:
    bold8: CTkFont
    bold9: CTkFont
    bold10: CTkFont
    bold11: CTkFont
    bold12: CTkFont
    bold13: CTkFont
    bold14: CTkFont
    bold16: CTkFont
    bold17: CTkFont
    bold18: CTkFont
    bold19: CTkFont
    bold20: CTkFont
    bold21: CTkFont
    bold22: CTkFont
    bold23: CTkFont
    bold24: CTkFont


@dataclass
class AppIcons:
    logo_git: CTkImage
    logo_telegram: CTkImage
    stop_icon: CTkImage
    upscale_icon: CTkImage
    clear_icon: CTkImage
    info_icon: CTkImage


def load_fonts() -> AppFonts:
    font = "Segoe UI"
    return AppFonts(
        bold8  = CTkFont(family = font, size = 8, weight = "bold"),
        bold9  = CTkFont(family = font, size = 9, weight = "bold"),
        bold10 = CTkFont(family = font, size = 10, weight = "bold"),
        bold11 = CTkFont(family = font, size = 11, weight = "bold"),
        bold12 = CTkFont(family = font, size = 12, weight = "bold"),
        bold13 = CTkFont(family = font, size = 13, weight = "bold"),
        bold14 = CTkFont(family = font, size = 14, weight = "bold"),
        bold16 = CTkFont(family = font, size = 16, weight = "bold"),
        bold17 = CTkFont(family = font, size = 17, weight = "bold"),
        bold18 = CTkFont(family = font, size = 18, weight = "bold"),
        bold19 = CTkFont(family = font, size = 19, weight = "bold"),
        bold20 = CTkFont(family = font, size = 20, weight = "bold"),
        bold21 = CTkFont(family = font, size = 21, weight = "bold"),
        bold22 = CTkFont(family = font, size = 22, weight = "bold"),
        bold23 = CTkFont(family = font, size = 23, weight = "bold"),
        bold24 = CTkFont(family = font, size = 24, weight = "bold"),
    )


def load_icons() -> AppIcons:
    return AppIcons(
        logo_git      = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}github_logo.png")),    size=(18, 18)),
        logo_telegram = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}telegram_logo.png")),  size=(16, 16)),
        stop_icon     = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}stop_icon.png")),      size=(15, 15)),
        upscale_icon  = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}upscale_icon.png")),   size=(15, 15)),
        clear_icon    = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}clear_icon.png")),     size=(15, 15)),
        info_icon     = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}info_icon.png")),      size=(18, 18)),
    )


class MessageBox(CTkToplevel):

    def __init__(
            self,
            messageType: str,
            title: str,
            subtitle: str,
            default_value: str,
            option_list: list,
            fonts: AppFonts,
            ) -> None:

        super().__init__()

        self._running: bool = False

        self._messageType = messageType
        self._title       = title
        self._subtitle    = subtitle
        self._default_value = default_value
        self._option_list   = option_list
        self._fonts         = fonts
        self._ctkwidgets_index = 0

        self.title('')
        self.lift()                          # lift window on top
        self.attributes("-topmost", True)    # stay on top
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        self.after(10, self._create_widgets)  # create widgets with slight delay, to avoid white flickering of background
        self.resizable(False, False)
        self.grab_set()                       # make other windows not clickable

    def _ok_event(
            self,
            event = None
            ) -> None:
        self.grab_release()
        self.destroy()

    def _on_closing(
            self
            ) -> None:
        self.grab_release()
        self.destroy()

    def createEmptyLabel(self) -> CTkLabel:
        return CTkLabel(
            master   = self,
            fg_color = "transparent",
            width    = 500,
            height   = 17,
            text     = ''
        )

    def placeInfoMessageTitleSubtitle(self) -> None:

        spacingLabel1 = self.createEmptyLabel()
        spacingLabel2 = self.createEmptyLabel()

        if self._messageType == "info":
            title_subtitle_text_color = "#3399FF"
        elif self._messageType == "error":
            title_subtitle_text_color = "#FF3131"

        titleLabel = CTkLabel(
            master     = self,
            width      = 500,
            anchor     = 'w',
            justify    = "left",
            fg_color   = "transparent",
            text_color = title_subtitle_text_color,
            font       = self._fonts.bold22,
            text       = self._title
            )

        if self._default_value is not None:
            defaultLabel = CTkLabel(
                master     = self,
                width      = 500,
                anchor     = 'w',
                justify    = "left",
                fg_color   = "transparent",
                text_color = "#3399FF",
                font       = self._fonts.bold17,
                text       = f"Default: {self._default_value}"
                )

        subtitleLabel = CTkLabel(
            master     = self,
            width      = 500,
            anchor     = 'w',
            justify    = "left",
            fg_color   = "transparent",
            text_color = title_subtitle_text_color,
            font       = self._fonts.bold14,
            text       = self._subtitle
            )

        spacingLabel1.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 0, pady = 0, sticky = "ew")

        self._ctkwidgets_index += 1
        titleLabel.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 25, pady = 0, sticky = "ew")

        if self._default_value is not None:
            self._ctkwidgets_index += 1
            defaultLabel.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 25, pady = 0, sticky = "ew")

        self._ctkwidgets_index += 1
        subtitleLabel.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 25, pady = 0, sticky = "ew")

        self._ctkwidgets_index += 1
        spacingLabel2.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 0, pady = 0, sticky = "ew")

    def placeInfoMessageOptionsText(self) -> None:

        for option_text in self._option_list:
            optionLabel = CTkLabel(
                master        = self,
                width         = 600,
                height        = 45,
                anchor        = 'w',
                justify       = "left",
                text_color    = text_color,
                fg_color      = "#282828",
                bg_color      = "transparent",
                font          = self._fonts.bold13,
                text          = option_text,
                corner_radius = 10,
            )

            self._ctkwidgets_index += 1
            optionLabel.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 25, pady = 4, sticky = "ew")

        spacingLabel3 = self.createEmptyLabel()

        self._ctkwidgets_index += 1
        spacingLabel3.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 0, pady = 0, sticky = "ew")

    def placeInfoMessageOkButton(
            self
            ) -> None:

        ok_button = CTkButton(
            master  = self,
            command = self._ok_event,
            text    = 'OK',
            width   = 125,
            font         = self._fonts.bold11,
            border_width = 1,
            fg_color     = "#282828",
            text_color   = "#E0E0E0",
            border_color = "#0096FF"
        )

        self._ctkwidgets_index += 1
        ok_button.grid(row = self._ctkwidgets_index, column = 1, columnspan = 1, padx = (10, 20), pady = (10, 20), sticky = "e")

    def _create_widgets(
            self
            ) -> None:

        self.grid_columnconfigure((0, 1), weight=1)
        self.rowconfigure(0, weight=1)

        self.placeInfoMessageTitleSubtitle()
        self.placeInfoMessageOptionsText()
        self.placeInfoMessageOkButton()


@cache
def extract_file_icon(file_path) -> CTkImage:
    max_size = 60

    if check_if_file_is_video(file_path):
        video_cap   = opencv_VideoCapture(file_path)
        _, frame    = video_cap.read()
        source_icon = opencv_cvtColor(frame, COLOR_BGR2RGB)
        video_cap.release()
    else:
        source_icon = opencv_cvtColor(image_read(file_path), COLOR_BGR2RGB)

    ratio       = min(max_size / source_icon.shape[0], max_size / source_icon.shape[1])
    new_width   = int(source_icon.shape[1] * ratio)
    new_height  = int(source_icon.shape[0] * ratio)
    source_icon = opencv_resize(source_icon, (new_width, new_height))
    ctk_icon    = CTkImage(pillow_image_fromarray(source_icon, mode="RGB"), size = (new_width, new_height))

    return ctk_icon


class FileWidget(CTkScrollableFrame):

    def __init__(
            self,
            master,
            selected_file_list,
            fonts: AppFonts,
            clear_icon: CTkImage,
            on_clean: Callable,
            upscale_factor       = 1,
            input_resize_factor  = 0,
            output_resize_factor = 0,
            **kwargs
            ) -> None:

        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight = 1)

        self.file_list            = selected_file_list
        self.upscale_factor       = upscale_factor
        self.input_resize_factor  = input_resize_factor
        self.output_resize_factor = output_resize_factor

        self._fonts      = fonts
        self._clear_icon = clear_icon
        self._on_clean   = on_clean

        self.index_row = 1
        self.ui_components = []
        self._create_widgets()

    def _destroy_(self) -> None:
        self.file_list = []
        self.destroy()
        self._on_clean()

    def _create_widgets(self) -> None:
        self.add_clean_button()
        for file_path in self.file_list:
            file_name_label, file_info_label = self.get_file_information(file_path)
            self.ui_components.append(file_name_label)
            self.ui_components.append(file_info_label)

    def get_file_information(self, file_path) -> tuple:
        infos, icon = self.extract_file_info(file_path)

        # File name
        file_name_label = CTkLabel(
            self,
            text       = os_path_basename(file_path),
            font       = self._fonts.bold13,
            text_color = text_color,
            compound   = "left",
            anchor     = "w",
            padx       = 10,
            pady       = 5,
            justify    = "left",
        )
        file_name_label.grid(
            row    = self.index_row,
            column = 0,
            pady   = (0, 2),
            padx   = (3, 3),
            sticky = "w"
        )

        # File infos and icon
        file_info_label = CTkLabel(
            self,
            text       = infos,
            image      = icon,
            font       = self._fonts.bold12,
            text_color = text_color,
            compound   = "left",
            anchor     = "w",
            padx       = 10,
            pady       = 5,
            justify    = "left",
        )
        file_info_label.grid(
            row    = self.index_row + 1,
            column = 0,
            pady   = (0, 15),
            padx   = (3, 3),
            sticky = "w"
        )

        self.index_row += 2

        return file_name_label, file_info_label

    def add_clean_button(self) -> None:

        button = CTkButton(
            master        = self,
            command       = self._destroy_,
            text          = "CLEAN",
            image         = self._clear_icon,
            width         = 90,
            height        = 28,
            font          = self._fonts.bold11,
            border_width  = 1,
            corner_radius = 1,
            fg_color      = "#282828",
            text_color    = "#E0E0E0",
            border_color  = "#0096FF"
        )

        button.grid(row = 0, column=2, pady=(7, 7), padx = (0, 7))

    def extract_file_info(self, file_path) -> tuple:

        if check_if_file_is_video(file_path):
            cap          = opencv_VideoCapture(file_path)
            width        = round(cap.get(CAP_PROP_FRAME_WIDTH))
            height       = round(cap.get(CAP_PROP_FRAME_HEIGHT))
            num_frames   = int(cap.get(CAP_PROP_FRAME_COUNT))
            frame_rate   = cap.get(CAP_PROP_FPS)
            duration     = num_frames/frame_rate
            minutes      = int(duration/60)
            seconds      = duration % 60
            cap.release()

            file_icon  = extract_file_icon(file_path)
            file_infos = f"{minutes}m:{round(seconds)}s - {num_frames}frames - {width}x{height} \n"
        else:
            height, width = get_image_resolution(image_read(file_path))
            file_icon     = extract_file_icon(file_path)

            file_infos = f"{width}x{height}\n"

        if self.input_resize_factor != 0 and self.output_resize_factor != 0 and self.upscale_factor != 0 :
            input_resized_height = int(height * (self.input_resize_factor/100))
            input_resized_width  = int(width * (self.input_resize_factor/100))

            upscaled_height = int(input_resized_height * self.upscale_factor)
            upscaled_width  = int(input_resized_width * self.upscale_factor)

            output_resized_height = int(upscaled_height * (self.output_resize_factor/100))
            output_resized_width  = int(upscaled_width * (self.output_resize_factor/100))

            label_in  = f"AI input ({self.input_resize_factor}%)"
            label_ups = f"AI output (x{self.upscale_factor})"
            label_out = f"File output ({self.output_resize_factor}%)"

            file_infos += (
                f"{label_in}\t= {input_resized_width}x{input_resized_height}\n"
                f"{label_ups}\t= {upscaled_width}x{upscaled_height}\n"
                f"{label_out}\t= {output_resized_width}x{output_resized_height}"
            )

        return file_infos, file_icon

    # EXTERNAL FUNCTIONS

    def clean_file_list(self) -> None:
        self.index_row = 1
        for ui_component in self.ui_components:
            ui_component.grid_forget()

    def get_selected_file_list(self) -> list:
        return self.file_list

    def set_upscale_factor(self, upscale_factor) -> None:
        self.upscale_factor = upscale_factor

    def set_input_resize_factor(self, input_resize_factor) -> None:
        self.input_resize_factor = input_resize_factor

    def set_output_resize_factor(self, output_resize_factor) -> None:
        self.output_resize_factor = output_resize_factor


def create_option_background(master) -> CTkFrame:
    return CTkFrame(
        master   = master,
        bg_color = background_color,
        fg_color = widget_background_color,
        height   = 46,
        corner_radius = 10
    )

def create_info_button(
        master,
        fonts:   AppFonts,
        command: Callable,
        text:    str,
        width:   int = 200
    ) -> CTkFrame:

    frame = CTkFrame(
        master   = master,
        fg_color = widget_background_color,
        height   = 25
    )

    button = CTkButton(
        master        = frame,
        command       = command,
        font          = fonts.bold12,
        text          = "?",
        border_color  = "#0096FF",
        border_width  = 1,
        fg_color      = widget_background_color,
        hover_color   = background_color,
        width         = 23,
        height        = 15,
        corner_radius = 1
    )
    button.grid(row=0, column=0, padx=(0, 7), pady=2, sticky="w")

    label = CTkLabel(
        master     = frame,
        text       = text,
        width      = width,
        height     = 22,
        fg_color   = "transparent",
        bg_color   = widget_background_color,
        text_color = text_color,
        font       = fonts.bold13,
        anchor     = "w"
    )
    label.grid(row=0, column=1, sticky="w")

    frame.grid_propagate(False)
    frame.grid_columnconfigure(1, weight=1)

    return frame

def create_option_menu(
        master,
        fonts:         AppFonts,
        command:       Callable,
        values:        list,
        default_value: str,
        border_color:  str = "#404040",
        border_width:  int = 1,
        width:         int = 159,
        height:        int = 26
    ) -> CTkFrame:

    total_width  = (width + 2 * border_width)
    total_height = (height + 2 * border_width)

    frame = CTkFrame(
        master        = master,
        fg_color      = border_color,
        width         = total_width,
        height        = total_height,
        border_width  = 0,
        corner_radius = 1,
    )

    option_menu = CTkOptionMenu(
        master             = frame,
        command            = command,
        values             = values,
        width              = width,
        height             = height,
        corner_radius      = 0,
        dropdown_font      = fonts.bold12,
        font               = fonts.bold11,
        anchor             = "center",
        text_color         = text_color,
        fg_color           = background_color,
        button_color       = background_color,
        button_hover_color = background_color,
        dropdown_fg_color  = background_color
    )

    option_menu.place(x = (total_width - width) / 2, y = (total_height - height) / 2)
    option_menu.set(default_value)
    return frame

def create_text_box(
        master,
        fonts:        AppFonts,
        textvariable: StringVar,
        width:        int,
        height:       int = 26
    ) -> CTkEntry:

    return CTkEntry(
        master        = master,
        textvariable  = textvariable,
        corner_radius = 1,
        width         = width,
        height        = height,
        font          = fonts.bold11,
        justify       = "center",
        text_color    = text_color,
        fg_color      = "#000000",
        border_width  = 1,
        border_color  = "#404040",
    )

def create_text_box_output_path(
        master,
        fonts:        AppFonts,
        textvariable: StringVar,
        height:       int = 26
    ) -> CTkEntry:

    return CTkEntry(
        master        = master,
        textvariable  = textvariable,
        corner_radius = 1,
        width         = 250,
        height        = height,
        font          = fonts.bold11,
        justify       = "center",
        text_color    = text_color,
        fg_color      = "#000000",
        border_width  = 1,
        border_color  = "#404040",
        state         = DISABLED
    )

def create_active_button(
        master,
        fonts:        AppFonts,
        command:      Callable,
        text:         str,
        icon:         CTkImage,
        width:        int = 140,
        height:       int = 30,
        border_color: str = "#0096FF"
    ) -> CTkButton:

    return CTkButton(
        master        = master,
        command       = command,
        text          = text,
        image         = icon,
        width         = width,
        height        = height,
        font          = fonts.bold11,
        border_width  = 1,
        corner_radius = 1,
        fg_color      = "#282828",
        text_color    = "#E0E0E0",
        border_color  = border_color
    )

def create_link_button(
        master,
        fonts:   AppFonts,
        command: Callable,
        icon:    CTkImage,
    ) -> CTkButton:

    return CTkButton(
        master        = master,
        command       = command,
        image         = icon,
        width         = 30,
        height        = 30,
        border_width  = 1,
        corner_radius = 1,
        fg_color      = "transparent",
        text_color    = text_color,
        border_color  = "#0096FF",
        anchor        = "center",
        text          = "",
        font          = fonts.bold11
    )
