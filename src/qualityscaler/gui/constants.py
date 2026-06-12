"""Static GUI constants: branding, menu option lists, and layout geometry.

This module must stay free of third-party imports so it can be loaded in the
headless unit-test environment.
"""

from __future__ import annotations


app_name   = "QualityScaler"
githubme   = "https://github.com/Djdefrag/QualityScaler/releases"
telegramme = "https://linktr.ee/j3ngystudio"

app_name_color          = "#F274EE"
background_color        = "#000000"
widget_background_color = "#181818"
text_color              = "#B8B8B8"


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

OUTPUT_PATH_CODED = "Same path as input files"


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
