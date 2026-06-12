import { useEffect, useRef } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import type { LogSink } from "../wsMessages";

interface ConsolePanelProps {
  sink: LogSink;
  open: boolean;
}

/** Collapsible bottom console hosting the xterm.js terminal. */
export function ConsolePanel({ sink, open }: ConsolePanelProps) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (host === null) return;
    const term = new Terminal({
      convertEol: false,
      scrollback: 10000,
      fontSize: 13,
      fontFamily: "Consolas, 'Cascadia Mono', monospace",
      theme: {
        background: "#000000",
        foreground: "#e0e0e0",
      },
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(host);
    fit.fit();
    termRef.current = term;
    fitRef.current = fit;
    sink.attach((text) => term.write(text));

    const onResize = () => fit.fit();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      sink.detach();
      term.dispose();
      termRef.current = null;
      fitRef.current = null;
    };
  }, [sink]);

  useEffect(() => {
    if (open) {
      // Re-fit after the panel becomes visible.
      requestAnimationFrame(() => fitRef.current?.fit());
    }
  }, [open]);

  return (
    <div className={`console-panel${open ? "" : " hidden"}`}>
      <div className="console-host" ref={hostRef} />
    </div>
  );
}
