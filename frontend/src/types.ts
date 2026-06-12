/** Shared types mirroring the Python RPC + WebSocket contract. */

export type Kind = "upscale" | "framegen";

/** Generic settings bag; field names mirror the Python UIState dataclasses. */
export type Settings = Record<string, unknown>;

export interface InitialState {
  upscale: Settings;
  framegen: Settings;
  version: string;
}

export interface Menus {
  upscale: Record<string, string[]>;
  framegen: Record<string, string[]>;
}

export interface InfoTexts {
  upscale: Record<string, string>;
  framegen: Record<string, string>;
}

export interface ProbeLine {
  label: string;
  value: string;
}

export interface ProbeResult {
  path: string;
  title: string;
  lines: ProbeLine[];
  thumb_data_url: string | null;
}

/** Python-side js_api surface exposed at window.pywebview.api. */
export interface QsApi {
  get_initial_state(): Promise<InitialState>;
  get_menus(): Promise<Menus>;
  get_info_texts(): Promise<InfoTexts>;
  pick_input_files(): Promise<string[]>;
  pick_output_dir(): Promise<string | null>;
  probe_files(paths: string[], settings: Settings): Promise<ProbeResult[]>;
  save_preferences(kind: Kind, state: Settings): Promise<boolean>;
  start_upscale(settings: Settings): Promise<boolean>;
  stop_upscale(): Promise<boolean>;
  start_framegen(settings: Settings): Promise<boolean>;
  stop_framegen(): Promise<boolean>;
  get_ws_url(): Promise<string>;
  open_external(url: string): Promise<void>;
  report_renderer_error(message: string): Promise<void>;
}

declare global {
  interface Window {
    pywebview?: { api: QsApi };
  }
}

/* ---------------------------- WebSocket frames ---------------------------- */

export interface WsLogMessage {
  type: "log";
  stream: "stdout" | "stderr" | "info";
  text: string;
}

export interface WsProgressMessage {
  type: "progress";
  kind: Kind;
  message: string;
  file_index: number | null;
  fraction: number | null;
}

export interface WsCompletedMessage {
  type: "completed";
  kind: Kind;
  output_paths: string[];
}

export interface WsErrorMessage {
  type: "error";
  kind: Kind;
  message: string;
}

export interface WsStoppedMessage {
  type: "stopped";
  kind: Kind;
}

export interface WsEngineInfoMessage {
  type: "engine_info";
  text: string;
}

export type WsMessage =
  | WsLogMessage
  | WsProgressMessage
  | WsCompletedMessage
  | WsErrorMessage
  | WsStoppedMessage
  | WsEngineInfoMessage;
