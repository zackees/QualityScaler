/** WebSocket client with simple reconnect, feeding parsed frames upstream. */

import { parseWsMessage } from "./wsMessages";
import type { WsMessage } from "./types";

const RECONNECT_DELAY_MS = 1500;
const MAX_ATTEMPTS = 40;

export interface WsConnection {
  close(): void;
}

/**
 * Connect to the event WebSocket. Reconnects on drop (bounded attempts).
 * Returns a handle whose close() stops reconnection.
 */
export function connectWs(url: string, onMessage: (msg: WsMessage) => void): WsConnection {
  let closed = false;
  let attempts = 0;
  let socket: WebSocket | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const open = () => {
    if (closed || attempts >= MAX_ATTEMPTS) return;
    attempts += 1;
    try {
      socket = new WebSocket(url);
    } catch {
      scheduleReconnect();
      return;
    }
    socket.onopen = () => {
      attempts = 0;
    };
    socket.onmessage = (event: MessageEvent) => {
      if (typeof event.data !== "string") return;
      const msg = parseWsMessage(event.data);
      if (msg !== null) onMessage(msg);
    };
    socket.onclose = () => {
      socket = null;
      scheduleReconnect();
    };
    socket.onerror = () => {
      // onclose follows; nothing to do here.
    };
  };

  const scheduleReconnect = () => {
    if (closed || attempts >= MAX_ATTEMPTS) return;
    timer = setTimeout(open, RECONNECT_DELAY_MS);
  };

  open();

  return {
    close() {
      closed = true;
      if (timer !== null) clearTimeout(timer);
      if (socket !== null) {
        socket.onclose = null;
        socket.close();
      }
    },
  };
}
