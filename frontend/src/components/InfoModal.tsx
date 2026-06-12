interface InfoModalProps {
  title: string;
  text: string;
  onClose: () => void;
}

/** Modal shown by the "?" info buttons, rendering the Python help prose. */
export function InfoModal({ title, text, onClose }: InfoModalProps) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">{title}</span>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        <div className="modal-body">{text}</div>
      </div>
    </div>
  );
}
