import { MENU_SEPARATOR, type RowSpec } from "../util";

interface OptionRowProps {
  spec: RowSpec;
  value: string;
  options: string[] | undefined;
  onChange: (value: string) => void;
  onInfo: (() => void) | null;
}

/** One settings row: label, "?" info button, and a dropdown or text box. */
export function OptionRow({ spec, value, options, onChange, onInfo }: OptionRowProps) {
  return (
    <div className="option-row">
      <button
        className="info-button"
        onClick={onInfo ?? undefined}
        disabled={onInfo === null}
        title={`About ${spec.label}`}
        aria-label={`About ${spec.label}`}
      >
        ?
      </button>
      <span className="option-label">{spec.label}</span>
      {spec.kind === "menu" && options !== undefined ? (
        <select
          className="option-input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        >
          {options.map((opt, i) =>
            opt === MENU_SEPARATOR ? (
              <option key={`sep-${i}`} disabled value={opt}>
                ────────
              </option>
            ) : (
              <option key={`${opt}-${i}`} value={opt}>
                {opt}
              </option>
            ),
          )}
        </select>
      ) : (
        <input
          className="option-input"
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </div>
  );
}
