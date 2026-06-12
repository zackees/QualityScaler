"""Info-popup prose shown by the MessageBox widgets.

Text is preserved byte-for-byte from the original inline closures in
QualityScaler.py. Toolkit-free on purpose.
"""

from __future__ import annotations


AI_MODEL_INFO = [
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

AI_BLENDING_INFO = [
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

AI_MULTITHREADING_INFO = [
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

INPUT_RESOLUTION_INFO = [
    " A high value (>50%) will create high quality photos/videos but will be slower",
    " While a low value (<50%) will create good quality photos/videos but will much faster",

    " \n For example, for a 1080p (1920x1080) image/video\n" +
    " - Input scale 25% => input to AI 270p (480x270)\n" +
    " - Input scale 50% => input to AI 540p (960x540)\n" +
    " - Input scale 75% => input to AI 810p (1440x810)\n" +
    " - Input scale 100% => input to AI 1080p (1920x1080) \n",
]

OUTPUT_RESOLUTION_INFO = [
    " 100% keeps the exact resolution produced by the AI upscaling",
    " A lower value (<100%) will downscale the AI result to a smaller resolution, saving space and processing time",
    " A higher value (>100%) will further upscale the AI output, increasing size but not adding real details",

    "\n For example, if the AI generates a 4K (3840x2160) image/video\n" +
    " - Output scale 50%  => final output 1920x1080 (downscaled)\n" +
    " - Output scale 100% => final output 3840x2160 (AI native)\n" +
    " - Output scale 200% => final output 7680x4320 (8K, interpolated)\n",
]

GPU_INFO = [
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

VRAM_LIMITER_INFO = [
    " Make sure to enter the correct value based on the selected GPU's VRAM",
    " Setting a value higher than the available VRAM may cause upscale failure",
    " For integrated GPUs (Intel HD series - Vega 3, 5, 7), select 2 GB to avoid issues",
]

IMAGE_OUTPUT_INFO = [
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

VIDEO_EXTENSION_INFO = [
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

VIDEO_CODEC_INFO = [
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

KEEP_FRAMES_INFO = [
    "\n ON \n" +
    " The app does NOT delete the video frames after creating the upscaled video \n",

    "\n OFF \n" +
    " The app deletes the video frames after creating the upscaled video \n"
]

VIDEO_QUALITY_INFO = [
    "\n LOW \n" +
    " Smaller files, visibly lower quality \n",

    "\n MEDIUM \n" +
    " Balanced size and quality \n",

    "\n HIGH \n" +
    " Best quality, larger files (x264 crf 18) \n"
]

OUTPUT_PATH_INFO = [
      "\n The default path is defined by the input files."
    + "\n For example: selecting a file from the Download folder,"
    + "\n the app will save upscaled files in the Download folder \n",

    " Otherwise it is possible to select the desired path using the SELECT button",
]
