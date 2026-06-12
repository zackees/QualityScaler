import { describe, expect, it } from "vitest";
import { createMockApi, getApi, hasPywebview, resetApiCache } from "../src/api";

describe("mock api fallback", () => {
  it("hasPywebview is false outside the webview host", () => {
    expect(hasPywebview()).toBe(false);
  });

  it("getApi falls back to the mock when pywebview is absent", async () => {
    resetApiCache();
    const api = await getApi(10);
    const initial = await api.get_initial_state();
    expect(typeof initial.version).toBe("string");
    expect(initial.upscale["ai_model"]).toBeDefined();
    expect(initial.framegen["ai_model"]).toBeDefined();
  });

  it("mock menus cover every required upscale option row", async () => {
    const api = createMockApi();
    const menus = await api.get_menus();
    for (const key of [
      "ai_model",
      "blending",
      "ai_multithreading",
      "gpu",
      "image_extension",
      "video_extension",
      "video_codec",
      "keep_frames",
      "video_quality",
    ]) {
      expect(menus.upscale[key], `missing upscale menu: ${key}`).toBeInstanceOf(Array);
      expect(menus.upscale[key].length).toBeGreaterThan(0);
    }
    for (const key of [
      "ai_model",
      "generation_option",
      "gpu",
      "keep_frames",
      "image_extension",
      "video_output",
    ]) {
      expect(menus.framegen[key], `missing framegen menu: ${key}`).toBeInstanceOf(Array);
    }
  });

  it("mock probe returns the required info-reveal lines and reacts to settings", async () => {
    const api = createMockApi();
    const [low] = await api.probe_files(["C:/demo/a.mp4"], {
      ai_model: "LVAx2",
      input_resize_factor: "50",
      output_resize_factor: "100",
    });
    const labels = low.lines.map((l) => l.label);
    expect(labels).toContain("AI input");
    expect(labels).toContain("AI output");
    expect(labels).toContain("File output");
    const aiInputLow = low.lines.find((l) => l.label === "AI input")!.value;

    const [high] = await api.probe_files(["C:/demo/a.mp4"], {
      ai_model: "LVAx2",
      input_resize_factor: "100",
      output_resize_factor: "100",
    });
    const aiInputHigh = high.lines.find((l) => l.label === "AI input")!.value;
    expect(aiInputLow).not.toBe(aiInputHigh);
  });
});
