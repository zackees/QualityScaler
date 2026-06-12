import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from "react";
import { getApi } from "../api";
import { connectWs, type WsConnection } from "../ws";
import {
  formatLogText,
  INITIAL_STATUS,
  LogSink,
  reduceStatus,
  type StatusMap,
  type TabStatus,
} from "../wsMessages";
import { buildRows } from "../util";
import type { InfoTexts, Kind, Menus, ProbeResult, QsApi, Settings } from "../types";
import { ConsolePanel } from "./ConsolePanel";
import { FileList } from "./FileList";
import { InfoModal } from "./InfoModal";
import { MessageBar } from "./MessageBar";
import { ModePanel } from "./ModePanel";

const GITHUB_URL = "https://github.com/Djdefrag/QualityScaler/releases";
const TELEGRAM_URL = "https://linktr.ee/j3ngystudio";
const ZOOM_OPTIONS = ["50%", "75%", "100%", "125%", "150%", "175%"];

type StatusAction =
  | { type: "ws"; msg: Parameters<typeof reduceStatus>[1] }
  | { type: "set"; kind: Kind; status: Partial<TabStatus> };

function statusReducer(state: StatusMap, action: StatusAction): StatusMap {
  if (action.type === "ws") return reduceStatus(state, action.msg);
  return { ...state, [action.kind]: { ...state[action.kind], ...action.status } };
}

export function App() {
  const [api, setApi] = useState<QsApi | null>(null);
  const [version, setVersion] = useState("");
  const [menus, setMenus] = useState<Menus>({ upscale: {}, framegen: {} });
  const [infoTexts, setInfoTexts] = useState<InfoTexts>({ upscale: {}, framegen: {} });
  const [activeTab, setActiveTab] = useState<Kind>("upscale");
  const [settings, setSettings] = useState<Record<Kind, Settings>>({
    upscale: {},
    framegen: {},
  });
  const [paths, setPaths] = useState<Record<Kind, string[]>>({ upscale: [], framegen: [] });
  const [files, setFiles] = useState<Record<Kind, ProbeResult[]>>({
    upscale: [],
    framegen: [],
  });
  const [status, dispatchStatus] = useReducer(statusReducer, INITIAL_STATUS);
  const [modal, setModal] = useState<{ title: string; text: string } | null>(null);
  const [consoleOpen, setConsoleOpen] = useState(false);
  const loadedRef = useRef(false);
  const sink = useMemo(() => new LogSink(), []);

  /* ------------------------------ bootstrap ----------------------------- */

  useEffect(() => {
    let ws: WsConnection | null = null;
    let cancelled = false;
    (async () => {
      const apiInstance = await getApi();
      if (cancelled) return;
      const [initial, menuData, infoData, wsUrl] = await Promise.all([
        apiInstance.get_initial_state(),
        apiInstance.get_menus(),
        apiInstance.get_info_texts(),
        apiInstance.get_ws_url(),
      ]);
      if (cancelled) return;
      setVersion(initial.version);
      setMenus(menuData);
      setInfoTexts(infoData);
      setSettings({ upscale: initial.upscale, framegen: initial.framegen });
      const initialPaths: Record<Kind, string[]> = {
        upscale: asStringList(initial.upscale["file_list"]),
        framegen: asStringList(initial.framegen["file_list"]),
      };
      setPaths(initialPaths);
      setApi(apiInstance);
      // Allow the preference-saving effects to run only after the initial
      // state has been applied.
      requestAnimationFrame(() => {
        loadedRef.current = true;
      });
      if (wsUrl) {
        ws = connectWs(wsUrl, (msg) => {
          if (msg.type === "log") {
            sink.write(formatLogText(msg.text));
          } else {
            dispatchStatus({ type: "ws", msg });
          }
        });
      }
    })();
    return () => {
      cancelled = true;
      ws?.close();
    };
  }, [sink]);

  /* ----------------------- persistence + re-probing ---------------------- */

  useSavePreferences(api, "upscale", settings.upscale, paths.upscale, loadedRef);
  useSavePreferences(api, "framegen", settings.framegen, paths.framegen, loadedRef);
  useProbe(api, "upscale", settings.upscale, paths.upscale, setFiles);
  useProbe(api, "framegen", settings.framegen, paths.framegen, setFiles);

  /* ------------------------------- actions ------------------------------ */

  const updateSetting = useCallback(
    (kind: Kind, key: string, value: string) => {
      setSettings((prev) => ({ ...prev, [kind]: { ...prev[kind], [key]: value } }));
    },
    [],
  );

  const selectFiles = useCallback(async () => {
    if (api === null) return;
    const picked = await api.pick_input_files();
    if (picked.length === 0) return;
    setPaths((prev) => {
      const merged = [...prev[activeTab]];
      for (const p of picked) if (!merged.includes(p)) merged.push(p);
      return { ...prev, [activeTab]: merged };
    });
  }, [api, activeTab]);

  const cleanFiles = useCallback(() => {
    setPaths((prev) => ({ ...prev, [activeTab]: [] }));
    setFiles((prev) => ({ ...prev, [activeTab]: [] }));
  }, [activeTab]);

  const pickOutputDir = useCallback(async () => {
    if (api === null) return;
    const dir = await api.pick_output_dir();
    if (dir !== null) updateSetting(activeTab, "output_path", dir);
  }, [api, activeTab, updateSetting]);

  const start = useCallback(
    async (kind: Kind) => {
      if (api === null) return;
      if (paths[kind].length === 0) {
        dispatchStatus({
          type: "set",
          kind,
          status: { message: "Please select at least one file", tone: "error" },
        });
        return;
      }
      const payload: Settings = { ...settings[kind], file_list: paths[kind] };
      const verb = kind === "upscale" ? "upscaling" : "frame generation";
      dispatchStatus({
        type: "set",
        kind,
        status: { message: `Starting ${verb}...`, tone: "info", running: true },
      });
      const ok = kind === "upscale" ? await api.start_upscale(payload) : await api.start_framegen(payload);
      if (!ok) {
        dispatchStatus({
          type: "set",
          kind,
          status: { message: `Could not start ${verb}`, tone: "error", running: false },
        });
      }
    },
    [api, paths, settings],
  );

  const stop = useCallback(
    async (kind: Kind) => {
      if (api === null) return;
      dispatchStatus({ type: "set", kind, status: { message: "Stopping..." } });
      if (kind === "upscale") await api.stop_upscale();
      else await api.stop_framegen();
    },
    [api],
  );

  const openExternal = useCallback(
    (url: string) => {
      void api?.open_external(url);
    },
    [api],
  );

  /* ------------------------------- render -------------------------------- */

  const appZoom = String(settings.upscale["app_zoom"] ?? "100%");
  const zoomScale = (parseFloat(appZoom) || 100) / 100;
  const rows = useMemo(
    () => ({
      upscale: buildRows(menus.upscale, settings.upscale),
      framegen: buildRows(menus.framegen, settings.framegen),
    }),
    [menus, settings],
  );

  if (api === null) {
    return <div className="file-list-empty">Loading QualityScaler...</div>;
  }

  const tab = activeTab;
  return (
    <div
      id="app-scale"
      style={
        zoomScale === 1
          ? undefined
          : {
              transform: `scale(${zoomScale})`,
              width: `${100 / zoomScale}%`,
              height: `${100 / zoomScale}%`,
            }
      }
    >
      <header className="app-header">
        <span className="app-title">QualityScaler {version}</span>
        <nav className="tab-bar">
          <button
            className={`tab-button${tab === "upscale" ? " active" : ""}`}
            onClick={() => setActiveTab("upscale")}
          >
            Quality Scaler
          </button>
          <button
            className={`tab-button${tab === "framegen" ? " active" : ""}`}
            onClick={() => setActiveTab("framegen")}
          >
            Fluid Frames
          </button>
        </nav>
        <span className="header-spacer" />
        <span className="zoom-row">
          Zoom
          <select
            className="option-input"
            value={appZoom}
            onChange={(e) => updateSetting("upscale", "app_zoom", e.target.value)}
          >
            {(menus.upscale["app_zoom"] ?? ZOOM_OPTIONS).map((z) => (
              <option key={z} value={z}>
                {z}
              </option>
            ))}
          </select>
        </span>
        <button className="link-button" onClick={() => openExternal(TELEGRAM_URL)}>
          Telegram
        </button>
        <button className="link-button" onClick={() => openExternal(GITHUB_URL)}>
          GitHub
        </button>
        <button
          className={`console-toggle${consoleOpen ? " open" : ""}`}
          onClick={() => setConsoleOpen((o) => !o)}
          title="Toggle console"
        >
          &gt;_
        </button>
      </header>
      <main className="app-main">
        <FileList files={files[tab]} onSelectFiles={selectFiles} onClean={cleanFiles} />
        <ModePanel
          kind={tab}
          rows={rows[tab]}
          settings={settings[tab]}
          menus={menus[tab]}
          infoTexts={infoTexts[tab]}
          running={status[tab].running}
          startLabel={tab === "upscale" ? "UPSCALE" : "GENERATE"}
          onSettingChange={(key, value) => updateSetting(tab, key, value)}
          onPickOutputDir={pickOutputDir}
          onShowInfo={(title, text) => setModal({ title, text })}
          onStart={() => void start(tab)}
          onStop={() => void stop(tab)}
        />
      </main>
      <MessageBar status={status[tab]} />
      <ConsolePanel sink={sink} open={consoleOpen} />
      {modal !== null && (
        <InfoModal title={modal.title} text={modal.text} onClose={() => setModal(null)} />
      )}
    </div>
  );
}

/* --------------------------------- hooks ---------------------------------- */

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter((v): v is string => typeof v === "string");
}

/** Persist a tab's settings (debounced) whenever they change after load. */
function useSavePreferences(
  api: QsApi | null,
  kind: Kind,
  settings: Settings,
  paths: string[],
  loadedRef: React.MutableRefObject<boolean>,
) {
  useEffect(() => {
    if (api === null || !loadedRef.current) return;
    const timer = setTimeout(() => {
      void api.save_preferences(kind, { ...settings, file_list: paths });
    }, 500);
    return () => clearTimeout(timer);
  }, [api, kind, settings, paths, loadedRef]);
}

/** Re-probe a tab's files (debounced) when its paths or settings change. */
function useProbe(
  api: QsApi | null,
  kind: Kind,
  settings: Settings,
  paths: string[],
  setFiles: React.Dispatch<React.SetStateAction<Record<Kind, ProbeResult[]>>>,
) {
  useEffect(() => {
    if (api === null) return;
    if (paths.length === 0) {
      setFiles((prev) => (prev[kind].length === 0 ? prev : { ...prev, [kind]: [] }));
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const results = await api.probe_files(paths, settings);
        if (!cancelled) setFiles((prev) => ({ ...prev, [kind]: results }));
      } catch {
        // Probe failures leave the previous info in place.
      }
    }, 300);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [api, kind, settings, paths, setFiles]);
}
