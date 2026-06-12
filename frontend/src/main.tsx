import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./components/App";
import "./styles/app.css";

// Forward renderer errors to the Python log (issue #70: a silent JS failure
// must never leave a blank window unexplained). Installed before React mounts;
// errors raised before the pywebview bridge is injected are buffered and
// flushed on `pywebviewready`.
const pendingErrors: string[] = [];

function sendRendererError(text: string): void {
  try {
    const send = window.pywebview?.api?.report_renderer_error;
    if (send) {
      void send.call(window.pywebview!.api, text);
    } else if (pendingErrors.length < 50) {
      pendingErrors.push(text);
    }
  } catch {
    // Best effort only; never throw from the error handler itself.
  }
}

window.addEventListener(
  "pywebviewready",
  () => {
    if (!window.pywebview?.api?.report_renderer_error) return;
    while (pendingErrors.length > 0) sendRendererError(pendingErrors.shift()!);
  },
  { once: true },
);

window.onerror = (message, source, lineno, colno, error) => {
  sendRendererError(
    `${String(message)} (${source ?? "?"}:${lineno ?? 0}:${colno ?? 0})` +
      (error?.stack ? `\n${error.stack}` : ""),
  );
};

window.addEventListener("unhandledrejection", (event) => {
  const reason = event.reason;
  const text =
    reason instanceof Error ? (reason.stack ?? reason.message) : String(reason);
  sendRendererError(`Unhandled promise rejection: ${text}`);
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
