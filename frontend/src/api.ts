/**
 * Wrapper around window.pywebview.api with a plain-browser mock fallback.
 *
 * Inside the pywebview host the bridge is injected asynchronously, so we
 * wait for the `pywebviewready` event before the first RPC. In a plain
 * browser (`npm run dev`) the event never fires and we fall back to the
 * mock api after a short timeout.
 */

import { createMockApi } from "./mockApi";
import type { QsApi } from "./types";

export { createMockApi };

const READY_TIMEOUT_MS = 1500;

let apiPromise: Promise<QsApi> | null = null;

/** True when running inside a real pywebview host. */
export function hasPywebview(): boolean {
  return typeof window !== "undefined" && window.pywebview?.api !== undefined;
}

function waitForPywebview(timeoutMs: number): Promise<QsApi | null> {
  return new Promise((resolve) => {
    if (typeof window === "undefined") {
      resolve(null);
      return;
    }
    if (window.pywebview?.api) {
      resolve(window.pywebview.api);
      return;
    }
    let settled = false;
    const finish = (api: QsApi | null) => {
      if (settled) return;
      settled = true;
      window.removeEventListener("pywebviewready", onReady);
      resolve(api);
    };
    const onReady = () => finish(window.pywebview?.api ?? null);
    window.addEventListener("pywebviewready", onReady);
    setTimeout(() => finish(window.pywebview?.api ?? null), timeoutMs);
  });
}

/**
 * Resolve the active api: the real pywebview bridge when present, otherwise
 * the standalone mock. The result is memoized for the page lifetime.
 */
export function getApi(timeoutMs: number = READY_TIMEOUT_MS): Promise<QsApi> {
  if (apiPromise === null) {
    apiPromise = waitForPywebview(timeoutMs).then((api) => api ?? createMockApi());
  }
  return apiPromise;
}

/** Test hook: clear the memoized api. */
export function resetApiCache(): void {
  apiPromise = null;
}
