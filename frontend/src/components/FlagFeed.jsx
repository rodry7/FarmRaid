const STATUS_CFG = {
  accepted:  { color: '#00ff41', label: 'ACCEPTED',  glow: true  },
  rejected:  { color: '#ff2040', label: 'REJECTED',  glow: false },
  pending:   { color: '#666666', label: 'PENDING',   glow: false },
  queued:    { color: '#666666', label: 'QUEUED',    glow: false },
  duplicate: { color: '#444444', label: 'DUPLICATE', glow: false },
  expired:   { color: '#ffaa00', label: 'TOO OLD',   glow: false },
  error:     { color: '#ff2040', label: 'ERROR',     glow: false },
}

export default function FlagFeed({ events }) {
  return (
    <div className="h-80 overflow-y-auto bg-farm-bg border border-farm-border rounded-lg p-3 font-mono text-xs flex flex-col-reverse gap-0.5">
      {events.length === 0 ? (
        <div className="text-farm-sub text-center py-8">Waiting for flags...</div>
      ) : (
        events.slice().reverse().map((e, i) => {
          const cfg = STATUS_CFG[e.status] || { color: '#666666', label: e.status?.toUpperCase(), glow: false }
          return (
            <div
              key={i}
              className="flex gap-2 items-center"
              style={{ animation: i === 0 ? 'fadeInRow 0.2s ease-out' : undefined }}
            >
              <span
                className="w-[72px] shrink-0 font-semibold"
                style={{
                  color: cfg.color,
                  textShadow: cfg.glow ? `0 0 8px ${cfg.color}88` : undefined,
                }}
              >
                [{cfg.label}]
              </span>
              <span
                className="text-farm-text truncate"
                style={{ textShadow: cfg.glow ? `0 0 6px ${cfg.color}55` : undefined }}
              >
                {e.flag}
              </span>
              <span className="text-farm-sub shrink-0">
                {e.team_id ? `team:${e.team_id}` : ''}
              </span>
            </div>
          )
        })
      )}
    </div>
  )
}
