/**
 * Plain-browser mock of the pywebview js_api, so `npm run dev` renders
 * standalone without a Python host. Menu/state data mirrors
 * qualityscaler.app.constants / ff_constants and the UIState dataclasses.
 */

import type { InitialState, InfoTexts, Menus, ProbeResult, QsApi, Settings } from "./types";

const SEP = "----";

export const MOCK_OUTPUT_PATH_CODED = "Same path as input files";

const UPSCALE_MENUS: Record<string, string[]> = {
  ai_model: [
    "LVAx2", SEP,
    "RealESR_Gx4", "RealESR_Ax4", SEP,
    "BSRGANx2", "BSRGANx4", SEP,
    "RealESRGANx4", SEP,
    "MSharpx4", SEP,
    "IRCNN_Mx1", "IRCNN_Lx1",
  ],
  blending: ["OFF", "Low", "Medium", "High"],
  ai_multithreading: ["OFF", "2 threads", "4 threads", "6 threads", "8 threads"],
  gpu: ["Auto", "GPU 1", "GPU 2", "GPU 3", "GPU 4"],
  keep_frames: ["OFF", "ON"],
  image_extension: [".png", ".jpg", ".bmp", ".tiff"],
  video_extension: [".mp4", ".mkv", ".avi", ".mov"],
  video_codec: [
    "x264", "x265", SEP,
    "h264_nvenc", "hevc_nvenc", SEP,
    "h264_amf", "hevc_amf", SEP,
    "h264_qsv", "hevc_qsv",
  ],
  video_quality: ["LOW", "MEDIUM", "HIGH"],
  app_zoom: ["50%", "75%", "100%", "125%", "150%", "175%"],
};

const FRAMEGEN_MENUS: Record<string, string[]> = {
  ai_model: ["RIFE", "RIFE_Lite"],
  generation_option: ["x2", "x4", "x8", "Slowmotion x2", "Slowmotion x4", "Slowmotion x8"],
  gpu: ["Auto", "GPU 1", "GPU 2", "GPU 3", "GPU 4"],
  keep_frames: ["OFF", "ON"],
  image_extension: [".jpg", ".png"],
  video_output: [".mp4 (x264)", ".mp4 (x265)", ".avi"],
};

const UPSCALE_STATE: Settings = {
  app_zoom: "100%",
  ai_model: "LVAx2",
  ai_multithreading: "OFF",
  gpu: "Auto",
  keep_frames: "ON",
  image_extension: ".png",
  video_extension: ".mp4",
  video_codec: "x264",
  video_quality: "HIGH",
  blending: "Low",
  output_path: MOCK_OUTPUT_PATH_CODED,
  input_resize_factor: "50",
  output_resize_factor: "100",
  vram_limiter: "4",
  file_list: [],
};

const FRAMEGEN_STATE: Settings = {
  ai_model: "RIFE",
  generation_option: "x2",
  gpu: "Auto",
  keep_frames: "ON",
  image_extension: ".jpg",
  video_output: ".mp4 (x264)",
  output_path: MOCK_OUTPUT_PATH_CODED,
  input_resize_factor: "50",
  cpu_number: "4",
  file_list: [],
};

const INFO_TEXTS: InfoTexts = {
  upscale: {
    ai_model: "Mock help: pick the AI model used for upscaling.",
    blending: "Mock help: blends the AI result with the original image.",
    ai_multithreading: "Mock help: number of frames processed simultaneously.",
    input_resize_factor: "Mock help: resolution percentage fed to the AI.",
    output_resize_factor: "Mock help: resolution percentage of the final output.",
    gpu: "Mock help: GPU used for AI processing.",
    vram_limiter: "Mock help: VRAM limit in GB for the selected GPU.",
    image_extension: "Mock help: output image format.",
    video_extension: "Mock help: output video format.",
    video_codec: "Mock help: codec used to encode output videos.",
    keep_frames: "Mock help: keep extracted frames after upscaling.",
    video_quality: "Mock help: output video quality.",
    output_path: "Mock help: where upscaled files are written.",
  },
  framegen: {
    ai_model: "Mock help: pick the AI model used for frame generation.",
    generation_option: "Mock help: frame generation / slowmotion factor.",
    gpu: "Mock help: GPU used for AI processing.",
    keep_frames: "Mock help: keep extracted frames after processing.",
    image_extension: "Mock help: extracted frame image format.",
    video_output: "Mock help: output video format and codec.",
    input_resize_factor: "Mock help: resolution percentage fed to the AI.",
    cpu_number: "Mock help: CPU cores used for processing.",
    output_path: "Mock help: where generated files are written.",
  },
};

let mockPickCounter = 0;

function mockProbe(paths: string[], settings: Settings): ProbeResult[] {
  const inputScale = Number(settings["input_resize_factor"] ?? 100) || 100;
  const outputScale = Number(settings["output_resize_factor"] ?? 100) || 100;
  const model = String(settings["ai_model"] ?? "LVAx2");
  const factorMatch = model.match(/x([1-4])$/);
  const factor = factorMatch ? Number(factorMatch[1]) : 2;
  const w = 1920;
  const h = 1080;
  const aiInW = Math.round((w * inputScale) / 100);
  const aiInH = Math.round((h * inputScale) / 100);
  const aiOutW = aiInW * factor;
  const aiOutH = aiInH * factor;
  const outW = Math.round((aiOutW * outputScale) / 100);
  const outH = Math.round((aiOutH * outputScale) / 100);
  return paths.map((path) => ({
    path,
    title: path.split(/[\\/]/).pop() ?? path,
    lines: [
      { label: "Time", value: "00:01:30 • 30 fps • 2700 frames" },
      { label: "Resolution", value: `${w}x${h}` },
      { label: "AI input", value: `${aiInW}x${aiInH}` },
      { label: "AI output", value: `${aiOutW}x${aiOutH}` },
      { label: "File output", value: `${outW}x${outH}` },
    ],
    thumb_data_url: null,
  }));
}

/** Build the mock api used when window.pywebview is unavailable. */
export function createMockApi(): QsApi {
  const notify = (msg: string) => {
    if (typeof alert !== "undefined") alert(msg);
  };
  return {
    async get_initial_state(): Promise<InitialState> {
      return {
        upscale: { ...UPSCALE_STATE },
        framegen: { ...FRAMEGEN_STATE },
        version: "0.0.0-dev",
      };
    },
    async get_menus(): Promise<Menus> {
      return { upscale: { ...UPSCALE_MENUS }, framegen: { ...FRAMEGEN_MENUS } };
    },
    async get_info_texts(): Promise<InfoTexts> {
      return INFO_TEXTS;
    },
    async pick_input_files(): Promise<string[]> {
      mockPickCounter += 1;
      return [
        `C:/demo/sample_video_${mockPickCounter}.mp4`,
        `C:/demo/photo_${mockPickCounter}.png`,
      ];
    },
    async pick_output_dir(): Promise<string | null> {
      return "C:/demo/output";
    },
    async probe_files(paths: string[], settings: Settings): Promise<ProbeResult[]> {
      return mockProbe(paths, settings);
    },
    async save_preferences(): Promise<boolean> {
      return true;
    },
    async start_upscale(): Promise<boolean> {
      notify("Mock mode: upscale would start now.");
      return true;
    },
    async stop_upscale(): Promise<boolean> {
      return true;
    },
    async start_framegen(): Promise<boolean> {
      notify("Mock mode: frame generation would start now.");
      return true;
    },
    async stop_framegen(): Promise<boolean> {
      return true;
    },
    async get_ws_url(): Promise<string> {
      return "";
    },
    async open_external(url: string): Promise<void> {
      if (typeof window !== "undefined") window.open(url, "_blank");
    },
  };
}
