/** Pure logic for handling WebSocket frames — kept toolkit-free for tests. */

import type { Kind, WsMessage } from "./types";

export type Tone = "info" | "success" | "error";

export interface TabStatus {
  message: string;
  tone: Tone;
  running: boolean;
}

export interface StatusMap {
  upscale: TabStatus;
  framegen: TabStatus;
}

export const INITIAL_STATUS: StatusMap = {
  upscale: { message: "Hi :)", tone: "info", running: false },
  framegen: { message: "Hi :)", tone: "info", running: false },
};

/** Parse one raw WebSocket payload; returns null on malformed input. */
export function parseWsMessage(raw: string): WsMessage | null {
  let data: unknown;
  try {
    data = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof data !== "object" || data === null) return null;
  const type = (data as { type?: unknown }).type;
  if (
    type === "log" ||
    type === "progress" ||
    type === "completed" ||
    type === "error" ||
    type === "stopped" ||
    type === "engine_info"
  ) {
    return data as WsMessage;
  }
  return null;
}

/**
 * Format a log frame's text for xterm: append CRLF unless the text ends with
 * a bare carriage return (ffmpeg-style in-place progress updates).
 */
export function formatLogText(text: string): string {
  if (text.endsWith("\r")) return text;
  return text + "\r\n";
}

function withKind(map: StatusMap, kind: Kind, status: TabStatus): StatusMap {
  return { ...map, [kind]: status };
}

/** Reduce a WebSocket frame into the per-tab status-bar state. */
export function reduceStatus(map: StatusMap, msg: WsMessage): StatusMap {
  switch (msg.type) {
    case "progress": {
      const pct =
        msg.fraction !== null && msg.fraction !== undefined
          ? ` (${Math.round(msg.fraction * 100)}%)`
          : "";
      return withKind(map, msg.kind, {
        message: `${msg.message}${pct}`,
        tone: "info",
        running: true,
      });
    }
    case "completed":
      return withKind(map, msg.kind, {
        message: "All files completed! :)",
        tone: "success",
        running: false,
      });
    case "error":
      return withKind(map, msg.kind, {
        message: `Error: ${msg.message}`,
        tone: "error",
        running: false,
      });
    case "stopped":
      return withKind(map, msg.kind, {
        message: "Stopped",
        tone: "info",
        running: false,
      });
    case "engine_info":
      // Engine info is not tied to a tab; surface it on both status bars
      // without changing the running flags.
      return {
        upscale: { ...map.upscale, message: msg.text, tone: "info" },
        framegen: { ...map.framegen, message: msg.text, tone: "info" },
      };
    case "log":
      return map;
  }
}

/**
 * Buffers terminal output until an xterm instance attaches, then streams
 * writes straight through. Lets the WebSocket outlive console mount cycles.
 */
export class LogSink {
  private buffer: string[] = [];
  private writer: ((text: string) => void) | null = null;

  write(text: string): void {
    if (this.writer) {
      this.writer(text);
    } else {
      this.buffer.push(text);
      // Cap memory if the console is never opened.
      if (this.buffer.length > 5000) this.buffer.splice(0, this.buffer.length - 5000);
    }
  }

  attach(writer: (text: string) => void): void {
    this.writer = writer;
    for (const text of this.buffer) writer(text);
    this.buffer = [];
  }

  detach(): void {
    this.writer = null;
  }
}
