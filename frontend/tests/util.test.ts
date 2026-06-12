import { describe, expect, it, vi } from "vitest";
import { buildRows, debounce, labelForKey } from "../src/util";

describe("labelForKey", () => {
  it("uppercases known acronyms", () => {
    expect(labelForKey("ai_model")).toBe("AI model");
    expect(labelForKey("gpu")).toBe("GPU");
    expect(labelForKey("cpu_number")).toBe("CPU number");
    expect(labelForKey("vram_limiter")).toBe("VRAM limiter");
  });

  it("capitalizes the first plain word", () => {
    expect(labelForKey("keep_frames")).toBe("Keep frames");
  });
});

describe("buildRows", () => {
  it("makes menu rows for menu keys and text rows for the rest", () => {
    const rows = buildRows(
      { ai_model: ["A", "B"], gpu: ["Auto"] },
      {
        ai_model: "A",
        gpu: "Auto",
        input_resize_factor: "50",
        output_path: "somewhere",
        file_list: [],
        app_zoom: "100%",
      },
    );
    const byKey = Object.fromEntries(rows.map((r) => [r.key, r]));
    expect(byKey["ai_model"].kind).toBe("menu");
    expect(byKey["gpu"].kind).toBe("menu");
    expect(byKey["input_resize_factor"].kind).toBe("text");
    // Special keys are excluded from generic rows.
    expect(byKey["output_path"]).toBeUndefined();
    expect(byKey["file_list"]).toBeUndefined();
    expect(byKey["app_zoom"]).toBeUndefined();
  });

  it("orders known keys per the CTk layout", () => {
    const rows = buildRows(
      { keep_frames: ["ON"], ai_model: ["A"] },
      { vram_limiter: "4", ai_model: "A", keep_frames: "ON" },
    );
    const keys = rows.map((r) => r.key);
    expect(keys.indexOf("ai_model")).toBeLessThan(keys.indexOf("vram_limiter"));
    expect(keys.indexOf("vram_limiter")).toBeLessThan(keys.indexOf("keep_frames"));
  });
});

describe("debounce", () => {
  it("fires once on the trailing edge with the last args", () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const d = debounce(fn, 100);
    d(1);
    d(2);
    d(3);
    vi.advanceTimersByTime(99);
    expect(fn).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1);
    expect(fn).toHaveBeenCalledTimes(1);
    expect(fn).toHaveBeenCalledWith(3);
    vi.useRealTimers();
  });

  it("cancel prevents the pending call", () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const d = debounce(fn, 100);
    d("x");
    d.cancel();
    vi.advanceTimersByTime(200);
    expect(fn).not.toHaveBeenCalled();
    vi.useRealTimers();
  });
});
