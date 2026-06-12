import { useState } from "react";
import type { ProbeResult } from "../types";

interface FileItemProps {
  file: ProbeResult;
}

/** One file card: thumbnail + title + the per-file info reveal. */
function FileItem({ file }: FileItemProps) {
  const [revealed, setRevealed] = useState(true);
  return (
    <div className="file-card">
      <div className="file-card-head">
        {file.thumb_data_url ? (
          <img className="file-thumb" src={file.thumb_data_url} alt="" />
        ) : (
          <div className="file-thumb placeholder">▶</div>
        )}
        <span className="file-title">{file.title}</span>
        <button
          className="file-info-toggle"
          onClick={() => setRevealed((r) => !r)}
          title={revealed ? "Hide file info" : "Show file info"}
          aria-label={revealed ? "Hide file info" : "Show file info"}
        >
          {revealed ? "−" : "i"}
        </button>
      </div>
      {revealed && (
        <div className="file-info-lines">
          {file.lines.map((line, i) => (
            <FileInfoLine key={`${line.label}-${i}`} label={line.label} value={line.value} />
          ))}
        </div>
      )}
    </div>
  );
}

function FileInfoLine({ label, value }: { label: string; value: string }) {
  return (
    <>
      <span className="file-info-label">{label}</span>
      <span className="file-info-value">{value}</span>
    </>
  );
}

interface FileListProps {
  files: ProbeResult[];
  onSelectFiles: () => void;
  onClean: () => void;
}

/** Left-hand file panel with SELECT FILES + CLEAN buttons and file cards. */
export function FileList({ files, onSelectFiles, onClean }: FileListProps) {
  return (
    <aside className="file-panel">
      <div className="file-panel-header">
        <span className="file-panel-title">Selected files</span>
        <button className="btn" onClick={onSelectFiles}>
          SELECT FILES
        </button>
        <button className="btn secondary" onClick={onClean} disabled={files.length === 0}>
          CLEAN
        </button>
      </div>
      <div className="file-list">
        {files.length === 0 ? (
          <div className="file-list-empty">
            No files selected.
            <br />
            Use SELECT FILES to add images and videos.
          </div>
        ) : (
          files.map((file) => <FileItem key={file.path} file={file} />)
        )}
      </div>
    </aside>
  );
}
