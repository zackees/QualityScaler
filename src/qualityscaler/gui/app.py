"""QualityScaler GUI application: window layout, event handlers and main().

This is the toolkit layer entry point: customtkinter/tkinter usage is
confined to this module and :mod:`qualityscaler.gui.widgets`.
"""

import sys

from multiprocessing import freeze_support as multiprocessing_freeze_support
from os import sep as os_separator, devnull as os_devnull
from os.path import exists as os_path_exists
from webbrowser import open as open_browser

from tkinter import StringVar

from customtkinter import (
    CTk,
    CTkButton,
    CTkCanvas,
    CTkFrame,
    CTkLabel,
    CTkTabview,
    filedialog,
    set_appearance_mode,
    set_default_color_theme,
    set_widget_scaling,
    set_window_scaling,
)

from qualityscaler.core import (
    UpscaleProgress,
    UpscaleCompleted,
    UpscaleError,
    UpscaleStopped,
)

from qualityscaler.gui.assets import ensure_assets, find_by_relative_path
from qualityscaler.gui.constants import (
    app_name,
    app_name_color,
    background_color,
    text_color,
    version,
    githubme,
    telegramme,
    AI_models_list,
    AI_multithreading_list,
    blending_list,
    gpus_list,
    image_extension_list,
    keep_frames_list,
    video_codec_list,
    video_extension_list,
    video_quality_list,
    zoom_option_list,
    OUTPUT_PATH_CODED,
    supported_file_extensions,
    row0, row1, row2, row3, row4, row5, row6, row7, row8, row10, row11,
    column_info1, column_info2,
    column_1, column_2, column_3,
    column_1_4, column_1_5, column_2_9, column_3_5,
    little_textbox_width, little_menu_width,
)
from qualityscaler.gui.console_log import ConsoleSink, install_console_redirectors
from qualityscaler.gui.console_widget import ConsoleWidget
from qualityscaler.gui.controller import (
    UpscaleController,
    build_settings,
    format_progress_event,
    validate,
)
from qualityscaler.gui.info_texts import (
    AI_MODEL_INFO,
    AI_BLENDING_INFO,
    AI_MULTITHREADING_INFO,
    INPUT_RESOLUTION_INFO,
    OUTPUT_RESOLUTION_INFO,
    GPU_INFO,
    VRAM_LIMITER_INFO,
    IMAGE_OUTPUT_INFO,
    VIDEO_EXTENSION_INFO,
    VIDEO_CODEC_INFO,
    KEEP_FRAMES_INFO,
    VIDEO_QUALITY_INFO,
    OUTPUT_PATH_INFO,
)
from qualityscaler.gui.ff_controller import FrameGenController
from qualityscaler.gui.ff_panel import FluidFramesPanel
from qualityscaler.gui.file_chooser import get_initial_dir, update_last_used_dir
from qualityscaler.gui.ff_preferences import FF_USER_PREFERENCE_PATH, load_ff_preferences
from qualityscaler.gui.preferences import USER_PREFERENCE_PATH, load_preferences, save_preferences
from qualityscaler.gui.state import UIState, upscale_factor_for_model
from qualityscaler.gui.widgets import (
    AppFonts,
    AppIcons,
    FileWidget,
    MessageBox,
    create_active_button,
    create_info_button,
    create_link_button,
    create_option_background,
    create_option_menu,
    create_text_box,
    create_text_box_output_path,
    load_fonts,
    load_icons,
)


if sys.stdout is None:
    sys.stdout = open(os_devnull, "w", encoding="utf-8", errors="replace")
else:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

if sys.stderr is None:
    sys.stderr = open(os_devnull, "w", encoding="utf-8", errors="replace")
else:
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


WINDOW_BASE_HEIGHT = 710
CONSOLE_HEIGHT = 180


def apply_app_zoom(zoom: float) -> None:
    set_window_scaling(zoom)
    set_widget_scaling(zoom)


class App():

    def __init__(
            self,
            window,
            parent,
            state: UIState,
            controller: UpscaleController,
            fonts: AppFonts,
            icons: AppIcons,
            extra_save = None,
            extra_shutdown = None,
            on_toggle_console = None,
            ) -> None:

        self.window            = window
        self.parent            = parent
        self.state             = state
        self.controller        = controller
        self.fonts             = fonts
        self.icons             = icons
        self.extra_save        = extra_save
        self.extra_shutdown    = extra_shutdown
        self.on_toggle_console = on_toggle_console

        self.toplevel_window = None
        self.file_widget = None

        self.info_message                  = StringVar()
        self.selected_output_path          = StringVar()
        self.selected_input_resize_factor  = StringVar()
        self.selected_output_resize_factor = StringVar()
        self.selected_VRAM_limiter         = StringVar()

        self.selected_input_resize_factor.set(state.input_resize_factor)
        self.selected_output_resize_factor.set(state.output_resize_factor)
        self.selected_VRAM_limiter.set(state.vram_limiter)
        self.selected_output_path.set(state.output_path)

        self.info_message.set("Hi :)")
        self.selected_input_resize_factor.trace_add('write', self.update_file_widget)
        self.selected_output_resize_factor.trace_add('write', self.update_file_widget)

        window.protocol("WM_DELETE_WINDOW", self.on_app_close)

        window.title(self._get_window_title())
        window.geometry("1000x710")
        window.resizable(False, False)
        window.iconbitmap(find_by_relative_path("Assets" + os_separator + "logo.ico"))

        self.place_loadFile_section()

        self.place_app_name()
        self.place_app_zoom_and_links()
        self.place_AI_menu()
        self.place_AI_blending_menu()
        self.place_AI_multithreading_menu()
        self.place_input_output_resolution_textboxs()
        self.place_gpu_gpuVRAM_menus()
        self.place_image_video_output_menus()
        self.place_video_codec_keep_frames_menus()
        self.place_video_quality_menu()
        self.place_output_path_textbox()

        self.place_message_label()
        self.place_upscale_button()

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
        except Exception:
            return ""

    # State helpers ---------------------------

    def _snapshot_state(self) -> UIState:
        self.state.output_path          = self.selected_output_path.get()
        self.state.input_resize_factor  = str(self.selected_input_resize_factor.get())
        self.state.output_resize_factor = str(self.selected_output_resize_factor.get())
        self.state.vram_limiter         = str(self.selected_VRAM_limiter.get())
        if self.file_widget is None:
            self.state.file_list = []
        else:
            self.state.file_list = list(self.file_widget.get_selected_file_list())
        return self.state

    def get_upscale_factor(self) -> int:
        return upscale_factor_for_model(self.state.ai_model)

    def get_values_for_file_widget(self) -> tuple:
        # Upscale factor
        upscale_factor = self.get_upscale_factor()

        # Input resolution %
        try:
            input_resize_factor = int(float(str(self.selected_input_resize_factor.get())))
        except Exception:
            input_resize_factor = 0

        # Output resolution %
        try:
            output_resize_factor = int(float(str(self.selected_output_resize_factor.get())))
        except Exception:
            output_resize_factor = 0

        return upscale_factor, input_resize_factor, output_resize_factor

    def update_file_widget(self, *args) -> None:
        if self.file_widget is None:
            return

        upscale_factor, input_resize_factor, output_resize_factor = self.get_values_for_file_widget()

        self.file_widget.clean_file_list()
        self.file_widget.set_upscale_factor(upscale_factor)
        self.file_widget.set_input_resize_factor(input_resize_factor)
        self.file_widget.set_output_resize_factor(output_resize_factor)
        self.file_widget._create_widgets()

    # Upscale orchestration ---------------------------

    def upscale_button_command(self) -> None:
        state = self._snapshot_state()

        error = validate(state)
        if error is not None:
            self.info_message.set(error)
            return

        self.info_message.set("Loading")

        settings = build_settings(state)
        try:
            settings.validate()
        except ValueError as validation_error:
            self.info_message.set(str(validation_error))
            return

        self.place_stop_button()
        self.controller.start(settings, self._on_pipeline_event)

    def stop_button_command(self) -> None:
        self.controller.request_stop()

    def _on_pipeline_event(self, actual_event) -> None:
        if isinstance(actual_event, UpscaleStopped):
            self.info_message.set("Upscaling stopped")
            self.place_upscale_button()

        elif isinstance(actual_event, UpscaleCompleted):
            self.info_message.set("All files completed! :)")
            self.controller.stop_process()
            self.place_upscale_button()

        elif isinstance(actual_event, UpscaleError):
            self.info_message.set("Error while upscaling :(")
            self.show_error_message(actual_event.message)
            self.controller.stop_process()
            self.place_upscale_button()

        elif isinstance(actual_event, UpscaleProgress):
            self.info_message.set(format_progress_event(actual_event))

        else:
            self.info_message.set(str(actual_event))

    def show_error_message(self, exception: str) -> None:
        messageBox_title    = "Upscale error"
        messageBox_subtitle = "Please report the error on Github or Telegram"
        messageBox_text     = f"\n {str(exception)} \n"

        MessageBox(
            messageType   = "error",
            title         = messageBox_title,
            subtitle      = messageBox_subtitle,
            default_value = None,
            option_list   = [messageBox_text],
            fonts         = self.fonts
        )

    # File selection ---------------------------

    def open_files_action(self) -> None:

        def check_supported_selected_files(uploaded_file_list: list) -> list:
            return [file for file in uploaded_file_list if any(supported_extension in file for supported_extension in supported_file_extensions)]

        self.info_message.set("Selecting files")

        uploaded_files_list    = list(filedialog.askopenfilenames(initialdir=get_initial_dir()))
        uploaded_files_counter = len(uploaded_files_list)
        update_last_used_dir(uploaded_files_list)

        supported_files_list    = check_supported_selected_files(uploaded_files_list)
        supported_files_counter = len(supported_files_list)

        print("> Uploaded files: " + str(uploaded_files_counter) + " => Supported files: " + str(supported_files_counter))

        if supported_files_counter > 0:
            upscale_factor, input_resize_factor, output_resize_factor = self.get_values_for_file_widget()

            self.file_widget = FileWidget(
                master               = self.parent,
                selected_file_list   = supported_files_list,
                fonts                = self.fonts,
                clear_icon           = self.icons.clear_icon,
                on_clean             = self._on_file_widget_clean,
                upscale_factor       = upscale_factor,
                input_resize_factor  = input_resize_factor,
                output_resize_factor = output_resize_factor,
                fg_color             = background_color,
                bg_color             = background_color
            )
            self.file_widget.place(relx = 0.0, rely = 0.0, relwidth = 0.5, relheight = 1.0)
            self.info_message.set("Ready")
        else:
            self.info_message.set("Not supported files :(")

    def _on_file_widget_clean(self) -> None:
        self.file_widget = None
        self.place_loadFile_section()

    def open_output_path_action(self) -> None:
        asked_selected_output_path = filedialog.askdirectory(initialdir=get_initial_dir())
        if asked_selected_output_path == "":
            self.selected_output_path.set(OUTPUT_PATH_CODED)
        else:
            update_last_used_dir(asked_selected_output_path)
            self.selected_output_path.set(asked_selected_output_path)

    # Menu select handlers ---------------------------

    def select_app_zoom(self, selected_option: str) -> None:
        self.state.app_zoom = selected_option
        apply_app_zoom(float(selected_option.replace("%", "")) / 100)

    def select_AI_from_menu(self, selected_option: str) -> None:
        self.state.ai_model = selected_option
        self.update_file_widget()

    def select_AI_multithreading_from_menu(self, selected_option: str) -> None:
        self.state.ai_multithreading = selected_option

    def select_blending_from_menu(self, selected_option: str) -> None:
        self.state.blending = selected_option

    def select_gpu_from_menu(self, selected_option: str) -> None:
        self.state.gpu = selected_option

    def select_save_frame_from_menu(self, selected_option: str) -> None:
        self.state.keep_frames = selected_option

    def select_image_extension_from_menu(self, selected_option: str) -> None:
        self.state.image_extension = selected_option

    def select_video_extension_from_menu(self, selected_option: str) -> None:
        self.state.video_extension = selected_option

    def select_video_codec_from_menu(self, selected_option: str) -> None:
        self.state.video_codec = selected_option

    def select_video_quality_from_menu(self, selected_option: str) -> None:
        self.state.video_quality = selected_option

    # Place functions ---------------------------

    def place_loadFile_section(self) -> None:
        background = CTkFrame(
            master        = self.parent,
            fg_color      = background_color,
            corner_radius = 0,
            border_width  = 0
        )

        text_drop = (" SUPPORTED FILES \n\n "
                   + "IMAGES - jpg png tif bmp webp heic \n "
                   + "VIDEOS - mp4 webm mkv flv gif avi mov mpg qt 3gp ")

        input_file_text = CTkLabel(
            master     = self.parent,
            text       = text_drop,
            fg_color   = background_color,
            bg_color   = background_color,
            text_color = text_color,
            width      = 300,
            height     = 150,
            font       = self.fonts.bold13,
            anchor     = "center"
        )

        input_file_button = CTkButton(
            master       = self.parent,
            command      = self.open_files_action,
            text         = "SELECT FILES",
            width        = 140,
            height       = 30,
            font         = self.fonts.bold12,
            border_width  = 1,
            corner_radius = 1,
            fg_color      = "#282828",
            text_color    = "#E0E0E0",
            border_color  = "#0096FF"
        )

        background.place(relx = 0.0, rely = 0.0, relwidth = 0.5, relheight = 1.0)
        input_file_text.place(relx = 0.25, rely = 0.4,  anchor = "center")
        input_file_button.place(relx = 0.25, rely = 0.5, anchor = "center")

    def place_app_name(self) -> None:
        background = CTkFrame(
            master        = self.parent,
            fg_color      = background_color,
            corner_radius = 0,
            border_width  = 0
        )
        app_name_label = CTkLabel(
            master     = self.parent,
            text       = app_name + " " + version,
            fg_color   = background_color,
            bg_color   = background_color,
            text_color = app_name_color,
            font       = self.fonts.bold18,
            anchor     = "w"
        )
        background.place(relx = 0.5, rely = 0.0, relwidth = 0.5, relheight = 1.0)
        app_name_label.place(relx = column_1 - 0.055, rely = row0, anchor = "center")

    def place_app_zoom_and_links(self) -> None:

        # App zoom menu
        label_app_zoom = CTkLabel(
            master     = self.parent,
            text       = "App zoom",
            width      = 50,
            height     = 22,
            fg_color   = "transparent",
            bg_color   = background_color,
            text_color = text_color,
            font       = self.fonts.bold13,
            anchor     = "w"
        )
        zoom_option_menu = create_option_menu(
            master        = self.parent,
            fonts         = self.fonts,
            command       = self.select_app_zoom,
            values        = zoom_option_list,
            default_value = self.state.app_zoom,
            width         = 71
        )
        label_app_zoom.place(  relx = column_2-0.06,   rely = row0, anchor = "center")
        zoom_option_menu.place(relx = column_2+0.0155, rely = row0, anchor = "center")

        def opentelegram() -> None:
            open_browser(telegramme, new=1)

        def opengithub() -> None:
            open_browser(githubme, new=1)

        # Telegram button
        telegram_button = create_link_button(self.parent, self.fonts, command = opentelegram, icon = self.icons.logo_telegram)
        telegram_button.place(relx = column_2+0.075, rely = row0, anchor = "center")

        # Github button
        git_button = create_link_button(self.parent, self.fonts, command = opengithub, icon = self.icons.logo_git)
        git_button.place(relx = column_2+0.11, rely = row0, anchor = "center")

        # Console toggle button
        if self.on_toggle_console is not None:
            console_button = CTkButton(
                master        = self.parent,
                command       = self.on_toggle_console,
                text          = ">_",
                width         = 30,
                height        = 30,
                font          = self.fonts.bold11,
                border_width  = 1,
                corner_radius = 1,
                fg_color      = "transparent",
                text_color    = "#E0E0E0",
                border_color  = "#404040",
            )
            console_button.place(relx = column_2+0.145, rely = row0, anchor = "center")

    def place_AI_menu(self) -> None:

        def open_info_AI_model():
            option_list = AI_MODEL_INFO

            MessageBox(
                messageType   = "info",
                title         = "AI model",
                subtitle      = "This widget allows to choose between different AI models for upscaling",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        widget_row = row1
        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_AI_model, "AI model")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_AI_from_menu, AI_models_list, self.state.ai_model)

        info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_3_5,   rely = widget_row, anchor = "center")

    def place_AI_blending_menu(self) -> None:

        def open_info_AI_blending():
            option_list = AI_BLENDING_INFO

            MessageBox(
                messageType   = "info",
                title         = "AI blending",
                subtitle      = "This widget allows you to choose the blending between the upscaled and original image/frame",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        widget_row = row2

        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_AI_blending, "AI blending")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_blending_from_menu, blending_list, self.state.blending)

        info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_3_5,   rely = widget_row, anchor = "center")

    def place_AI_multithreading_menu(self) -> None:

        def open_info_AI_multithreading():
            option_list = AI_MULTITHREADING_INFO

            MessageBox(
                messageType   = "info",
                title         = "AI multithreading",
                subtitle      = "This widget allows to choose how many video frames are upscaled simultaneously",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        widget_row = row3
        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_AI_multithreading, "AI multithreading")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_AI_multithreading_from_menu, AI_multithreading_list, self.state.ai_multithreading)

        info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_3_5,   rely = widget_row, anchor = "center")

    def place_input_output_resolution_textboxs(self) -> None:

        def open_info_input_resolution():
            option_list = INPUT_RESOLUTION_INFO

            MessageBox(
                messageType   = "info",
                title         = "Input resolution %",
                subtitle      = "This widget allows to choose the resolution input to the AI",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        def open_info_output_resolution():
            option_list = OUTPUT_RESOLUTION_INFO

            MessageBox(
                messageType   = "info",
                title         = "Output resolution %",
                subtitle      = "This widget allows to choose upscaled files resolution",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        widget_row = row4

        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        # Input scale %
        info_button = create_info_button(self.parent, self.fonts, open_info_input_resolution, "Input scale %")
        option_menu = create_text_box(self.parent, self.fonts, self.selected_input_resize_factor, width = little_textbox_width)

        info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_1_5,   rely = widget_row, anchor = "center")

        # Output scale %
        info_button = create_info_button(self.parent, self.fonts, open_info_output_resolution, "Output scale %")
        option_menu = create_text_box(self.parent, self.fonts, self.selected_output_resize_factor, width = little_textbox_width)

        info_button.place(relx = column_info2, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_3,     rely = widget_row, anchor = "center")

    def place_gpu_gpuVRAM_menus(self) -> None:

        def open_info_gpu():
            option_list = GPU_INFO

            MessageBox(
                messageType   = "info",
                title         = "GPU",
                subtitle      = "This widget allows to select the GPU for AI upscale",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        def open_info_vram_limiter():
            option_list = VRAM_LIMITER_INFO

            MessageBox(
                messageType   = "info",
                title         = "GPU VRAM (GB)",
                subtitle      = "This widget allows to set a limit on the GPU VRAM memory usage",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        widget_row = row5

        background  = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        # GPU
        info_button = create_info_button(self.parent, self.fonts, open_info_gpu, "GPU")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_gpu_from_menu, gpus_list, self.state.gpu, width = little_menu_width)

        info_button.place(relx = column_info1,        rely = widget_row, anchor = "center")
        option_menu.place(relx = column_1_4, rely = widget_row,  anchor = "center")

        # GPU VRAM
        info_button = create_info_button(self.parent, self.fonts, open_info_vram_limiter, "GPU VRAM (GB)")
        option_menu = create_text_box(self.parent, self.fonts, self.selected_VRAM_limiter, width = little_textbox_width)

        info_button.place(relx = column_info2, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_3,     rely = widget_row, anchor = "center")

    def place_image_video_output_menus(self) -> None:

        def open_info_image_output():
            option_list = IMAGE_OUTPUT_INFO

            MessageBox(
                messageType   = "info",
                title         = "Image output",
                subtitle      = "This widget allows to choose the extension of upscaled images",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        def open_info_video_extension():
            option_list = VIDEO_EXTENSION_INFO

            MessageBox(
                messageType   = "info",
                title         = "Video output",
                subtitle      = "This widget allows to choose the extension of the upscaled video",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        widget_row = row6

        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        # Image output
        info_button = create_info_button(self.parent, self.fonts, open_info_image_output, "Image output")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_image_extension_from_menu, image_extension_list, self.state.image_extension, width = little_menu_width)
        info_button.place(relx = column_info1,        rely = widget_row, anchor = "center")
        option_menu.place(relx = column_1_4, rely = widget_row, anchor = "center")

        # Video output
        info_button = create_info_button(self.parent, self.fonts, open_info_video_extension, "Video output")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_video_extension_from_menu, video_extension_list, self.state.video_extension, width = little_menu_width)
        info_button.place(relx = column_info2,      rely = widget_row, anchor = "center")
        option_menu.place(relx = column_2_9, rely = widget_row, anchor = "center")

    def place_video_codec_keep_frames_menus(self) -> None:

        def open_info_video_codec():
            option_list = VIDEO_CODEC_INFO

            MessageBox(
                messageType   = "info",
                title         = "Video codec",
                subtitle      = "This widget allows to choose video codec for upscaled video",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        def open_info_keep_frames():
            option_list = KEEP_FRAMES_INFO

            MessageBox(
                messageType   = "info",
                title         = "Keep video frames",
                subtitle      = "This widget allows to choose to keep video frames",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        widget_row = row7

        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        # Video codec
        info_button = create_info_button(self.parent, self.fonts, open_info_video_codec, "Video codec")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_video_codec_from_menu, video_codec_list, self.state.video_codec, width = little_menu_width)
        info_button.place(relx = column_info1,        rely = widget_row, anchor = "center")
        option_menu.place(relx = column_1_4, rely = widget_row, anchor = "center")

        # Keep frames
        info_button = create_info_button(self.parent, self.fonts, open_info_keep_frames, "Keep frames")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_save_frame_from_menu, keep_frames_list, self.state.keep_frames, width = little_menu_width)
        info_button.place(relx = column_info2,      rely = widget_row, anchor = "center")
        option_menu.place(relx = column_2_9, rely = widget_row, anchor = "center")

    def place_video_quality_menu(self) -> None:

        def open_info_video_quality():
            option_list = VIDEO_QUALITY_INFO

            MessageBox(
                messageType   = "info",
                title         = "Video quality",
                subtitle      = "This widget allows to choose the video encoder quality",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        widget_row = row8

        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_video_quality, "Video quality")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_video_quality_from_menu, video_quality_list, self.state.video_quality, width = little_menu_width)
        info_button.place(relx = column_info1,        rely = widget_row, anchor = "center")
        option_menu.place(relx = column_1_4, rely = widget_row, anchor = "center")

    def place_output_path_textbox(self) -> None:

        def open_info_output_path():
            option_list = OUTPUT_PATH_INFO

            MessageBox(
                messageType   = "info",
                title         = "Output path",
                subtitle      = "This widget allows to choose upscaled files path",
                default_value = None,
                option_list   = option_list,
                fonts         = self.fonts
            )

        background    = create_option_background(self.parent)
        info_button   = create_info_button(self.parent, self.fonts, open_info_output_path, "Output path")
        option_menu   = create_text_box_output_path(self.parent, self.fonts, self.selected_output_path)
        active_button = create_active_button(
            master  = self.parent,
            fonts   = self.fonts,
            command = self.open_output_path_action,
            text    = "SELECT",
            icon    = None,
            width   = 60,
            height  = 25
        )

        background.place(   relx = 0.75,                 rely = row10, relwidth = 0.48,  anchor = "center")
        info_button.place(  relx = column_info1,         rely = row10 - 0.003,           anchor = "center")
        active_button.place(relx = column_info1 + 0.052, rely = row10,                   anchor = "center")
        option_menu.place(  relx = column_2 - 0.008,     rely = row10,                   anchor = "center")

    def place_message_label(self) -> None:
        message_label = CTkLabel(
            master        = self.parent,
            textvariable  = self.info_message,
            height        = 25,
            width         = 250,
            font          = self.fonts.bold11,
            fg_color      = "#ffbf00",
            text_color    = "#000000",
            anchor        = "center",
            corner_radius = 4
        )

        triangle_dimension = 14
        zero = 0
        triangle_pointer = CTkCanvas(
            self.parent,
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

    def place_stop_button(self) -> None:
        stop_button = create_active_button(
            master       = self.parent,
            fonts        = self.fonts,
            command      = self.stop_button_command,
            text         = "STOP",
            icon         = self.icons.stop_icon,
            width        = 150,
            height       = 30,
            border_color = "#EC1D1D"
        )
        stop_button.place(relx = 0.62, rely = row11, anchor = "center")

    def place_upscale_button(self) -> None:
        upscale_button = create_active_button(
            master  = self.parent,
            fonts   = self.fonts,
            command = self.upscale_button_command,
            text    = "UPSCALE",
            icon    = self.icons.upscale_icon,
            width   = 150,
            height  = 30
        )
        upscale_button.place(relx = 0.62, rely = row11, anchor = "center")

    # App close ---------------------------

    def save_user_choices_in_json(self) -> None:
        state = self._snapshot_state()
        save_preferences(state, USER_PREFERENCE_PATH)

    def on_app_close(self) -> None:
        # 1. Save user choices in file (StringVars die with the root window)
        self.save_user_choices_in_json()
        if self.extra_save is not None:
            self.extra_save()

        # 2. Destroy app window
        self.window.grab_release()
        self.window.destroy()

        # 3. Stop upscale process and thread check_upscale_step
        self.controller.notify_close()
        if self.extra_shutdown is not None:
            self.extra_shutdown()



# Main functions ---------------------------

def main() -> None:
    multiprocessing_freeze_support()

    ensure_assets()

    if os_path_exists(USER_PREFERENCE_PATH):
        print(f"[{app_name}] Preference file exist")
    else:
        print(f"[{app_name}] Preference file does not exist, using default coded value")

    user_preferences = load_preferences(USER_PREFERENCE_PATH)

    set_appearance_mode("Dark")
    set_default_color_theme("dark-blue")
    apply_app_zoom(float(user_preferences.app_zoom.replace("%", "")) / 100)

    console_sink = ConsoleSink()
    install_console_redirectors(console_sink)

    controller = UpscaleController(log_sink=console_sink)

    window = CTk()
    fonts = load_fonts()
    icons = load_icons()

    tabview = CTkTabview(
        master             = window,
        fg_color           = background_color,
        corner_radius      = 0,
        border_width       = 0,
        anchor             = "nw",
    )
    tabview.pack(side = "top", fill = "both", expand = True)
    tab_quality_scaler = tabview.add("Quality Scaler")
    tab_fluid_frames   = tabview.add("Fluid Frames")
    tab_quality_scaler.configure(fg_color = background_color)
    tab_fluid_frames.configure(fg_color = background_color)

    console_visible = False

    def hide_console() -> None:
        nonlocal console_visible
        if not console_visible:
            return
        console_visible = False
        console_widget.pack_forget()
        window.geometry(f"1000x{WINDOW_BASE_HEIGHT}")

    def show_console() -> None:
        nonlocal console_visible
        if console_visible:
            return
        console_visible = True
        window.geometry(f"1000x{WINDOW_BASE_HEIGHT + CONSOLE_HEIGHT}")
        console_widget.pack(side = "bottom", fill = "x")

    def toggle_console() -> None:
        if console_visible:
            hide_console()
        else:
            show_console()

    console_widget = ConsoleWidget(window, fonts, on_close=hide_console, height=CONSOLE_HEIGHT)

    def drain_console() -> None:
        lines = console_sink.drain(max_items=200)
        if lines:
            console_widget.append_batch(lines)
        window.after(50, drain_console)

    window.after(50, drain_console)

    ff_controller = FrameGenController(log_sink=console_sink)
    ff_preferences = load_ff_preferences(FF_USER_PREFERENCE_PATH)
    ff_panel = FluidFramesPanel(tab_fluid_frames, ff_preferences, ff_controller, fonts, icons)

    App(
        window,
        tab_quality_scaler,
        user_preferences,
        controller,
        fonts,
        icons,
        extra_save        = ff_panel.save_user_choices_in_json,
        extra_shutdown    = ff_controller.notify_close,
        on_toggle_console = toggle_console,
    )
    window.update()
    window.mainloop()


if __name__ == "__main__":
    main()
