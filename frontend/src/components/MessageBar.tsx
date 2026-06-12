import type { TabStatus } from "../wsMessages";

/** Yellow status message bar (red on error, green on completion). */
export function MessageBar({ status }: { status: TabStatus }) {
  const toneClass = status.tone === "info" ? "" : ` ${status.tone}`;
  return <div className={`message-bar${toneClass}`}>{status.message}</div>;
}
