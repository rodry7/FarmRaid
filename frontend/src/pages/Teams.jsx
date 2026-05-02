import { useCallback, useEffect, useState } from 'react'
import api from '../api'
import TeamTable from '../components/TeamTable'

const inputCls = 'bg-farm-bg rounded px-3 py-2 text-farm-text border border-farm-border focus:outline-none focus:border-farm-green placeholder:text-farm-sub text-sm'

export default function Teams() {
  const [teams, setTeams] = useState([])
  const [form, setForm] = useState({ name: '', ip: '' })
  const [bulk, setBulk] = useState('')
  const [bulkMode, setBulkMode] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    const res = await api.get('/api/teams')
    setTeams(res.data)
  }, [])

  useEffect(() => { load() }, [load])

  const add = async e => {
    e.preventDefault()
    setError('')
    try {
      await api.post('/api/teams', form)
      setForm({ name: '', ip: '' })
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add team')
    }
  }

  const bulkImport = async e => {
    e.preventDefault()
    setError('')
    const lines = bulk.split('\n').map(l => l.trim()).filter(Boolean)
    const teamsData = lines.map((l, i) => {
      const parts = l.split(',')
      const ip = parts[0].trim()
      const name = parts[1]?.trim() || `Team ${i + 1}`
      return { name, ip }
    })
    try {
      await api.post('/api/teams/bulk', { teams: teamsData })
      setBulk('')
      setBulkMode(false)
      load()
    } catch (err) {
      setError(err.response?.data?.detail || 'Bulk import failed')
    }
  }

  return (
    <div className="space-y-5">
      <h1 className="text-[10px] font-bold tracking-[0.15em] uppercase text-farm-sub">Teams</h1>

      <div className="bg-farm-card border border-farm-border rounded-lg p-4 space-y-4">
        <div className="flex gap-2 border-b border-farm-border pb-3">
          <button
            onClick={() => { setBulkMode(false); setError('') }}
            className={`text-[10px] font-bold tracking-[0.1em] uppercase px-3 py-1.5 rounded transition-colors ${
              !bulkMode
                ? 'bg-farm-green/15 text-farm-green border border-farm-green/30'
                : 'text-farm-sub hover:text-farm-text border border-transparent'
            }`}
          >
            Add Single
          </button>
          <button
            onClick={() => { setBulkMode(true); setError('') }}
            className={`text-[10px] font-bold tracking-[0.1em] uppercase px-3 py-1.5 rounded transition-colors ${
              bulkMode
                ? 'bg-farm-green/15 text-farm-green border border-farm-green/30'
                : 'text-farm-sub hover:text-farm-text border border-transparent'
            }`}
          >
            Bulk Import
          </button>
        </div>

        {error && <p className="text-farm-red text-xs">{error}</p>}

        {!bulkMode ? (
          <form onSubmit={add} className="flex gap-3">
            <input
              placeholder="Team name"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className={`flex-1 ${inputCls}`}
              required
            />
            <input
              placeholder="IP address (e.g. 10.60.1.2)"
              value={form.ip}
              onChange={e => setForm(f => ({ ...f, ip: e.target.value }))}
              className={`flex-1 font-mono ${inputCls}`}
              required
            />
            <button
              type="submit"
              className="bg-farm-green text-black font-bold px-4 py-2 rounded text-xs uppercase tracking-wide hover:brightness-110 transition-all"
            >
              Add
            </button>
          </form>
        ) : (
          <form onSubmit={bulkImport} className="space-y-2">
            <p className="text-[10px] text-farm-sub">
              One per line:{' '}
              <code className="text-farm-green font-mono">10.60.1.2</code> or{' '}
              <code className="text-farm-green font-mono">10.60.1.2, TeamName</code>
            </p>
            <textarea
              value={bulk}
              onChange={e => setBulk(e.target.value)}
              rows={6}
              className={`w-full font-mono resize-none ${inputCls}`}
              placeholder={"10.60.1.2, TeamA\n10.60.1.3, TeamB\n10.60.1.4"}
            />
            <button
              type="submit"
              disabled={!bulk.trim()}
              className="bg-farm-green text-black font-bold px-4 py-2 rounded text-xs uppercase tracking-wide disabled:opacity-50 hover:brightness-110 transition-all"
            >
              Import
            </button>
          </form>
        )}
      </div>

      <div className="bg-farm-card border border-farm-border rounded-lg overflow-hidden">
        <TeamTable teams={teams} onRefresh={load} />
      </div>
    </div>
  )
}
