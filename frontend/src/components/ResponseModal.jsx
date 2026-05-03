export default function ResponseModal({ text, onClose }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="bg-farm-card border border-farm-border rounded-lg p-4 max-w-lg w-full mx-4 space-y-3"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-bold tracking-[0.1em] uppercase text-farm-sub">Response</span>
          <button onClick={onClose} className="text-farm-muted hover:text-farm-text transition-colors text-sm leading-none">✕</button>
        </div>
        <pre className="font-mono text-xs text-farm-text whitespace-pre-wrap break-all bg-farm-bg border border-farm-border rounded px-3 py-2 max-h-64 overflow-y-auto">
          {text || '—'}
        </pre>
      </div>
    </div>
  )
}
