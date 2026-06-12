"""Fluid Frames mode panel: widget layout and event handlers for the
frame-generation tab.

This is a toolkit layer module: customtkinter/tkinter usage is confined to
this module, :mod:`qualityscaler.gui.app` and :mod:`qualityscaler.gui.widgets`.
"""

from __future__ import annotations

from tkinter import StringVar

from customtkinter import CTkButton, CTkCanvas, CTkFrame, CTkLabel, filedialog

from qualityscaler.core import (
    UpscaleProgress,
    UpscaleCompleted,
    UpscaleError,
    UpscaleStopped,
)

from qualityscaler.gui.constants import (
    OUTPUT_PATH_CODED,
    app_name_color,
    background_color,
    gpus_list,
    keep_frames_list,
    supported_video_extensions,
    text_color,
    row0, row1, row2, row3, row4, row5, row10, row11,
    column_info1, column_info2,
    column_1, column_2,
    column_1_4, column_2_9, column_3_5,
    little_textbox_width, little_menu_width,
)
from qualityscaler.gui.controller import format_progress_event
from qualityscaler.gui.ff_constants import (
    FF_AI_models_list,
    FF_image_extension_list,
    FF_video_output_list,
    ff_mode_name,
    generation_options_list,
)
from qualityscaler.gui.ff_controller import FrameGenController, build_settings, validate
from qualityscaler.gui.file_chooser import get_initial_dir, update_last_used_dir
from qualityscaler.gui.ff_info_texts import (
    FF_AI_MODEL_INFO,
    FF_CPU_INFO,
    FF_GENERATION_OPTION_INFO,
    FF_IMAGE_OUTPUT_INFO,
    FF_INPUT_RESOLUTION_INFO,
    FF_KEEP_FRAMES_INFO,
    FF_VIDEO_OUTPUT_INFO,
)
from qualityscaler.gui.ff_preferences import FF_USER_PREFERENCE_PATH, save_ff_preferences
from qualityscaler.gui.ff_state import FFUIState
from qualityscaler.gui.info_texts import GPU_INFO, OUTPUT_PATH_INFO
from qualityscaler.gui.widgets import (
    AppFonts,
    AppIcons,
    FileWidget,
    MessageBox,
    create_active_button,
    create_info_button,
    create_option_background,
    create_option_menu,
    create_text_box,
    create_text_box_output_path,
)


class FluidFramesPanel:
    """Builds and drives the Fluid Frames tab inside the mode tabview."""

    def __init__(
            self,
            parent,
            state: FFUIState,
            controller: FrameGenController,
            fonts: AppFonts,
            icons: AppIcons,
            ) -> None:

        self.parent     = parent
        self.state      = state
        self.controller = controller
        self.fonts      = fonts
        self.icons      = icons

        self.file_widget = None

        self.info_message                 = StringVar()
        self.selected_output_path         = StringVar()
        self.selected_input_resize_factor = StringVar()
        self.selected_cpu_number          = StringVar()

        self.selected_output_path.set(state.output_path)
        self.selected_input_resize_factor.set(state.input_resize_factor)
        self.selected_cpu_number.set(state.cpu_number)

        self.info_message.set("Hi :)")
        self.selected_input_resize_factor.trace_add('write', self.update_file_widget)

        self.place_loadFile_section()

        self.place_mode_name()
        self.place_AI_menu()
        self.place_generation_option_menu()
        self.place_gpu_image_output_menus()
        self.place_video_output_keep_frames_menus()
        self.place_input_resolution_cpu_textboxs()
        self.place_output_path_textbox()

        self.place_message_label()
        self.place_generate_button()

    # State helpers ---------------------------

    def _snapshot_state(self) -> FFUIState:
        self.state.output_path         = self.selected_output_path.get()
        self.state.input_resize_factor = str(self.selected_input_resize_factor.get())
        self.state.cpu_number          = str(self.selected_cpu_number.get())
        if self.file_widget is None:
            self.state.file_list = []
        else:
            self.state.file_list = list(self.file_widget.get_selected_file_list())
        return self.state

    def get_values_for_file_widget(self) -> int:
        try:
            input_resize_factor = int(float(str(self.selected_input_resize_factor.get())))
        except Exception:
            input_resize_factor = 0
        return input_resize_factor

    def update_file_widget(self, *args) -> None:
        if self.file_widget is None:
            return

        input_resize_factor = self.get_values_for_file_widget()

        self.file_widget.clean_file_list()
        self.file_widget.set_upscale_factor(1)
        self.file_widget.set_input_resize_factor(input_resize_factor)
        self.file_widget.set_output_resize_factor(100)
        self.file_widget._create_widgets()

    # Frame generation orchestration ---------------------------

    def generate_button_command(self) -> None:
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
            self.info_message.set("Frame generation stopped")
            self.place_generate_button()

        elif isinstance(actual_event, UpscaleCompleted):
            self.info_message.set("All files completed! :)")
            self.controller.stop_process()
            self.place_generate_button()

        elif isinstance(actual_event, UpscaleError):
            self.info_message.set("Error while generating frames :(")
            self.show_error_message(actual_event.message)
            self.controller.stop_process()
            self.place_generate_button()

        elif isinstance(actual_event, UpscaleProgress):
            self.info_message.set(format_progress_event(actual_event))

        else:
            self.info_message.set(str(actual_event))

    def show_error_message(self, exception: str) -> None:
        MessageBox(
            messageType   = "error",
            title         = "Frame generation error",
            subtitle      = "Please report the error on Github",
            default_value = None,
            option_list   = [f"\n {str(exception)} \n"],
            fonts         = self.fonts
        )

    # File selection ---------------------------

    def open_files_action(self) -> None:

        def check_supported_selected_files(uploaded_file_list: list) -> list:
            return [file for file in uploaded_file_list if any(supported_extension in file for supported_extension in supported_video_extensions)]

        self.info_message.set("Selecting files")

        uploaded_files_list    = list(filedialog.askopenfilenames(initialdir=get_initial_dir()))
        uploaded_files_counter = len(uploaded_files_list)
        update_last_used_dir(uploaded_files_list)

        supported_files_list    = check_supported_selected_files(uploaded_files_list)
        supported_files_counter = len(supported_files_list)

        print("> Uploaded files: " + str(uploaded_files_counter) + " => Supported files: " + str(supported_files_counter))

        if supported_files_counter > 0:
            input_resize_factor = self.get_values_for_file_widget()

            self.file_widget = FileWidget(
                master               = self.parent,
                selected_file_list   = supported_files_list,
                fonts                = self.fonts,
                clear_icon           = self.icons.clear_icon,
                on_clean             = self._on_file_widget_clean,
                upscale_factor       = 1,
                input_resize_factor  = input_resize_factor,
                output_resize_factor = 100,
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

    def select_AI_from_menu(self, selected_option: str) -> None:
        self.state.ai_model = selected_option

    def select_generation_option_from_menu(self, selected_option: str) -> None:
        self.state.generation_option = selected_option

    def select_gpu_from_menu(self, selected_option: str) -> None:
        self.state.gpu = selected_option

    def select_keep_frames_from_menu(self, selected_option: str) -> None:
        self.state.keep_frames = selected_option

    def select_image_extension_from_menu(self, selected_option: str) -> None:
        self.state.image_extension = selected_option

    def select_video_output_from_menu(self, selected_option: str) -> None:
        self.state.video_output = selected_option

    # Place functions ---------------------------

    def place_loadFile_section(self) -> None:
        background = CTkFrame(
            master        = self.parent,
            fg_color      = background_color,
            corner_radius = 0,
            border_width  = 0
        )

        text_drop = (" SUPPORTED FILES \n\n "
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

    def place_mode_name(self) -> None:
        background = CTkFrame(
            master        = self.parent,
            fg_color      = background_color,
            corner_radius = 0,
            border_width  = 0
        )
        mode_name_label = CTkLabel(
            master     = self.parent,
            text       = ff_mode_name,
            fg_color   = background_color,
            bg_color   = background_color,
            text_color = app_name_color,
            font       = self.fonts.bold18,
            anchor     = "w"
        )
        background.place(relx = 0.5, rely = 0.0, relwidth = 0.5, relheight = 1.0)
        mode_name_label.place(relx = column_1 - 0.055, rely = row0, anchor = "center")

    def place_AI_menu(self) -> None:

        def open_info_AI_model():
            MessageBox(
                messageType   = "info",
                title         = "AI model",
                subtitle      = "This widget allows to choose between different RIFE models",
                default_value = None,
                option_list   = FF_AI_MODEL_INFO,
                fonts         = self.fonts
            )

        widget_row = row1
        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_AI_model, "AI model")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_AI_from_menu, FF_AI_models_list, self.state.ai_model)

        info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_3_5,   rely = widget_row, anchor = "center")

    def place_generation_option_menu(self) -> None:

        def open_info_generation_option():
            MessageBox(
                messageType   = "info",
                title         = "AI frame generation",
                subtitle      = "This widget allows to choose between different AI frame generation options",
                default_value = None,
                option_list   = FF_GENERATION_OPTION_INFO,
                fonts         = self.fonts
            )

        widget_row = row2
        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_generation_option, "AI frame generation")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_generation_option_from_menu, generation_options_list, self.state.generation_option)

        info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_3_5,   rely = widget_row, anchor = "center")

    def place_gpu_image_output_menus(self) -> None:

        def open_info_gpu():
            MessageBox(
                messageType   = "info",
                title         = "GPU",
                subtitle      = "This widget allows to select the GPU for AI frame generation",
                default_value = None,
                option_list   = GPU_INFO,
                fonts         = self.fonts
            )

        def open_info_image_output():
            MessageBox(
                messageType   = "info",
                title         = "Image output",
                subtitle      = "This widget allows to choose the extension of generated frames",
                default_value = None,
                option_list   = FF_IMAGE_OUTPUT_INFO,
                fonts         = self.fonts
            )

        widget_row = row3

        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_gpu, "GPU")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_gpu_from_menu, gpus_list, self.state.gpu, width = little_menu_width)
        info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_1_4,   rely = widget_row, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_image_output, "Image output")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_image_extension_from_menu, FF_image_extension_list, self.state.image_extension, width = little_menu_width)
        info_button.place(relx = column_info2, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_2_9,   rely = widget_row, anchor = "center")

    def place_video_output_keep_frames_menus(self) -> None:

        def open_info_video_output():
            MessageBox(
                messageType   = "info",
                title         = "Video output",
                subtitle      = "This widget allows to choose the extension of the generated video",
                default_value = None,
                option_list   = FF_VIDEO_OUTPUT_INFO,
                fonts         = self.fonts
            )

        def open_info_keep_frames():
            MessageBox(
                messageType   = "info",
                title         = "Keep video frames",
                subtitle      = "This widget allows to choose to keep video frames",
                default_value = None,
                option_list   = FF_KEEP_FRAMES_INFO,
                fonts         = self.fonts
            )

        widget_row = row4

        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_video_output, "Video output")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_video_output_from_menu, FF_video_output_list, self.state.video_output, width = little_menu_width)
        info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_1_4,   rely = widget_row, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_keep_frames, "Keep frames")
        option_menu = create_option_menu(self.parent, self.fonts, self.select_keep_frames_from_menu, keep_frames_list, self.state.keep_frames, width = little_menu_width)
        info_button.place(relx = column_info2, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_2_9,   rely = widget_row, anchor = "center")

    def place_input_resolution_cpu_textboxs(self) -> None:

        def open_info_input_resolution():
            MessageBox(
                messageType   = "info",
                title         = "Input resolution %",
                subtitle      = "This widget allows to choose the resolution input to the AI",
                default_value = None,
                option_list   = FF_INPUT_RESOLUTION_INFO,
                fonts         = self.fonts
            )

        def open_info_cpu():
            MessageBox(
                messageType   = "info",
                title         = "Cpu number",
                subtitle      = "This widget allows to choose how many cpus to devote to the app",
                default_value = None,
                option_list   = FF_CPU_INFO,
                fonts         = self.fonts
            )

        widget_row = row5

        background = create_option_background(self.parent)
        background.place(relx = 0.75, rely = widget_row, relwidth = 0.48, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_input_resolution, "Input scale %")
        option_menu = create_text_box(self.parent, self.fonts, self.selected_input_resize_factor, width = little_textbox_width)
        info_button.place(relx = column_info1, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_1_4,   rely = widget_row, anchor = "center")

        info_button = create_info_button(self.parent, self.fonts, open_info_cpu, "CPU number")
        option_menu = create_text_box(self.parent, self.fonts, self.selected_cpu_number, width = little_textbox_width)
        info_button.place(relx = column_info2, rely = widget_row, anchor = "center")
        option_menu.place(relx = column_2_9,   rely = widget_row, anchor = "center")

    def place_output_path_textbox(self) -> None:

        def open_info_output_path():
            MessageBox(
                messageType   = "info",
                title         = "Output path",
                subtitle      = "This widget allows to choose generated files path",
                default_value = None,
                option_list   = OUTPUT_PATH_INFO,
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

    def place_generate_button(self) -> None:
        generate_button = create_active_button(
            master  = self.parent,
            fonts   = self.fonts,
            command = self.generate_button_command,
            text    = "GENERATE",
            icon    = self.icons.upscale_icon,
            width   = 150,
            height  = 30
        )
        generate_button.place(relx = 0.62, rely = row11, anchor = "center")

    # App close ---------------------------

    def save_user_choices_in_json(self) -> None:
        state = self._snapshot_state()
        save_ff_preferences(state, FF_USER_PREFERENCE_PATH)
