"""Info popup texts for the Fluid Frames mode widgets.

Ported from FluidFrames.RIFE. Toolkit-free.
"""

from __future__ import annotations

FF_AI_MODEL_INFO = [
    "\n RIFE\n"
    + "   • The complete RIFE AI model\n"
    + "   • Excellent frame generation quality\n"
    + "   • Recommended GPUs with VRAM >= 4GB\n",

    "\n RIFE_Lite\n"
    + "   • Lightweight version of RIFE AI model\n"
    + "   • High frame generation quality\n"
    + "   • 10% faster than full model\n"
    + "   • Use less GPU VRAM memory\n"
    + "   • Recommended for GPUs with VRAM < 4GB \n",
]

FF_GENERATION_OPTION_INFO = [
    "\n FRAME GENERATION\n"
    + "   • x2 - doubles video framerate • 30fps => 60fps\n"
    + "   • x4 - quadruples video framerate • 30fps => 120fps\n"
    + "   • x8 - octuplicate video framerate • 30fps => 240fps\n",

    "\n SLOWMOTION (no audio)\n"
    + "   • Slowmotion x2 - slowmotion effect by a factor of 2\n"
    + "   • Slowmotion x4 - slowmotion effect by a factor of 4\n"
    + "   • Slowmotion x8 - slowmotion effect by a factor of 8\n",
]

FF_IMAGE_OUTPUT_INFO = [
    " \n JPG\n  • good quality\n  • fast and lightweight file\n",
    " \n PNG\n  • very good quality\n  • slow and heavy file\n  • supports transparent images\n",
]

FF_VIDEO_OUTPUT_INFO = [
    "\n MP4 (x264)\n   • produces well compressed video using x264 codec\n",
    "\n MP4 (x265)\n   • produces well compressed video using x265 codec\n",
    "\n AVI\n   • produces the highest quality video\n   • the video produced can also be of large size\n",
]

FF_KEEP_FRAMES_INFO = [
    "\n ON \n The app does not delete the video frames after creating the frame-generated video \n",
    "\n OFF \n The app deletes the video frames after creating the frame-generated video \n",
]

FF_INPUT_RESOLUTION_INFO = [
    " A high value (>70%) will create high quality videos but will be slower",
    " While a low value (<40%) will create good quality videos but will be much faster",

    " \n For example, for a 1080p (1920x1080) video\n"
    + " • Input resolution 25% => input to AI 270p (480x270)\n"
    + " • Input resolution 50% => input to AI 540p (960x540)\n"
    + " • Input resolution 75% => input to AI 810p (1440x810)\n"
    + " • Input resolution 100% => input to AI 1080p (1920x1080) \n",
]

FF_CPU_INFO = [
    " When possible the app will use the number of cpus selected",
    "\n Currently this value is used for: \n  • video frames extraction \n  • video encoding \n",
]
