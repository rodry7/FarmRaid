import { useEffect, useState } from 'react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import api, { openFeed } from '../api'
import useAuthStore from '../store/authStore'
import StatCard from '../components/StatCard'
import FlagFeed from '../components/FlagFeed'

const thCls = 'text-left text-[9px] font-bold tracking-[0.1em] uppercase text-farm-muted py-[7px] px-3 border-b border-farm-border'

const SUBMIT_COLOR = {
  accepted:  'text-farm-green',
  rejected:  'text-farm-red',
  duplicate: 'text-farm-amber',
  expired:   'text-farm-sub',
  error:     'text-farm-red',
}

export default function Dashboard() {
  const token = useAuthStore(s => s.token)
  const [stats, setStats] = useState({})
  const [flagEvents, setFlagEvents] = useState([])
  const [timeline, setTimeline] = useState([])
  const [byExploit, setByExploit] = useState([])
  const [byTeam, setByTeam] = useState([])

  const [manualOpen, setManualOpen] = useState(false)
  const [manualText, setManualText] = useState('')
  const [manualLoading, setManualLoading] = useState(false)
  const [manualResults, setManualResults] = useState([])

  const handleManualSubmit = async () => {
    const flags = manualText.split('\n').map(f => f.trim()).filter(Boolean)
    if (!flags.length) return
    setManualLoading(true)
    setManualResults([])
    try {
      const res = await api.post('/api/flags/submit', { flags })
      setManualResults(res.data)
      setManualText('')
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || 'request failed'
      setManualResults(flags.map(f => ({ flag: f, status: 'error', response: msg })))
    } finally {
      setManualLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const [overview, tl, exp, team] = await Promise.all([
        api.get('/api/stats/overview'),
        api.get('/api/stats/timeline'),
        api.get('/api/stats/by_exploit'),
        api.get('/api/stats/by_team'),
      ])
      setStats(overview.data)
      setTimeline(
        tl.data.map(p => ({
          time: new Date(p.minute).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          count: p.count,
        }))
      )
      setByExploit(exp.data)
      setByTeam(team.data)
    } catch {}
  }

  useEffect(() => {
    loadStats()
    const ws = openFeed(token)
    ws.onmessage = e => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === 'stats') setStats(s => ({ ...s, ...msg.data }))
        else if (msg.type === 'flag') setFlagEvents(prev => [msg.data, ...prev].slice(0, 200))
      } catch {}
    }
    return () => ws.close()
  }, [token])

  return (
    <div className="space-y-5">
      <h1 className="text-[10px] font-bold tracking-[0.15em] uppercase text-farm-sub">Dashboard</h1>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Total Flags"    value={stats.total_flags}     />
        <StatCard label="Accepted"       value={stats.accepted}        color="text-farm-green"  />
        <StatCard label="Rejected"       value={stats.rejected}        color="text-farm-red"    />
        <StatCard label="Pending"        value={stats.pending}         color="text-farm-amber"  />
        <StatCard label="Active Exploits" value={stats.exploits_active} color="text-farm-blue"   />
        <StatCard label="Active Teams"   value={stats.teams_active}    color="text-farm-purple" />
      </div>

      <div className="bg-farm-card border border-farm-border rounded-lg overflow-hidden">
        <button
          className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-farm-card2 transition-colors"
          onClick={() => setManualOpen(o => !o)}
        >
          <span className="text-[10px] font-bold tracking-[0.1em] uppercase text-farm-sub">Manual Flag Submit</span>
          <span className="text-farm-muted text-[10px]">{manualOpen ? '▲' : '▼'}</span>
        </button>

        {manualOpen && (
          <div className="px-4 pb-4 pt-2 border-t border-farm-border space-y-3">
            <textarea
              className="w-full bg-farm-bg border border-farm-border rounded px-3 py-2 text-sm font-mono text-farm-text placeholder:text-farm-sub focus:outline-none focus:border-farm-green resize-none h-24"
              placeholder="Paste flags here, one per line…"
              value={manualText}
              onChange={e => setManualText(e.target.value)}
            />
            <div className="flex items-center gap-3">
              <button
                className="px-4 py-1.5 bg-farm-green text-black text-[11px] font-bold rounded hover:opacity-90 transition-opacity disabled:opacity-40"
                disabled={manualLoading || !manualText.trim()}
                onClick={handleManualSubmit}
              >
                {manualLoading ? 'Submitting…' : 'Submit Flags'}
              </button>
              {manualResults.length > 0 && (
                <button
                  className="text-[10px] text-farm-sub hover:text-farm-text transition-colors"
                  onClick={() => setManualResults([])}
                >
                  Clear
                </button>
              )}
            </div>

            {manualResults.length > 0 && (
              <div className="space-y-0.5 max-h-48 overflow-y-auto pr-1">
                {manualResults.map((r, i) => (
                  <div key={i} className="flex items-center gap-3 text-xs font-mono py-0.5">
                    <span className={`text-[9px] font-bold tracking-[0.1em] uppercase w-16 shrink-0 ${SUBMIT_COLOR[r.status] ?? 'text-farm-sub'}`}>
                      {r.status}
                    </span>
                    <span className="text-farm-sub truncate flex-1">{r.flag}</span>
                    <span className="text-farm-sub text-[10px] shrink-0 max-w-[180px] truncate">{r.response}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-farm-card border border-farm-border rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-farm-border">
            <span className="text-[10px] font-bold tracking-[0.1em] uppercase text-farm-sub">Live Flag Feed</span>
          </div>
          <div className="p-3">
            <FlagFeed events={flagEvents} />
          </div>
        </div>

        <div className="bg-farm-card border border-farm-border rounded-lg overflow-hidden">
          <div className="flex items-center gap-2 px-4 py-2.5 border-b border-farm-border">
            <span className="text-[10px] font-bold tracking-[0.1em] uppercase text-farm-sub">Flags / Minute</span>
          </div>
          <div className="p-4">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={timeline}>
                <XAxis dataKey="time" tick={{ fill: '#444', fontSize: 9, fontFamily: 'IBM Plex Sans' }} axisLine={{ stroke: '#1e1e1e' }} tickLine={false} />
                <YAxis tick={{ fill: '#444', fontSize: 9, fontFamily: 'IBM Plex Sans' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: '#111111', border: '1px solid #1e1e1e', color: '#e8e8e8', fontSize: 11, fontFamily: 'IBM Plex Sans' }}
                  labelStyle={{ color: '#666' }}
                  cursor={{ stroke: '#1e1e1e' }}
                />
                <Line
                  type="monotone"
                  dataKey="count"
                  stroke="#00ff41"
                  dot={false}
                  strokeWidth={1.5}
                  name="Flags"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="bg-farm-card border border-farm-border rounded-lg overflow-hidden">
          <div className="px-4 py-2.5 border-b border-farm-border">
            <span className="text-[10px] font-bold tracking-[0.1em] uppercase text-farm-sub">Top Exploits</span>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className={thCls}>Name</th>
                <th className={`${thCls} text-right`}>Accepted</th>
                <th className={`${thCls} text-right`}>Total</th>
              </tr>
            </thead>
            <tbody>
              {byExploit.map(e => (
                <tr key={e.exploit_id} className="border-b border-farm-border hover:bg-farm-card2 transition-colors">
                  <td className="py-2 px-3 text-farm-text font-mono">{e.exploit_name}</td>
                  <td className="py-2 px-3 text-right text-farm-green font-mono">{e.flags_accepted}</td>
                  <td className="py-2 px-3 text-right text-farm-sub font-mono">{e.flags_total}</td>
                </tr>
              ))}
              {byExploit.length === 0 && (
                <tr><td colSpan={3} className="text-center text-farm-sub py-6">No data yet</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="bg-farm-card border border-farm-border rounded-lg overflow-hidden">
          <div className="px-4 py-2.5 border-b border-farm-border">
            <span className="text-[10px] font-bold tracking-[0.1em] uppercase text-farm-sub">Top Teams Attacked</span>
          </div>
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className={thCls}>Team</th>
                <th className={thCls}>IP</th>
                <th className={`${thCls} text-right`}>Flags</th>
              </tr>
            </thead>
            <tbody>
              {byTeam.map(t => (
                <tr key={t.team_id} className="border-b border-farm-border hover:bg-farm-card2 transition-colors">
                  <td className="py-2 px-3 text-farm-text">{t.team_name}</td>
                  <td className="py-2 px-3 font-mono text-farm-green">{t.team_ip}</td>
                  <td className="py-2 px-3 text-right font-mono text-farm-text">{t.flags_accepted}</td>
                </tr>
              ))}
              {byTeam.length === 0 && (
                <tr><td colSpan={3} className="text-center text-farm-sub py-6">No data yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
