
# Standard library imports
import sys
from functools  import cache
from time       import sleep
from webbrowser import open as open_browser
from shutil     import unpack_archive as shutil_unpack_archive

from typing    import Callable
from threading import (
    Thread,
    Event as threading_Event
)
from queue import Empty, Full
from multiprocessing import (
    Process        as multiprocessing_Process,
    Manager        as multiprocessing_Manager,
    freeze_support as multiprocessing_freeze_support
)

from json import (
    load  as json_load,
    dumps as json_dumps
)

from os import (
    sep     as os_separator,
    devnull as os_devnull
)

from os.path import (
    basename   as os_path_basename,
    dirname    as os_path_dirname,
    abspath    as os_path_abspath,
    join       as os_path_join,
    exists     as os_path_exists,
    expanduser as os_path_expanduser
)

# Third-party library imports
from download import download

from PIL.Image import (
    open      as pillow_image_open,
    fromarray as pillow_image_fromarray
)

from cv2 import (
    CAP_PROP_FPS,
    CAP_PROP_FRAME_COUNT,
    CAP_PROP_FRAME_HEIGHT,
    CAP_PROP_FRAME_WIDTH,
    COLOR_BGR2RGB,
    IMREAD_UNCHANGED,
    VideoCapture as opencv_VideoCapture,
    cvtColor     as opencv_cvtColor,
    imdecode     as opencv_imdecode,
    resize       as opencv_resize,
)

from numpy import (
    frombuffer as numpy_frombuffer,
    ndarray    as numpy_ndarray,
    uint8
)

# First-party imports (headless pipeline contract)
from qualityscaler.core import (
    UpscaleSettings,
    UpscaleEvent,
    UpscaleProgress,
    UpscaleCompleted,
    UpscaleError,
    UpscaleStopped,
    run_pipeline,
    app_version,
)

# GUI imports
from tkinter import StringVar
from tkinter import DISABLED
from customtkinter import (
    CTk,
    CTkFrame,
    CTkButton,
    CTkEntry,
    CTkFont,
    CTkImage,
    CTkLabel,
    CTkOptionMenu,
    CTkScrollableFrame,
    CTkToplevel,
    CTkCanvas,
    filedialog,
    set_appearance_mode,
    set_default_color_theme,
    set_widget_scaling,
    set_window_scaling
)

if sys.stdout is None: sys.stdout = open(os_devnull, "w", encoding="utf-8", errors="replace")
else:                  sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if sys.stderr is None: sys.stderr = open(os_devnull, "w", encoding="utf-8", errors="replace")
else:                  sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def find_by_relative_path(relative_path: str) -> str:
    base_path = getattr(sys, '_MEIPASS', os_path_dirname(os_path_abspath(__file__)))
    return os_path_join(base_path, relative_path)


HERE = os_path_dirname(os_path_abspath(__file__))


app_name   = "QualityScaler"
version    = app_version()
githubme   = "https://github.com/Djdefrag/QualityScaler/releases"
telegramme = "https://linktr.ee/j3ngystudio"

app_name_color          = "#F274EE"
background_color        = "#000000"
widget_background_color = "#181818"
text_color              = "#B8B8B8"


VRAM_model_usage = {
    'LVAx2':           2,
    'RealESR_Gx4':     2.5,
    'RealESR_Ax4':     2.5,
    'BSRGANx2':        0.8,
    'BSRGANx4':        0.75,
    'RealESRGANx4':    0.75,
    'MSharpx4':        1.5,
    'IRCNN_Mx1':       4,
    'IRCNN_Lx1':       4,
}

MENU_LIST_SEPARATOR = [ "----" ]
LVA_models        = [ "LVAx2"                      ]
RealESR_models    = [ "RealESR_Gx4", "RealESR_Ax4" ]
BSRGAN_models     = [ "BSRGANx2",    "BSRGANx4"    ]
RealESRGAN_models = [ "RealESRGANx4"               ]
MSharp_models     = [ "MSharpx4"                   ]
IRCNN_models      = [ "IRCNN_Mx1",   "IRCNN_Lx1"   ]

AI_models_list = (
    LVA_models          + MENU_LIST_SEPARATOR +
    RealESR_models      + MENU_LIST_SEPARATOR +
    BSRGAN_models       + MENU_LIST_SEPARATOR +
    RealESRGAN_models   + MENU_LIST_SEPARATOR +
    MSharp_models       + MENU_LIST_SEPARATOR +
    IRCNN_models
)

zoom_option_list       = [ "50%", "75%", "100%", "125%", "150%", "175%" ]
AI_multithreading_list = [ "OFF", "2 threads", "4 threads", "6 threads", "8 threads"]
blending_list          = [ "OFF", "Low", "Medium", "High" ]
gpus_list              = [ "Auto", "GPU 1", "GPU 2", "GPU 3", "GPU 4" ]
keep_frames_list       = [ "OFF", "ON" ]
image_extension_list   = [ ".png", ".jpg", ".bmp", ".tiff" ]
video_extension_list   = [ ".mp4", ".mkv", ".avi", ".mov" ]
video_codec_list = [
    "x264",       "x265",       MENU_LIST_SEPARATOR[0],
    "h264_nvenc", "hevc_nvenc", MENU_LIST_SEPARATOR[0],
    "h264_amf",   "hevc_amf",   MENU_LIST_SEPARATOR[0],
    "h264_qsv",   "hevc_qsv",
    ]
video_quality_list     = [ "LOW", "MEDIUM", "HIGH" ]

OUTPUT_PATH_CODED    = "Same path as input files"
DOCUMENT_PATH        = os_path_join(os_path_expanduser('~'), 'Documents')
USER_PREFERENCE_PATH = find_by_relative_path(f"{DOCUMENT_PATH}{os_separator}{app_name}_{version}_userpreference.json")

# Install Assets -------------------

ASSETS_ZIP_URL    = "https://github.com/zackees/QualityScaler/raw/main/assets.zip"
ASSETS_TARGET_DIR = os_path_join(HERE, "Assets")
ASSETS_TARGET_ZIP = os_path_join(HERE, "assets.zip")
if not os_path_exists(ASSETS_TARGET_DIR):
    download(ASSETS_ZIP_URL, ASSETS_TARGET_ZIP, replace = True, kind = "file", timeout=60 * 5)
    shutil_unpack_archive(ASSETS_TARGET_ZIP, ASSETS_TARGET_DIR)

CLOSE_APP_STATUS = "CloseApp"


offset_y_options = 0.0825
row0  = 0.05
row1  = 0.125
row2  = row1 + offset_y_options
row3  = row2 + offset_y_options
row4  = row3 + offset_y_options
row5  = row4 + offset_y_options
row6  = row5 + offset_y_options
row7  = row6 + offset_y_options
row8  = row7 + offset_y_options
row9  = row8 + offset_y_options
row10 = row9 + offset_y_options
row11 = row10 + offset_y_options

column_offset = 0.2
column_info1  = 0.625
column_info2  = 0.858
column_1      = 0.66
column_2      = column_1 + column_offset
column_1_5    = column_info1 + 0.08
column_1_4    = column_1_5 - 0.0127
column_3      = column_info2 + 0.08
column_2_9    = column_3 - 0.0127
column_3_5    = column_2 + 0.0355

little_textbox_width = 74
little_menu_width = 98



supported_file_extensions = [
    '.heic', '.jpg', '.jpeg', '.JPG', '.JPEG', '.png',
    '.PNG', '.webp', '.WEBP', '.bmp', '.BMP', '.tif',
    '.tiff', '.TIF', '.TIFF', '.mp4', '.MP4', '.webm',
    '.WEBM', '.mkv', '.MKV', '.flv', '.FLV', '.gif',
    '.GIF', '.m4v', ',M4V', '.avi', '.AVI', '.mov',
    '.MOV', '.qt', '.3gp', '.mpg', '.mpeg', ".vob"
]

supported_video_extensions = [
    '.mp4', '.MP4', '.webm', '.WEBM', '.mkv', '.MKV',
    '.flv', '.FLV', '.gif', '.GIF', '.m4v', ',M4V',
    '.avi', '.AVI', '.mov', '.MOV', '.qt', '.3gp',
    '.mpg', '.mpeg', ".vob"
]



# GUI utils ---------------------------

class MessageBox(CTkToplevel):

    def __init__(
            self,
            messageType: str,
            title: str,
            subtitle: str,
            default_value: str,
            option_list: list,
            ) -> None:

        super().__init__()

        self._running: bool = False

        self._messageType = messageType
        self._title       = title
        self._subtitle    = subtitle
        self._default_value = default_value
        self._option_list   = option_list
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
            font       = bold22,
            text       = self._title
            )

        if self._default_value != None:
            defaultLabel = CTkLabel(
                master     = self,
                width      = 500,
                anchor     = 'w',
                justify    = "left",
                fg_color   = "transparent",
                text_color = "#3399FF",
                font       = bold17,
                text       = f"Default: {self._default_value}"
                )

        subtitleLabel = CTkLabel(
            master     = self,
            width      = 500,
            anchor     = 'w',
            justify    = "left",
            fg_color   = "transparent",
            text_color = title_subtitle_text_color,
            font       = bold14,
            text       = self._subtitle
            )

        spacingLabel1.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 0, pady = 0, sticky = "ew")

        self._ctkwidgets_index += 1
        titleLabel.grid(row = self._ctkwidgets_index, column = 0, columnspan = 2, padx = 25, pady = 0, sticky = "ew")

        if self._default_value != None:
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
                font          = bold13,
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
            font         = bold11,
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

class FileWidget(CTkScrollableFrame):

    def __init__(
            self,
            master,
            selected_file_list,
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

        self.index_row = 1
        self.ui_components = []
        self._create_widgets()

    def _destroy_(self) -> None:
        self.file_list = []
        self.destroy()
        place_loadFile_section()

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
            font       = bold13,
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
            font       = bold12,
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
            image         = clear_icon,
            width         = 90,
            height        = 28,
            font          = bold11,
            border_width  = 1,
            corner_radius = 1,
            fg_color      = "#282828",
            text_color    = "#E0E0E0",
            border_color  = "#0096FF"
        )

        button.grid(row = 0, column=2, pady=(7, 7), padx = (0, 7))




    @cache
    def extract_file_icon(self, file_path) -> CTkImage:
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
        source_icon = opencv_resize(source_icon,(new_width, new_height))
        ctk_icon    = CTkImage(pillow_image_fromarray(source_icon, mode="RGB"), size = (new_width, new_height))

        return ctk_icon

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

            file_icon  = self.extract_file_icon(file_path)
            file_infos = f"{minutes}m:{round(seconds)}s - {num_frames}frames - {width}x{height} \n"

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

        else:
            height, width = get_image_resolution(image_read(file_path))
            file_icon     = self.extract_file_icon(file_path)

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
        for ui_component in self.ui_components: ui_component.grid_forget()

    def get_selected_file_list(self) -> list:
        return self.file_list

    def set_upscale_factor(self, upscale_factor) -> None:
        self.upscale_factor = upscale_factor

    def set_input_resize_factor(self, input_resize_factor) -> None:
        self.input_resize_factor = input_resize_factor

    def set_output_resize_factor(self, output_resize_factor) -> None:
        self.output_resize_factor = output_resize_factor

def get_values_for_file_widget() -> tuple:
    # Upscale factor
    upscale_factor = get_upscale_factor()

    # Input resolution %
    try:
        input_resize_factor = int(float(str(selected_input_resize_factor.get())))
    except:
        input_resize_factor = 0

    # Output resolution %
    try:
        output_resize_factor = int(float(str(selected_output_resize_factor.get())))
    except:
        output_resize_factor = 0

    return upscale_factor, input_resize_factor, output_resize_factor

def update_file_widget(a, b, c) -> None:
    try:
        global file_widget
        file_widget
    except:
        return

    upscale_factor, input_resize_factor, output_resize_factor = get_values_for_file_widget()

    file_widget.clean_file_list()
    file_widget.set_upscale_factor(upscale_factor)
    file_widget.set_input_resize_factor(input_resize_factor)
    file_widget.set_output_resize_factor(output_resize_factor)
    file_widget._create_widgets()

def create_option_background() -> CTkFrame:
    return CTkFrame(
        master   = window,
        bg_color = background_color,
        fg_color = widget_background_color,
        height   = 46,
        corner_radius = 10
    )

def create_info_button(
        command: Callable,
        text:    str,
        width:   int = 200
    ) -> CTkFrame:

    frame = CTkFrame(
        master   = window,
        fg_color = widget_background_color,
        height   = 25
    )

    button = CTkButton(
        master        = frame,
        command       = command,
        font          = bold12,
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
        font       = bold13,
        anchor     = "w"
    )
    label.grid(row=0, column=1, sticky="w")

    frame.grid_propagate(False)
    frame.grid_columnconfigure(1, weight=1)

    return frame

def create_option_menu(
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
        master        = window,
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
        dropdown_font      = bold12,
        font               = bold11,
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
        textvariable: StringVar,
        width:        int,
        height:       int = 26
    ) -> CTkEntry:

    return CTkEntry(
        master        = window,
        textvariable  = textvariable,
        corner_radius = 1,
        width         = width,
        height        = height,
        font          = bold11,
        justify       = "center",
        text_color    = text_color,
        fg_color      = "#000000",
        border_width  = 1,
        border_color  = "#404040",
    )

def create_text_box_output_path(
        textvariable: StringVar,
        height:       int = 26
    ) -> CTkEntry:

    return CTkEntry(
        master        = window,
        textvariable  = textvariable,
        corner_radius = 1,
        width         = 250,
        height        = height,
        font          = bold11,
        justify       = "center",
        text_color    = text_color,
        fg_color      = "#000000",
        border_width  = 1,
        border_color  = "#404040",
        state         = DISABLED
    )

def create_active_button(
        command:      Callable,
        text:         str,
        icon:         CTkImage,
        width:        int = 140,
        height:       int = 30,
        border_color: str = "#0096FF"
    ) -> CTkButton:

    return CTkButton(
        master        = window,
        command       = command,
        text          = text,
        image         = icon,
        width         = width,
        height        = height,
        font          = bold11,
        border_width  = 1,
        corner_radius = 1,
        fg_color      = "#282828",
        text_color    = "#E0E0E0",
        border_color  = border_color
    )

def create_link_button(
        command: Callable,
        icon:    CTkImage,
    ) -> CTkButton:

    return CTkButton(
        master        = window,
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
        font          = bold11
    )



# File Utils functions ------------------------

def image_read(file_path: str) -> numpy_ndarray:
    with open(file_path, 'rb') as file:
        return opencv_imdecode(
            numpy_frombuffer(file.read(), uint8),
            IMREAD_UNCHANGED
        )

def check_if_file_is_video(file: str) -> bool:
    return any(video_extension in file for video_extension in supported_video_extensions)

# Image/video Utils functions ------------------------

def get_image_resolution(image: numpy_ndarray) -> tuple:
    # Return height x width
    return image.shape[0], image.shape[1]

# Core functions ------------------------

def _format_progress_event(event: UpscaleProgress) -> str:
    message = event.message
    if event.file_index > 0:
        message = f"{event.file_index}. {message}"
    if event.fraction is not None:
        message = f"{message} {int(event.fraction * 100)}%"
    return message

def check_upscale_steps() -> None:
    sleep(1)

    while True:
        actual_event = process_status_q.get()
        print(f"[{app_name}] check_upscale_steps - {actual_event}")

        if actual_event == CLOSE_APP_STATUS:
            break

        elif isinstance(actual_event, UpscaleStopped):
            info_message.set(f"Upscaling stopped")
            place_upscale_button()
            break

        elif isinstance(actual_event, UpscaleCompleted):
            info_message.set(f"All files completed! :)")
            stop_upscale_process()
            place_upscale_button()
            break

        elif isinstance(actual_event, UpscaleError):
            info_message.set(f"Error while upscaling :(")
            show_error_message(actual_event.message)
            stop_upscale_process()
            place_upscale_button()
            break

        elif isinstance(actual_event, UpscaleProgress):
            info_message.set(_format_progress_event(actual_event))

        else:
            info_message.set(str(actual_event))

        sleep(1)

def write_process_status(
        process_status_q,
        status: object
        ) -> None:

    while not process_status_q.empty(): process_status_q.get()
    process_status_q.put(status)

def stop_upscale_process() -> None:
    global process_upscale_orchestrator

    print(f"[{app_name}] stop_upscale_process - setting upscale process stop event")
    event_stop_upscale_process.set()

    sleep(1)

    try:
        process_upscale_orchestrator
    except:
        pass
    else:
        print(f"[{app_name}] stop_upscale_process - waiting for upscale orchestrator to terminate")
        process_upscale_orchestrator.kill()
        print(f"[{app_name}] stop_upscale_process - upscale orchestrator terminated")

    event_stop_upscale_process.clear()

def stop_button_command() -> None:
    write_process_status(process_status_q, UpscaleStopped())
    stop_upscale_process()

# PIPELINE SUBPROCESS

def _pipeline_process_main(
        event_q,
        stop_mp_event,
        settings: UpscaleSettings
        ) -> None:

    cancel_threading_event = threading_Event()

    def watch_stop_event() -> None:
        while not cancel_threading_event.is_set():
            if stop_mp_event.is_set():
                cancel_threading_event.set()
                break
            sleep(0.25)

    Thread(target = watch_stop_event, daemon = True).start()

    def emit_event(event: UpscaleEvent) -> None:
        # Keep only the freshest event so the pipeline never blocks on the GUI
        while not event_q.empty():
            try: event_q.get_nowait()
            except Empty: break
        try: event_q.put_nowait(event)
        except Full: pass

    def emit_terminal_event(event: UpscaleEvent) -> None:
        while not event_q.empty():
            try: event_q.get_nowait()
            except Empty: break
        event_q.put(event)

    try:
        output_paths = run_pipeline(settings, emit = emit_event, cancel = cancel_threading_event)
    except Exception as exception:
        if cancel_threading_event.is_set() or stop_mp_event.is_set():
            emit_terminal_event(UpscaleStopped())
        else:
            emit_terminal_event(UpscaleError(str(exception)))
    else:
        if cancel_threading_event.is_set() or stop_mp_event.is_set():
            emit_terminal_event(UpscaleStopped())
        else:
            emit_terminal_event(UpscaleCompleted(tuple(output_paths)))

# ORCHESTRATOR

def upscale_button_command() -> None:
    global selected_file_list
    global selected_AI_model
    global selected_gpu
    global selected_keep_frames
    global selected_AI_multithreading
    global selected_blending_factor
    global selected_image_extension
    global selected_video_extension
    global selected_video_codec
    global selected_video_quality
    global tiles_resolution
    global input_resize_factor
    global output_resize_factor

    global process_upscale_orchestrator

    if user_input_checks():
        info_message.set("Loading")

        selected_output_path_value = selected_output_path.get()
        blending_name = {0: "OFF", 0.3: "Low", 0.5: "Medium", 0.7: "High"}.get(selected_blending_factor, "OFF")

        settings = UpscaleSettings(
            input_paths          = list(selected_file_list),
            output_path          = None if selected_output_path_value == OUTPUT_PATH_CODED else selected_output_path_value,
            ai_model             = selected_AI_model,
            gpu                  = selected_gpu,
            vram_gb              = float(str(selected_VRAM_limiter.get())),
            multithreading       = selected_AI_multithreading,
            input_resize_factor  = input_resize_factor,
            output_resize_factor = output_resize_factor,
            blending             = blending_name,
            keep_frames          = selected_keep_frames,
            image_extension      = selected_image_extension,
            video_extension      = selected_video_extension,
            video_codec          = selected_video_codec,
            video_quality        = selected_video_quality,
        )

        try:
            settings.validate()
        except ValueError as error:
            info_message.set(str(error))
            return

        print("=" * 50)
        print("> Starting upscale:")
        print(f"    Files to upscale: {len(settings.input_paths)}")
        print(f"    Output path: {selected_output_path_value}")
        print(f"    Selected AI model: {settings.ai_model}")
        print(f"    Blending: {settings.blending}")
        print(f"    AI multithreading: {settings.multithreading}")
        print(f"    Selected GPU: {settings.gpu}")
        print(f"    Tiles resolution for selected GPU VRAM: {settings.tiles_resolution}x{settings.tiles_resolution}px")
        print(f"    Selected image output extension: {settings.image_extension}")
        print(f"    Selected video output extension: {settings.video_extension}")
        print(f"    Selected video output codec: {settings.video_codec}")
        print(f"    Input resize factor: {int(settings.input_resize_factor * 100)}%")
        print(f"    Output resize factor: {int(settings.output_resize_factor * 100)}%")
        print(f"    Save frames: {settings.keep_frames}")
        print("=" * 50)

        place_stop_button()

        event_stop_upscale_process.clear()
        while not process_status_q.empty(): process_status_q.get_nowait()

        process_upscale_orchestrator = multiprocessing_Process(
            target = _pipeline_process_main,
            args   = (process_status_q, event_stop_upscale_process, settings)
        )
        process_upscale_orchestrator.start()

        Thread(target = check_upscale_steps).start()



# GUI functions ---------------------------

def apply_app_zoom(zoom: float) -> None:
    set_window_scaling(zoom)
    set_widget_scaling(zoom)

def user_input_checks() -> bool:
    global selected_file_list
    global selected_AI_model
    global selected_image_extension
    global tiles_resolution
    global input_resize_factor
    global output_resize_factor

    # Selected files
    try: selected_file_list = file_widget.get_selected_file_list()
    except:
        info_message.set("Please select a file")
        return False

    if len(selected_file_list) <= 0:
        info_message.set("Please select a file")
        return False


    # AI model
    if selected_AI_model == MENU_LIST_SEPARATOR[0]:
        info_message.set("Please select the AI model")
        return False


    # Input resize factor
    try: input_resize_factor = int(float(str(selected_input_resize_factor.get())))
    except:
        info_message.set("Input resolution % must be a number")
        return False

    if input_resize_factor > 0: input_resize_factor = input_resize_factor/100
    else:
        info_message.set("Input resolution % must be a value > 0")
        return False


    # Output resize factor
    try: output_resize_factor = int(float(str(selected_output_resize_factor.get())))
    except:
        info_message.set("Output resolution % must be a number")
        return False

    if output_resize_factor > 0: output_resize_factor = output_resize_factor/100
    else:
        info_message.set("Output resolution % must be a value > 0")
        return False


    # VRAM limiter
    try: tiles_resolution = 100 * int(float(str(selected_VRAM_limiter.get())))
    except:
        info_message.set("GPU VRAM value must be a number")
        return False

    if tiles_resolution > 0:
        vram_multiplier = VRAM_model_usage.get(selected_AI_model)

        selected_vram = (vram_multiplier * int(float(str(selected_VRAM_limiter.get()))))
        tiles_resolution = int(selected_vram * 100)
    else:
        info_message.set("GPU VRAM value must be a value > 0")
        return False

    return True

def show_error_message(exception: str) -> None:
    messageBox_title    = "Upscale error"
    messageBox_subtitle = "Please report the error on Github or Telegram"
    messageBox_text     = f"\n {str(exception)} \n"

    MessageBox(
        messageType   = "error",
        title         = messageBox_title,
        subtitle      = messageBox_subtitle,
        default_value = None,
        option_list   = [messageBox_text]
    )

def get_upscale_factor() -> int:
    global selected_AI_model
    if MENU_LIST_SEPARATOR[0] in selected_AI_model: upscale_factor = 0
    elif 'x1' in selected_AI_model: upscale_factor = 1
    elif 'x2' in selected_AI_model: upscale_factor = 2
    elif 'x3' in selected_AI_model: upscale_factor = 3
    elif 'x4' in selected_AI_model: upscale_factor = 4

    return upscale_factor

def open_files_action():

    def check_supported_selected_files(uploaded_file_list: list) -> list:
        return [file for file in uploaded_file_list if any(supported_extension in file for supported_extension in supported_file_extensions)]

    info_message.set("Selecting files")

    uploaded_files_list    = list(filedialog.askopenfilenames())
    uploaded_files_counter = len(uploaded_files_list)

    supported_files_list    = check_supported_selected_files(uploaded_files_list)
    supported_files_counter = len(supported_files_list)

    print("> Uploaded files: " + str(uploaded_files_counter) + " => Supported files: " + str(supported_files_counter))

    if supported_files_counter > 0:

        upscale_factor, input_resize_factor, output_resize_factor = get_values_for_file_widget()

        global file_widget
        file_widget = FileWidget(
            master               = window,
            selected_file_list   = supported_files_list,
            upscale_factor       = upscale_factor,
            input_resize_factor  = input_resize_factor,
            output_resize_factor = output_resize_factor,
            fg_color             = background_color,
            bg_color             = background_color
        )
        file_widget.place(relx = 0.0, rely = 0.0, relwidth = 0.5, relheight = 1.0)
        info_message.set("Ready")
    else:
        info_message.set("Not supported files :(")

def open_output_path_action():
    asked_selected_output_path = filedialog.askdirectory()
    if asked_selected_output_path == "":
        selected_output_path.set(OUTPUT_PATH_CODED)
    else:
        selected_output_path.set(asked_selected_output_path)



# GUI select from menus functions ---------------------------

def select_app_zoom(selected_option: str) -> None:
    global selected_app_zoom
    selected_app_zoom = selected_option
    apply_app_zoom(float(selected_option.replace("%", "")) / 100)

def select_AI_from_menu(selected_option: str) -> None:
    global selected_AI_model
    selected_AI_model = selected_option
    update_file_widget(1, 2, 3)

def select_AI_multithreading_from_menu(selected_option: str) -> None:
    global selected_AI_multithreading
    if selected_option == "OFF":
        selected_AI_multithreading = 1
    else:
        selected_AI_multithreading = int(selected_option.split()[0])

def select_blending_from_menu(selected_option: str) -> None:
    global selected_blending_factor

    match selected_option:
        case "OFF": selected_blending_factor = 0
        case "Low":      selected_blending_factor = 0.3
        case "Medium":   selected_blending_factor = 0.5
        case "High":     selected_blending_factor = 0.7

def select_gpu_from_menu(selected_option: str) -> None:
    global selected_gpu
    selected_gpu = selected_option

def select_save_frame_from_menu(selected_option: str):
    global selected_keep_frames
    if   selected_option == "ON":  selected_keep_frames = True
    elif selected_option == "OFF": selected_keep_frames = False

def select_image_extension_from_menu(selected_option: str) -> None:
    global selected_image_extension
    selected_image_extension = selected_option

def select_video_extension_from_menu(selected_option: str) -> None:
    global selected_video_extension
    selected_video_extension = selected_option

def select_video_codec_from_menu(selected_option: str) -> None:
    global selected_video_codec
    selected_video_codec = selected_option

def select_video_quality_from_menu(selected_option: str) -> None:
    global selected_video_quality
    selected_video_quality = selected_option



# GUI place functions ---------------------------

def place_loadFile_section() -> None:
    background = CTkFrame(
        master        = window,
        fg_color      = background_color,
        corner_radius = 0,
        border_width  = 0
    )

    text_drop = (" SUPPORTED FILES \n\n "
               + "IMAGES - jpg png tif bmp webp heic \n "
               + "VIDEOS - mp4 webm mkv flv gif avi mov mpg qt 3gp ")

    input_file_text = CTkLabel(
        master     = window,
        text       = text_drop,
        fg_color   = background_color,
        bg_color   = background_color,
        text_color = text_color,
        width      = 300,
        height     = 150,
        font       = bold13,
        anchor     = "center"
    )

    input_file_button = CTkButton(
        master       = window,
        command      = open_files_action,
        text         = "SELECT FILES",
        width        = 140,
        height       = 30,
        font         = bold12,
        border_width  = 1,
        corner_radius = 1,
        fg_color      = "#282828",
        text_color    = "#E0E0E0",
        border_color  = "#0096FF"
    )

    background.place(relx = 0.0, rely = 0.0, relwidth = 0.5, relheight = 1.0)
    input_file_text.place(relx = 0.25, rely = 0.4,  anchor = "center")
    input_file_button.place(relx = 0.25, rely = 0.5, anchor = "center")

def place_app_name() -> None:
    background = CTkFrame(
        master        = window,
        fg_color      = background_color,
        corner_radius = 0,
        border_width  = 0
    )
    app_name_label = CTkLabel(
        master     = window,
        text       = app_name + " " + version,
        fg_color   = background_color,
        bg_color   = background_color,
        text_color = app_name_color,
        font       = bold18,
        anchor     = "w"
    )
    background.place(relx = 0.5, rely = 0.0, relwidth = 0.5, relheight = 1.0)
    app_name_label.place(relx = column_1 - 0.055, rely = row0, anchor = "center")

def place_app_zoom_and_links() -> None:

    # App zoom menu
    label_app_zoom = CTkLabel(
        master     = window,
        text       = "App zoom",
        width      = 50,
        height     = 22,
        fg_color   = "transparent",
        bg_color   = background_color,
        text_color = text_color,
        font       = bold13,
        anchor     = "w"
    )
    zoom_option_menu = create_option_menu(
        command       = select_app_zoom,
        values        = zoom_option_list,
        default_value = selected_app_zoom,
        width         = 71
    )
    label_app_zoom.place(  relx = column_2-0.06,   rely = row0, anchor = "center")
    zoom_option_menu.place(relx = column_2+0.0155, rely = row0, anchor = "center")

    def opentelegram() -> None: open_browser(telegramme, new=1)
    def opengithub()   -> None: open_browser(githubme, new=1)

    # Telegram button
    telegram_button = create_link_button(command = opentelegram, icon = logo_telegram)
    telegram_button.place(relx = column_2+0.075, rely = row0, anchor = "center")

    # Github button
    git_button = create_link_button(command = opengithub, icon = logo_git)
    git_button.place(relx = column_2+0.11, rely = row0, anchor = "center")

def place_AI_menu() -> None:

    def open_info_AI_model():
        option_list = [
            "\n"
            "LVAx2"
            "\n"
            " - Target: Live-action video upscaling"
            "\n"
            " - Tips: AI interpolation - OFF/Low"
            "\n",

            "\n"
            "RealESR_Gx4 - RealESR_Ax4"
            "\n"
            " - Target: Animated/degraded live-action video upscaling"
            "\n"
            " - Tips: AI interpolation - Low for animation, Medium/High for live-action videos"
            "\n",

            "\n"
            "BSRGANx2 - BSRGANx4"
            "\n"
            " - Target: High-quality image upscaling"
            "\n"
            " - Tips: can be used to upscale videos but will be slow"
            "\n",

            "\n"
            "RealESRGANx4"
            "\n"
            " - Target: High-quality image upscaling"
            "\n"
            " - Tips: can be used to upscale videos but will be slow"
            "\n",

            "\n"
            "MSharpx4"
            "\n"
            " - Target: Image upscaling and sharpening"
            "\n"
            " - Tips: to use on good quality photos (not too much noise)"
            "\n",

            "\n"
            "IRCNN_Mx1 - IRCNN_Lx1"
            "\n"
            " - Target: Video/image denoising"
            "\n"
            " - Tips: AI interpolation - OFF"
            "\n",

        ]

        MessageBox(
            messageType   = "info",
            title         = "AI model",
            subtitle      = "This widget allows to choose between different AI models for upscaling",
            default_value = None,
            option_list   = option_list
        )

    widget_row = row1
    background = create_option_background()
    background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

    info_button = create_info_button(open_info_AI_model, "AI model")
    option_menu = create_option_menu(select_AI_from_menu, AI_models_list, default_AI_model)

    info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
    option_menu.place(relx = column_3_5,   rely = widget_row, anchor = "center")

def place_AI_blending_menu() -> None:

    def open_info_AI_blending():
        option_list = [
            " Blending combines the upscaled image produced by AI with the original image",

            " \n BLENDING OPTIONS\n" +
            "  - [OFF] No blending is applied\n" +
            "  - [Low] The result favors the upscaled image, with a slight touch of the original\n" +
            "  - [Medium] A balanced blend of the original and upscaled images\n" +
            "  - [High] The result favors the original image, with subtle enhancements from the upscaled version\n",

            " \n NOTES\n" +
            "  - Can enhance the quality of the final result\n" +
            "  - Especially effective when using the tiling/merging function (useful for low VRAM)\n" +
            "  - Particularly helpful at low input resolution percentages (<50%)\n",
        ]

        MessageBox(
            messageType   = "info",
            title         = "AI blending",
            subtitle      = "This widget allows you to choose the blending between the upscaled and original image/frame",
            default_value = None,
            option_list   = option_list
        )

    widget_row = row2

    background = create_option_background()
    background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

    info_button = create_info_button(open_info_AI_blending, "AI blending")
    option_menu = create_option_menu(select_blending_from_menu, blending_list, default_blending)

    info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
    option_menu.place(relx = column_3_5,   rely = widget_row, anchor = "center")

def place_AI_multithreading_menu() -> None:

    def open_info_AI_multithreading():
        option_list = [
            " This option can enhance video upscaling performance, especially on powerful GPUs.",

            " \n AI MULTITHREADING OPTIONS\n"
            + "  - OFF - Processes one frame at a time.\n"
            + "  - 2 threads - Processes two frames simultaneously.\n"
            + "  - 4 threads - Processes four frames simultaneously.\n"
            + "  - 6 threads - Processes six frames simultaneously.\n"
            + "  - 8 threads - Processes eight frames simultaneously.\n",

            " \n NOTES\n"
            + "  - Higher thread counts increase CPU, GPU, and RAM usage.\n"
            + "  - The GPU may be heavily stressed, potentially reaching high temperatures.\n"
            + "  - Monitor your system's temperature to prevent overheating.\n"
            + "  - If the chosen thread count exceeds GPU capacity, the app automatically selects an optimal value.\n",
        ]

        MessageBox(
            messageType   = "info",
            title         = "AI multithreading",
            subtitle      = "This widget allows to choose how many video frames are upscaled simultaneously",
            default_value = None,
            option_list   = option_list
        )

    widget_row = row3
    background = create_option_background()
    background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

    info_button = create_info_button(open_info_AI_multithreading, "AI multithreading")
    option_menu = create_option_menu(select_AI_multithreading_from_menu, AI_multithreading_list, default_AI_multithreading)

    info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
    option_menu.place(relx = column_3_5,   rely = widget_row, anchor = "center")

def place_input_output_resolution_textboxs() -> None:

    def open_info_input_resolution():
        option_list = [
            " A high value (>50%) will create high quality photos/videos but will be slower",
            " While a low value (<50%) will create good quality photos/videos but will much faster",

            " \n For example, for a 1080p (1920x1080) image/video\n" +
            " - Input scale 25% => input to AI 270p (480x270)\n" +
            " - Input scale 50% => input to AI 540p (960x540)\n" +
            " - Input scale 75% => input to AI 810p (1440x810)\n" +
            " - Input scale 100% => input to AI 1080p (1920x1080) \n",
        ]

        MessageBox(
            messageType   = "info",
            title         = "Input resolution %",
            subtitle      = "This widget allows to choose the resolution input to the AI",
            default_value = None,
            option_list   = option_list
        )

    def open_info_output_resolution():
        option_list = [
            " 100% keeps the exact resolution produced by the AI upscaling",
            " A lower value (<100%) will downscale the AI result to a smaller resolution, saving space and processing time",
            " A higher value (>100%) will further upscale the AI output, increasing size but not adding real details",

            "\n For example, if the AI generates a 4K (3840x2160) image/video\n" +
            " - Output scale 50%  => final output 1920x1080 (downscaled)\n" +
            " - Output scale 100% => final output 3840x2160 (AI native)\n" +
            " - Output scale 200% => final output 7680x4320 (8K, interpolated)\n",
        ]

        MessageBox(
            messageType   = "info",
            title         = "Output resolution %",
            subtitle      = "This widget allows to choose upscaled files resolution",
            default_value = None,
            option_list   = option_list
        )


    widget_row = row4

    background = create_option_background()
    background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

    # Input scale %
    info_button = create_info_button(open_info_input_resolution, "Input scale %")
    option_menu = create_text_box(selected_input_resize_factor, width = little_textbox_width)

    info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
    option_menu.place(relx = column_1_5,   rely = widget_row, anchor = "center")

    # Output scale %
    info_button = create_info_button(open_info_output_resolution, "Output scale %")
    option_menu = create_text_box(selected_output_resize_factor, width = little_textbox_width)

    info_button.place(relx = column_info2, rely = widget_row, anchor = "center")
    option_menu.place(relx = column_3,     rely = widget_row, anchor = "center")

def place_gpu_gpuVRAM_menus() -> None:

    def open_info_gpu():
        option_list = [
            "\n It is possible to select up to 4 GPUs for AI processing\n" +
            "  - Auto (the app will select the most powerful GPU)\n" +
            "  - GPU 1 (GPU 0 in Task manager)\n" +
            "  - GPU 2 (GPU 1 in Task manager)\n" +
            "  - GPU 3 (GPU 2 in Task manager)\n" +
            "  - GPU 4 (GPU 3 in Task manager)\n",

            "\n NOTES\n" +
            "  - Keep in mind that the more powerful the chosen gpu is, the faster the upscaling will be\n" +
            "  - For optimal performance, it is essential to regularly update your GPUs drivers\n" +
            "  - Selecting a GPU not present in the PC will cause the app to use the CPU for AI processing\n"
        ]

        MessageBox(
            messageType   = "info",
            title         = "GPU",
            subtitle      = "This widget allows to select the GPU for AI upscale",
            default_value = None,
            option_list   = option_list
        )

    def open_info_vram_limiter():
        option_list = [
            " Make sure to enter the correct value based on the selected GPU's VRAM",
            " Setting a value higher than the available VRAM may cause upscale failure",
            " For integrated GPUs (Intel HD series - Vega 3, 5, 7), select 2 GB to avoid issues",
        ]

        MessageBox(
            messageType   = "info",
            title         = "GPU VRAM (GB)",
            subtitle      = "This widget allows to set a limit on the GPU VRAM memory usage",
            default_value = None,
            option_list   = option_list
        )

    widget_row = row5

    background  = create_option_background()
    background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

    # GPU
    info_button = create_info_button(open_info_gpu, "GPU")
    option_menu = create_option_menu(select_gpu_from_menu, gpus_list, default_gpu, width = little_menu_width)

    info_button.place(relx = column_info1,        rely = widget_row, anchor = "center")
    option_menu.place(relx = column_1_4, rely = widget_row,  anchor = "center")

    # GPU VRAM
    info_button = create_info_button(open_info_vram_limiter, "GPU VRAM (GB)")
    option_menu = create_text_box(selected_VRAM_limiter, width = little_textbox_width)

    info_button.place(relx = column_info2, rely = widget_row, anchor = "center")
    option_menu.place(relx = column_3,     rely = widget_row, anchor = "center")

def place_image_video_output_menus() -> None:

    def open_info_image_output():
        option_list = [
            " \n PNG\n"
            " - Very good quality\n"
            " - Slow and heavy file\n"
            " - Supports transparent images\n"
            " - Lossless compression (no quality loss)\n"
            " - Ideal for graphics, web images, and screenshots\n",

            " \n JPG\n"
            " - Good quality\n"
            " - Fast and lightweight file\n"
            " - Lossy compression (some quality loss)\n"
            " - Ideal for photos and web images\n"
            " - Does not support transparency\n",

            " \n BMP\n"
            " - Highest quality\n"
            " - Slow and heavy file\n"
            " - Uncompressed format (large file size)\n"
            " - Ideal for raw images and high-detail graphics\n"
            " - Does not support transparency\n",

            " \n TIFF\n"
            " - Highest quality\n"
            " - Very slow and heavy file\n"
            " - Supports both lossless and lossy compression\n"
            " - Often used in professional photography and printing\n"
            " - Supports multiple layers and transparency\n",
        ]


        MessageBox(
            messageType   = "info",
            title         = "Image output",
            subtitle      = "This widget allows to choose the extension of upscaled images",
            default_value = None,
            option_list   = option_list
        )

    def open_info_video_extension():
        option_list = [
            " \n MP4\n"
            " - Most widely supported format\n"
            " - Good quality with efficient compression\n"
            " - Fast and lightweight file\n"
            " - Ideal for streaming and general use\n",

            " \n MKV\n"
            " - High-quality format with multiple audio and subtitle tracks support\n"
            " - Larger file size compared to MP4\n"
            " - Supports almost any codec\n"
            " - Ideal for high-quality videos and archiving\n",

            " \n AVI\n"
            " - Older format with high compatibility\n"
            " - Larger file size due to less efficient compression\n"
            " - Supports multiple codecs but lacks modern features\n"
            " - Ideal for older devices and raw video storage\n",

            " \n MOV\n"
            " - High-quality format developed by Apple\n"
            " - Large file size due to less compression\n"
            " - Best suited for editing and high-quality playback\n"
            " - Compatible mainly with macOS and iOS devices\n",
        ]

        MessageBox(
            messageType   = "info",
            title         = "Video output",
            subtitle      = "This widget allows to choose the extension of the upscaled video",
            default_value = None,
            option_list   = option_list
        )

    widget_row = row6

    background = create_option_background()
    background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

    # Image output
    info_button = create_info_button(open_info_image_output, "Image output")
    option_menu = create_option_menu(select_image_extension_from_menu, image_extension_list, default_image_extension, width = little_menu_width)
    info_button.place(relx = column_info1,        rely = widget_row, anchor = "center")
    option_menu.place(relx = column_1_4, rely = widget_row, anchor = "center")

    # Video output
    info_button = create_info_button(open_info_video_extension, "Video output")
    option_menu = create_option_menu(select_video_extension_from_menu, video_extension_list, default_video_extension, width = little_menu_width)
    info_button.place(relx = column_info2,      rely = widget_row, anchor = "center")
    option_menu.place(relx = column_2_9, rely = widget_row, anchor = "center")

def place_video_codec_keep_frames_menus() -> None:

    def open_info_video_codec():
        option_list = [
            " \n SOFTWARE ENCODING (CPU)\n"
            " - x264 | H.264 software encoding\n"
            " - x265 | HEVC (H.265) software encoding\n",

            " \n NVIDIA GPU ENCODING (NVENC - Optimized for NVIDIA GPU)\n"
            " - h264_nvenc | H.264 hardware encoding\n"
            " - hevc_nvenc | HEVC (H.265) hardware encoding\n",

            " \n AMD GPU ENCODING (AMF - Optimized for AMD GPU)\n"
            " - h264_amf | H.264 hardware encoding\n"
            " - hevc_amf | HEVC (H.265) hardware encoding\n",

            " \n INTEL GPU ENCODING (QSV - Optimized for Intel GPU)\n"
            " - h264_qsv | H.264 hardware encoding\n"
            " - hevc_qsv | HEVC (H.265) hardware encoding\n"
        ]


        MessageBox(
            messageType   = "info",
            title         = "Video codec",
            subtitle      = "This widget allows to choose video codec for upscaled video",
            default_value = None,
            option_list   = option_list
        )

    def open_info_keep_frames():
        option_list = [
            "\n ON \n" +
            " The app does NOT delete the video frames after creating the upscaled video \n",

            "\n OFF \n" +
            " The app deletes the video frames after creating the upscaled video \n"
        ]

        MessageBox(
            messageType   = "info",
            title         = "Keep video frames",
            subtitle      = "This widget allows to choose to keep video frames",
            default_value = None,
            option_list   = option_list
        )


    widget_row = row7

    background = create_option_background()
    background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

    # Video codec
    info_button = create_info_button(open_info_video_codec, "Video codec")
    option_menu = create_option_menu(select_video_codec_from_menu, video_codec_list, default_video_codec, width = little_menu_width)
    info_button.place(relx = column_info1,        rely = widget_row, anchor = "center")
    option_menu.place(relx = column_1_4, rely = widget_row, anchor = "center")

    # Keep frames
    info_button = create_info_button(open_info_keep_frames, "Keep frames")
    option_menu = create_option_menu(select_save_frame_from_menu, keep_frames_list, default_keep_frames, width = little_menu_width)
    info_button.place(relx = column_info2,      rely = widget_row, anchor = "center")
    option_menu.place(relx = column_2_9, rely = widget_row, anchor = "center")

def place_video_quality_menu() -> None:

    def open_info_video_quality():
        option_list = [
            "\n LOW \n" +
            " Smaller files, visibly lower quality \n",

            "\n MEDIUM \n" +
            " Balanced size and quality \n",

            "\n HIGH \n" +
            " Best quality, larger files (x264 crf 18) \n"
        ]

        MessageBox(
            messageType   = "info",
            title         = "Video quality",
            subtitle      = "This widget allows to choose the video encoder quality",
            default_value = None,
            option_list   = option_list
        )

    widget_row = row8

    background = create_option_background()
    background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

    info_button = create_info_button(open_info_video_quality, "Video quality")
    option_menu = create_option_menu(select_video_quality_from_menu, video_quality_list, default_video_quality, width = little_menu_width)
    info_button.place(relx = column_info1,        rely = widget_row, anchor = "center")
    option_menu.place(relx = column_1_4, rely = widget_row, anchor = "center")

def place_output_path_textbox() -> None:

    def open_info_output_path():
        option_list = [
              "\n The default path is defined by the input files."
            + "\n For example: selecting a file from the Download folder,"
            + "\n the app will save upscaled files in the Download folder \n",

            " Otherwise it is possible to select the desired path using the SELECT button",
        ]

        MessageBox(
            messageType   = "info",
            title         = "Output path",
            subtitle      = "This widget allows to choose upscaled files path",
            default_value = None,
            option_list   = option_list
        )

    background    = create_option_background()
    info_button   = create_info_button(open_info_output_path, "Output path")
    option_menu   = create_text_box_output_path(selected_output_path)
    active_button = create_active_button(
        command = open_output_path_action,
        text    = "SELECT",
        icon    = None,
        width   = 60,
        height  = 25
    )

    background.place(   relx = 0.75,                 rely = row10, relwidth = 0.48,  anchor = "center")
    info_button.place(  relx = column_info1,         rely = row10 - 0.003,           anchor = "center")
    active_button.place(relx = column_info1 + 0.052, rely = row10,                   anchor = "center")
    option_menu.place(  relx = column_2 - 0.008,     rely = row10,                   anchor = "center")

def place_message_label() -> None:
    message_label = CTkLabel(
        master        = window,
        textvariable  = info_message,
        height        = 25,
        width         = 250,
        font          = bold11,
        fg_color      = "#ffbf00",
        text_color    = "#000000",
        anchor        = "center",
        corner_radius = 4
    )

    triangle_dimension = 14
    zero = 0
    triangle_pointer = CTkCanvas(
        window,
        width   = triangle_dimension,
        height  = triangle_dimension,
        bg      = background_color,
        highlightthickness = 0
    )
    triangle_pointer.create_polygon(
        triangle_dimension, zero,
        zero,               (triangle_dimension/2),
        triangle_dimension, triangle_dimension,
        fill = "#ffbf00"
    )
    triangle_pointer.place(relx = 0.716, rely = row11, anchor = "center")
    message_label.place(   relx = 0.85,  rely = row11, anchor = "center")

def place_stop_button() -> None:
    stop_button = create_active_button(
        command      = stop_button_command,
        text         = "STOP",
        icon         = stop_icon,
        width        = 150,
        height       = 30,
        border_color = "#EC1D1D"
    )
    stop_button.place(relx = 0.62, rely = row11, anchor = "center")

def place_upscale_button() -> None:
    upscale_button = create_active_button(
        command = upscale_button_command,
        text    = "UPSCALE",
        icon    = upscale_icon,
        width   = 150,
        height  = 30
    )
    upscale_button.place(relx = 0.62, rely = row11, anchor = "center")



# App related functions ---------------------------

def save_user_choices_in_json() -> None:
    global selected_app_zoom
    global selected_AI_model
    global selected_AI_multithreading
    global selected_gpu
    global selected_blending_factor
    global selected_image_extension
    global selected_video_extension
    global selected_video_codec
    global selected_video_quality
    global tiles_resolution
    global input_resize_factor

    app_zoom_to_save        = selected_app_zoom
    AI_model_to_save        = selected_AI_model
    gpu_to_save             = selected_gpu
    image_extension_to_save = selected_image_extension
    video_extension_to_save = selected_video_extension
    video_codec_to_save     = selected_video_codec
    video_quality_to_save   = selected_video_quality
    blending_to_save        = {0: "OFF", 0.3: "Low", 0.5: "Medium", 0.7: "High"}.get(selected_blending_factor)

    keep_frames_to_save = "OFF"
    if selected_keep_frames == True: keep_frames_to_save = "ON"

    AI_multithreading_to_save = f"{selected_AI_multithreading} threads"
    if selected_AI_multithreading == 1: AI_multithreading_to_save = "OFF"

    user_preference = {
        "default_app_zoom":             app_zoom_to_save,
        "default_AI_model":             AI_model_to_save,
        "default_AI_multithreading":    AI_multithreading_to_save,
        "default_gpu":                  gpu_to_save,
        "default_keep_frames":          keep_frames_to_save,
        "default_image_extension":      image_extension_to_save,
        "default_video_extension":      video_extension_to_save,
        "default_video_codec":          video_codec_to_save,
        "default_video_quality":        video_quality_to_save,
        "default_blending":             blending_to_save,
        "default_output_path":          selected_output_path.get(),
        "default_input_resize_factor":  str(selected_input_resize_factor.get()),
        "default_output_resize_factor": str(selected_output_resize_factor.get()),
        "default_VRAM_limiter":         str(selected_VRAM_limiter.get()),
    }
    user_preference_json = json_dumps(user_preference)
    with open(USER_PREFERENCE_PATH, "w") as preference_file:
        preference_file.write(user_preference_json)

def on_app_close() -> None:
    # 1. Save user choices in file
    save_user_choices_in_json()

    # 2. Destroy app window
    window.grab_release()
    window.destroy()

    # 3. Stop upscale process and thread check_upscale_step
    write_process_status(process_status_q, f"{CLOSE_APP_STATUS}")
    stop_upscale_process()

class App():

    def __init__(self, window) -> None:
        self.toplevel_window = None
        window.protocol("WM_DELETE_WINDOW", on_app_close)

        window.title(self._get_window_title())
        window.geometry("1000x675")
        window.resizable(False, False)
        window.iconbitmap(find_by_relative_path("Assets" + os_separator + "logo.ico"))

        place_loadFile_section()

        place_app_name()
        place_app_zoom_and_links()
        place_AI_menu()
        place_AI_blending_menu()
        place_AI_multithreading_menu()
        place_input_output_resolution_textboxs()
        place_gpu_gpuVRAM_menus()
        place_image_video_output_menus()
        place_video_codec_keep_frames_menus()
        place_video_quality_menu()
        place_output_path_textbox()

        place_message_label()
        place_upscale_button()

    def _get_window_title(self) -> str:
        AI_engine_info = self._get_AI_engine_info()
        if AI_engine_info:
            return f"{app_name} - {AI_engine_info}"
        return app_name

    def _get_AI_engine_info(self) -> str:
        try:
            # Lazy import: onnxruntime is a heavy dependency only needed by the
            # pipeline subprocess, the GUI only reads its version string here
            from onnxruntime import (
                get_available_providers as onnxruntime_get_available_providers,
                get_version_string      as onnxruntime_get_version_string
            )
            AI_engine_v  = onnxruntime_get_version_string()
            print(onnxruntime_get_available_providers())
            is_directml  = any("Dml" in p or "DirectML" in p for p in onnxruntime_get_available_providers())
            AI_providers = "DirectML" if is_directml else "CPU"
            return f"AI engine {AI_engine_v} + {AI_providers}"
        except:
            return ""



# Main functions ---------------------------

if __name__ == "__main__":

    if os_path_exists(USER_PREFERENCE_PATH):
        print(f"[{app_name}] Preference file exist")
        with open(USER_PREFERENCE_PATH, "r") as json_file:
            json_data = json_load(json_file)
            default_app_zoom             = json_data.get("default_app_zoom",             "100%")
            default_AI_model             = json_data.get("default_AI_model",             AI_models_list[0])
            default_AI_multithreading    = json_data.get("default_AI_multithreading",    AI_multithreading_list[0])
            default_gpu                  = json_data.get("default_gpu",                  gpus_list[0])
            default_keep_frames          = json_data.get("default_keep_frames",          keep_frames_list[1])
            default_image_extension      = json_data.get("default_image_extension",      image_extension_list[0])
            default_video_extension      = json_data.get("default_video_extension",      video_extension_list[0])
            default_video_codec          = json_data.get("default_video_codec",          video_codec_list[0])
            default_video_quality        = json_data.get("default_video_quality",        "HIGH")
            default_blending             = json_data.get("default_blending",             blending_list[1])
            default_output_path          = json_data.get("default_output_path",          OUTPUT_PATH_CODED)
            default_input_resize_factor  = json_data.get("default_input_resize_factor",  str(50))
            default_output_resize_factor = json_data.get("default_output_resize_factor", str(100))
            default_VRAM_limiter         = json_data.get("default_VRAM_limiter",         str(4))
    else:
        print(f"[{app_name}] Preference file does not exist, using default coded value")
        default_app_zoom             = "100%"
        default_AI_model             = AI_models_list[0]
        default_AI_multithreading    = AI_multithreading_list[0]
        default_gpu                  = gpus_list[0]
        default_keep_frames          = keep_frames_list[1]
        default_image_extension      = image_extension_list[0]
        default_video_extension      = video_extension_list[0]
        default_video_codec          = video_codec_list[0]
        default_video_quality        = "HIGH"
        default_blending             = blending_list[1]
        default_output_path          = OUTPUT_PATH_CODED
        default_input_resize_factor  = str(50)
        default_output_resize_factor = str(100)
        default_VRAM_limiter         = str(4)

    multiprocessing_freeze_support()
    set_appearance_mode("Dark")
    set_default_color_theme("dark-blue")
    apply_app_zoom(float(default_app_zoom.replace("%", "")) / 100)

    multiprocessing_manager    = multiprocessing_Manager()
    process_status_q           = multiprocessing_manager.Queue(maxsize=1)
    event_stop_upscale_process = multiprocessing_manager.Event()

    window = CTk()
    info_message                  = StringVar()
    selected_output_path          = StringVar()
    selected_input_resize_factor  = StringVar()
    selected_output_resize_factor = StringVar()
    selected_VRAM_limiter         = StringVar()

    global selected_app_zoom
    global selected_file_list
    global selected_AI_model
    global selected_blending_factor
    global selected_AI_multithreading
    global selected_gpu
    global selected_keep_frames
    global selected_image_extension
    global selected_video_extension
    global selected_video_codec
    global selected_video_quality
    global tiles_resolution
    global input_resize_factor

    selected_app_zoom        = default_app_zoom
    selected_file_list       = []
    selected_AI_model        = default_AI_model
    selected_gpu             = default_gpu
    selected_image_extension = default_image_extension
    selected_video_extension = default_video_extension
    selected_video_codec     = default_video_codec
    selected_video_quality   = default_video_quality

    if default_AI_multithreading == "OFF":
        selected_AI_multithreading = 1
    else:
        selected_AI_multithreading = int(default_AI_multithreading.split()[0])

    selected_keep_frames = False
    if default_keep_frames == "ON": selected_keep_frames = True

    selected_blending_factor = {"OFF": 0, "Low": 0.3, "Medium": 0.5, "High": 0.7}.get(default_blending)

    selected_input_resize_factor.set(default_input_resize_factor)
    selected_output_resize_factor.set(default_output_resize_factor)
    selected_VRAM_limiter.set(default_VRAM_limiter)
    selected_output_path.set(default_output_path)

    info_message.set("Hi :)")
    selected_input_resize_factor.trace_add('write', update_file_widget)
    selected_output_resize_factor.trace_add('write', update_file_widget)

    font   = "Segoe UI"
    bold8  = CTkFont(family = font, size = 8, weight = "bold")
    bold9  = CTkFont(family = font, size = 9, weight = "bold")
    bold10 = CTkFont(family = font, size = 10, weight = "bold")
    bold11 = CTkFont(family = font, size = 11, weight = "bold")
    bold12 = CTkFont(family = font, size = 12, weight = "bold")
    bold13 = CTkFont(family = font, size = 13, weight = "bold")
    bold14 = CTkFont(family = font, size = 14, weight = "bold")
    bold16 = CTkFont(family = font, size = 16, weight = "bold")
    bold17 = CTkFont(family = font, size = 17, weight = "bold")
    bold18 = CTkFont(family = font, size = 18, weight = "bold")
    bold19 = CTkFont(family = font, size = 19, weight = "bold")
    bold20 = CTkFont(family = font, size = 20, weight = "bold")
    bold21 = CTkFont(family = font, size = 21, weight = "bold")
    bold22 = CTkFont(family = font, size = 22, weight = "bold")
    bold23 = CTkFont(family = font, size = 23, weight = "bold")
    bold24 = CTkFont(family = font, size = 24, weight = "bold")

    # Images
    logo_git      = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}github_logo.png")),    size=(18, 18))
    logo_telegram = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}telegram_logo.png")),  size=(16, 16))
    stop_icon     = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}stop_icon.png")),      size=(15, 15))
    upscale_icon  = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}upscale_icon.png")),   size=(15, 15))
    clear_icon    = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}clear_icon.png")),     size=(15, 15))
    info_icon     = CTkImage(pillow_image_open(find_by_relative_path(f"Assets{os_separator}info_icon.png")),      size=(18, 18))

    app = App(window)
    window.update()
    window.mainloop()
