import { describe, expect, it } from "vitest";
import {
  formatLogText,
  INITIAL_STATUS,
  LogSink,
  parseWsMessage,
  reduceStatus,
} from "../src/wsMessages";
import type { WsMessage } from "../src/types";

describe("parseWsMessage", () => {
  it("parses a valid log frame", () => {
    const msg = parseWsMessage('{"type":"log","stream":"stdout","text":"hi"}');
    expect(msg).toEqual({ type: "log", stream: "stdout", text: "hi" });
  });

  it("returns null for malformed JSON", () => {
    expect(parseWsMessage("{not json")).toBeNull();
  });

  it("returns null for unknown types and non-objects", () => {
    expect(parseWsMessage('{"type":"bogus"}')).toBeNull();
    expect(parseWsMessage('"just a string"')).toBeNull();
    expect(parseWsMessage("null")).toBeNull();
  });
});

describe("formatLogText", () => {
  it("appends CRLF to normal lines", () => {
    expect(formatLogText("hello")).toBe("hello\r\n");
  });

  it("preserves carriage-return progress lines without appending", () => {
    expect(formatLogText("frame= 42\r")).toBe("frame= 42\r");
  });

  it("passes ANSI escapes through untouched", () => {
    expect(formatLogText("[31merr[0m")).toBe("[31merr[0m\r\n");
  });
});

describe("reduceStatus", () => {
  it("updates only the matching tab on progress and marks it running", () => {
    const msg: WsMessage = {
      type: "progress",
      kind: "upscale",
      message: "Upscaling frame 10/100",
      file_index: 0,
      fraction: 0.1,
    };
    const next = reduceStatus(INITIAL_STATUS, msg);
    expect(next.upscale.message).toBe("Upscaling frame 10/100 (10%)");
    expect(next.upscale.running).toBe(true);
    expect(next.framegen).toEqual(INITIAL_STATUS.framegen);
  });

  it("omits the percentage when fraction is null", () => {
    const msg: WsMessage = {
      type: "progress",
      kind: "framegen",
      message: "Extracting frames",
      file_index: null,
      fraction: null,
    };
    const next = reduceStatus(INITIAL_STATUS, msg);
    expect(next.framegen.message).toBe("Extracting frames");
  });

  it("completed re-enables and reports success", () => {
    const running = reduceStatus(INITIAL_STATUS, {
      type: "progress",
      kind: "upscale",
      message: "working",
      file_index: null,
      fraction: null,
    });
    const next = reduceStatus(running, {
      type: "completed",
      kind: "upscale",
      output_paths: ["a.mp4"],
    });
    expect(next.upscale).toEqual({
      message: "All files completed! :)",
      tone: "success",
      running: false,
    });
  });

  it("error re-enables with an error tone", () => {
    const next = reduceStatus(INITIAL_STATUS, {
      type: "error",
      kind: "framegen",
      message: "boom",
    });
    expect(next.framegen).toEqual({ message: "Error: boom", tone: "error", running: false });
  });

  it("stopped re-enables with an info tone", () => {
    const next = reduceStatus(INITIAL_STATUS, { type: "stopped", kind: "upscale" });
    expect(next.upscale).toEqual({ message: "Stopped", tone: "info", running: false });
  });

  it("engine_info updates both tabs without touching running flags", () => {
    const running = reduceStatus(INITIAL_STATUS, {
      type: "progress",
      kind: "upscale",
      message: "working",
      file_index: null,
      fraction: null,
    });
    const next = reduceStatus(running, { type: "engine_info", text: "GPU: RTX 4090" });
    expect(next.upscale.message).toBe("GPU: RTX 4090");
    expect(next.upscale.running).toBe(true);
    expect(next.framegen.message).toBe("GPU: RTX 4090");
    expect(next.framegen.running).toBe(false);
  });

  it("log frames do not change status", () => {
    const next = reduceStatus(INITIAL_STATUS, {
      type: "log",
      stream: "stderr",
      text: "noise",
    });
    expect(next).toBe(INITIAL_STATUS);
  });
});

describe("LogSink", () => {
  it("buffers writes until a writer attaches, then streams through", () => {
    const sink = new LogSink();
    const out: string[] = [];
    sink.write("one\r\n");
    sink.write("two\r\n");
    sink.attach((text) => out.push(text));
    expect(out).toEqual(["one\r\n", "two\r\n"]);
    sink.write("three\r\n");
    expect(out).toEqual(["one\r\n", "two\r\n", "three\r\n"]);
  });

  it("buffers again after detach", () => {
    const sink = new LogSink();
    const out: string[] = [];
    sink.attach((text) => out.push(text));
    sink.detach();
    sink.write("late");
    expect(out).toEqual([]);
    sink.attach((text) => out.push(text));
    expect(out).toEqual(["late"]);
  });
});
