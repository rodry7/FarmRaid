import { useCallback, useEffect, useState } from 'react'
import api from '../api'

const STATUS_CFG = {
  accepted:  { bg: 'bg-farm-green/15',  text: 'text-farm-green'  },
  rejected:  { bg: 'bg-farm-red/15',    text: 'text-farm-red'    },
  pending:   { bg: 'bg-farm-amber/15',  text: 'text-farm-amber'  },
  queued:    { bg: 'bg-farm-amber/15',  text: 'text-farm-amber'  },
  duplicate: { bg: 'bg-farm-dim',       text: 'text-farm-sub'    },
  expired:   { bg: 'bg-farm-dim',       text: 'text-farm-muted'  },
  error:     { bg: 'bg-farm-red/10',    text: 'text-farm-red'    },
}

const STATUSES = ['accepted', 'rejected', 'pending', 'queued', 'duplicate', 'expired', 'error']

const selectCls = 'bg-farm-bg rounded px-3 py-1.5 text-xs text-farm-text border border-farm-border focus:outline-none focus:border-farm-green'
const thCls = 'text-left text-[9px] font-bold tracking-[0.1em] uppercase text-farm-muted py-[7px] px-3 border-b border-farm-border'

function ResponseModal({ text, onClose }) {
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

export default function Flags() {
  const [flags, setFlags] = useState([])
  const [total, setTotal] = useState(0)
  const [exploits, setExploits] = useState([])
  const [teams, setTeams] = useState([])
  const [filter, setFilter] = useState({ status: '', exploit_id: '', team_id: '', limit: 50, offset: 0 })
  const [modalText, setModalText] = useState(null)

  const load = useCallback(async () => {
    const params = Object.fromEntries(Object.entries(filter).filter(([, v]) => v !== ''))
    try {
      const res = await api.get('/api/flags', { params })
      setFlags(res.data.items)
      setTotal(res.data.total)
    } catch {}
  }, [filter])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    Promise.all([api.get('/api/exploits'), api.get('/api/teams')]).then(([e, t]) => {
      setExploits(e.data)
      setTeams(t.data)
    }).catch(() => {})
  }, [])

  const setField = k => e => setFilter(f => ({ ...f, [k]: e.target.value, offset: 0 }))

  const exportCsv = () => {
    const header = 'Flag,Status,Exploit,Team,Captured,Response'
    const rows = flags.map(f =>
      [f.flag, f.status, f.exploit_name || '', f.team_ip || '', f.captured_at, (f.response || '').replace(/,/g, ';')].join(',')
    )
    const blob = new Blob([[header, ...rows].join('\n')], { type: 'text/csv' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'flags.csv'
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const totalPages = Math.ceil(total / filter.limit)

  return (
    <div className="space-y-4">
      {modalText !== null && <ResponseModal text={modalText} onClose={() => setModalText(null)} />}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-[10px] font-bold tracking-[0.15em] uppercase text-farm-sub">
            Flags{' '}
            <span className="text-farm-muted font-mono normal-case tracking-normal">{total}</span>
          </h1>
        </div>
        <button onClick={exportCsv} className="text-[11px] font-semibold tracking-wide uppercase text-farm-blue hover:text-farm-text transition-colors">
          Export CSV
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <select onChange={setField('status')} value={filter.status} className={selectCls}>
          <option value="">All statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select onChange={setField('exploit_id')} value={filter.exploit_id} className={selectCls}>
          <option value="">All exploits</option>
          {exploits.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
        </select>
        <select onChange={setField('team_id')} value={filter.team_id} className={selectCls}>
          <option value="">All teams</option>
          {teams.map(t => <option key={t.id} value={t.id}>{t.name} ({t.ip})</option>)}
        </select>
      </div>

      <div className="bg-farm-card border border-farm-border rounded-lg overflow-x-auto">
        <table className="w-full text-xs min-w-[700px]">
          <thead>
            <tr>
              <th className={thCls}>Flag</th>
              <th className={thCls}>Status</th>
              <th className={thCls}>Exploit</th>
              <th className={thCls}>Team</th>
              <th className={thCls}>Captured</th>
              <th className={thCls}>Response</th>
            </tr>
          </thead>
          <tbody>
            {flags.map(f => {
              const cfg = STATUS_CFG[f.status] || { bg: 'bg-farm-dim', text: 'text-farm-sub' }
              return (
                <tr key={f.id} className="border-b border-farm-border hover:bg-farm-card2 transition-colors">
                  <td className="py-2 px-3 font-mono text-farm-green max-w-[200px] truncate">{f.flag}</td>
                  <td className="py-2 px-3">
                    <span className={`${cfg.bg} ${cfg.text} text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded`}>
                      {f.status}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-farm-text">{f.exploit_name || f.exploit_id || '—'}</td>
                  <td className="py-2 px-3 font-mono text-farm-blue">{f.team_ip || f.team_id || '—'}</td>
                  <td className="py-2 px-3 text-farm-sub whitespace-nowrap font-mono">{new Date(f.captured_at).toLocaleString()}</td>
                  <td
                    className="py-2 px-3 text-farm-sub max-w-[150px] truncate cursor-pointer hover:text-farm-text transition-colors"
                    title="Click to view full response"
                    onClick={() => setModalText(f.response || '')}
                  >{f.response || '—'}</td>
                </tr>
              )
            })}
            {flags.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center text-farm-sub py-8">No flags yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex gap-3 items-center justify-end text-xs">
          <button
            onClick={() => setFilter(f => ({ ...f, offset: Math.max(0, f.offset - f.limit) }))}
            disabled={filter.offset === 0}
            className="text-farm-sub hover:text-farm-text disabled:opacity-30 transition-colors font-mono"
          >
            ← Prev
          </button>
          <span className="text-farm-sub font-mono">
            {filter.offset + 1}–{Math.min(filter.offset + filter.limit, total)} of {total}
          </span>
          <button
            onClick={() => setFilter(f => ({ ...f, offset: f.offset + f.limit }))}
            disabled={filter.offset + filter.limit >= total}
            className="text-farm-sub hover:text-farm-text disabled:opacity-30 transition-colors font-mono"
          >
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
