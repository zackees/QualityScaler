/** Small pure helpers shared across the app. */

/** Debounce a function; trailing-edge only. */
export function debounce<A extends unknown[]>(
  fn: (...args: A) => void,
  waitMs: number,
): ((...args: A) => void) & { cancel: () => void } {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const wrapped = (...args: A) => {
    if (timer !== null) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      fn(...args);
    }, waitMs);
  };
  wrapped.cancel = () => {
    if (timer !== null) clearTimeout(timer);
    timer = null;
  };
  return wrapped;
}

const ACRONYMS: Record<string, string> = {
  ai: "AI",
  gpu: "GPU",
  cpu: "CPU",
  vram: "VRAM",
};

/** Turn a snake_case settings key into a human-facing row label. */
export function labelForKey(key: string): string {
  const words = key.split("_").map((word, i) => {
    const lower = word.toLowerCase();
    if (lower in ACRONYMS) return ACRONYMS[lower];
    if (i === 0) return word.charAt(0).toUpperCase() + word.slice(1);
    return word;
  });
  return words.join(" ");
}

/** Settings keys that are not rendered as generic option rows. */
export const NON_ROW_KEYS = new Set(["output_path", "file_list", "app_zoom"]);

export const MENU_SEPARATOR = "----";

export interface RowSpec {
  key: string;
  label: string;
  kind: "menu" | "text";
}

/** Friendly overrides for known settings keys (matches the CTk GUI labels). */
const LABEL_OVERRIDES: Record<string, string> = {
  ai_model: "AI model",
  blending: "AI blending",
  ai_multithreading: "AI multithreading",
  input_resize_factor: "Input scale %",
  output_resize_factor: "Output scale %",
  gpu: "GPU",
  vram_limiter: "GPU VRAM (GB)",
  image_extension: "Image output",
  video_extension: "Video output",
  video_codec: "Video codec",
  keep_frames: "Keep frames",
  video_quality: "Video quality",
  generation_option: "AI frame generation",
  video_output: "Video output",
  cpu_number: "CPU number",
};

/** Preferred row ordering; unknown keys are appended in API order. */
const KEY_ORDER = [
  "ai_model",
  "blending",
  "generation_option",
  "ai_multithreading",
  "input_resize_factor",
  "output_resize_factor",
  "gpu",
  "vram_limiter",
  "cpu_number",
  "image_extension",
  "video_extension",
  "video_output",
  "video_codec",
  "keep_frames",
  "video_quality",
];

/**
 * Build the option rows for one tab, driven by the keys the API returns:
 * every menu key becomes a dropdown, every remaining scalar settings key
 * becomes a text box. Special keys (output path, file list, zoom) excluded.
 */
export function buildRows(
  menus: Record<string, string[]>,
  state: Record<string, unknown>,
): RowSpec[] {
  const keys: string[] = [];
  for (const key of Object.keys(menus)) {
    if (!NON_ROW_KEYS.has(key)) keys.push(key);
  }
  for (const key of Object.keys(state)) {
    if (NON_ROW_KEYS.has(key) || keys.includes(key)) continue;
    if (typeof state[key] !== "string") continue;
    keys.push(key);
  }
  keys.sort((a, b) => {
    const ia = KEY_ORDER.indexOf(a);
    const ib = KEY_ORDER.indexOf(b);
    if (ia === -1 && ib === -1) return 0;
    if (ia === -1) return 1;
    if (ib === -1) return -1;
    return ia - ib;
  });
  return keys.map((key) => ({
    key,
    label: LABEL_OVERRIDES[key] ?? labelForKey(key),
    kind: key in menus ? "menu" : "text",
  }));
}
