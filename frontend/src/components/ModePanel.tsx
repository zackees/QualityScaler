import type { Kind, Settings } from "../types";
import type { RowSpec } from "../util";
import { OptionRow } from "./OptionRow";

interface ModePanelProps {
  kind: Kind;
  rows: RowSpec[];
  settings: Settings;
  menus: Record<string, string[]>;
  infoTexts: Record<string, string>;
  running: boolean;
  startLabel: string;
  onSettingChange: (key: string, value: string) => void;
  onPickOutputDir: () => void;
  onShowInfo: (title: string, text: string) => void;
  onStart: () => void;
  onStop: () => void;
}

/** Right-hand settings panel for one tab (Quality Scaler / Fluid Frames). */
export function ModePanel({
  kind,
  rows,
  settings,
  menus,
  infoTexts,
  running,
  startLabel,
  onSettingChange,
  onPickOutputDir,
  onShowInfo,
  onStart,
  onStop,
}: ModePanelProps) {
  const outputPath = String(settings["output_path"] ?? "");
  const outputInfo = infoTexts["output_path"];
  return (
    <section className="settings-panel" data-kind={kind}>
      {rows.map((spec) => {
        const info = infoTexts[spec.key];
        return (
          <OptionRow
            key={spec.key}
            spec={spec}
            value={String(settings[spec.key] ?? "")}
            options={menus[spec.key]}
            onChange={(value) => onSettingChange(spec.key, value)}
            onInfo={info !== undefined ? () => onShowInfo(spec.label, info) : null}
          />
        );
      })}
      <div className="option-row">
        <button
          className="info-button"
          disabled={outputInfo === undefined}
          onClick={
            outputInfo !== undefined ? () => onShowInfo("Output path", outputInfo) : undefined
          }
          title="About Output path"
          aria-label="About Output path"
        >
          ?
        </button>
        <span className="option-label">Output path</span>
        <span className="output-path-display" title={outputPath}>
          {outputPath}
        </span>
        <button className="btn secondary" onClick={onPickOutputDir}>
          SELECT
        </button>
      </div>
      {running ? (
        <button className="btn start-button stop" onClick={onStop}>
          STOP
        </button>
      ) : (
        <button className="btn start-button" onClick={onStart}>
          {startLabel}
        </button>
      )}
    </section>
  );
}
