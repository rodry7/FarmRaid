import { useEffect, useState } from 'react'
import api from '../api'
import useConfigStore from '../store/configStore'
import ProtocolForm from '../components/ProtocolForm'

const TABS = [
  { id: 'competition', label: 'Competition' },
  { id: 'submission',  label: 'Submission'  },
  { id: 'server',      label: 'Server'       },
]

const inputCls = 'w-full bg-farm-bg rounded px-3 py-2 text-farm-text border border-farm-border focus:outline-none focus:border-farm-green placeholder:text-farm-sub text-sm'
const labelCls = 'block text-[9px] font-semibold tracking-[0.1em] uppercase text-farm-sub mb-1'

export default function Settings() {
  const { config, protocols, fetchConfig, setConfig } = useConfigStore()
  const [tab, setTab] = useState('competition')
  const [competition, setCompetition] = useState({})
  const [submission, setSubmission] = useState({})
  const [selectedProtocol, setSelectedProtocol] = useState('')
  const [protocolParams, setProtocolParams] = useState({})
  const [newPassword, setNewPassword] = useState('')
  const [pwStatus, setPwStatus] = useState('')
  const [flagTest, setFlagTest] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => { fetchConfig() }, [])

  useEffect(() => {
    if (config.competition) setCompetition({ ...config.competition })
    if (config.submission) {
      setSubmission({ ...config.submission })
      setSelectedProtocol(config.submission.protocol || '')
      setProtocolParams(config.submission.params || {})
    }
  }, [config])

  const showSaved = () => { setSaved(true); setTimeout(() => setSaved(false), 2000) }

  const saveCompetition = async () => {
    setSaving(true)
    try {
      await setConfig('competition', competition)
      await setConfig('server', { ...(config.server || {}), setup_complete: true })
      showSaved()
    } finally { setSaving(false) }
  }

  const saveSubmission = async () => {
    setSaving(true)
    try {
      await setConfig('submission', { ...submission, protocol: selectedProtocol, params: protocolParams })
      showSaved()
    } finally { setSaving(false) }
  }

  const changePassword = async () => {
    setPwStatus('')
    if (!newPassword) return
    try {
      await api.post('/api/auth/change_password', { new_password: newPassword })
      setNewPassword('')
      setPwStatus('success')
    } catch (e) {
      setPwStatus(e.response?.data?.detail || 'Failed to change password')
    }
  }

  const proto = protocols.find(p => p.name === selectedProtocol)

  let flagTestMatch = null
  if (flagTest && competition.flag_format) {
    try { flagTestMatch = new RegExp(competition.flag_format).test(flagTest) }
    catch { flagTestMatch = false }
  }

  const saveBtnCls = 'bg-farm-green text-black font-bold px-4 py-2 rounded text-xs uppercase tracking-wide disabled:opacity-50 hover:brightness-110 transition-all'

  return (
    <div className="space-y-5 max-w-2xl">
      <h1 className="text-[10px] font-bold tracking-[0.15em] uppercase text-farm-sub">Settings</h1>

      <div className="flex gap-0 border-b border-farm-border">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2.5 text-[11px] font-bold tracking-[0.1em] uppercase transition-colors ${
              tab === t.id
                ? 'text-farm-text border-b-2 border-farm-green -mb-px'
                : 'text-farm-sub hover:text-farm-text'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'competition' && (
        <div className="space-y-4">
          <div>
            <label className={labelCls}>Competition Name</label>
            <input
              className={inputCls}
              value={competition.name || ''}
              onChange={e => setCompetition(c => ({ ...c, name: e.target.value }))}
              placeholder="My CTF 2024"
            />
          </div>
          <div>
            <label className={labelCls}>Flag Format (regex)</label>
            <input
              className={`${inputCls} font-mono`}
              value={competition.flag_format || ''}
              onChange={e => setCompetition(c => ({ ...c, flag_format: e.target.value }))}
              placeholder="[A-Z0-9]{31}="
            />
          </div>
          <div>
            <label className={labelCls}>Test flag format</label>
            <div className="flex gap-2 items-center">
              <input
                className={`flex-1 font-mono ${inputCls}`}
                value={flagTest}
                onChange={e => setFlagTest(e.target.value)}
                placeholder="Paste a sample flag to test"
              />
              {flagTest && (
                <span className={`text-xs shrink-0 font-mono font-semibold ${flagTestMatch ? 'text-farm-green' : 'text-farm-red'}`}>
                  {flagTestMatch ? '✓ match' : '✗ no match'}
                </span>
              )}
            </div>
          </div>
          <div>
            <label className={labelCls}>Flag Lifetime (seconds)</label>
            <input
              type="number"
              className={inputCls}
              value={competition.flag_lifetime || 300}
              onChange={e => setCompetition(c => ({ ...c, flag_lifetime: Number(e.target.value) }))}
            />
          </div>
          <div className="flex items-center gap-3 pt-1">
            <button onClick={saveCompetition} disabled={saving} className={saveBtnCls}>
              {saving ? 'Saving...' : 'Save Competition Settings'}
            </button>
            {saved && <span className="text-farm-green text-xs font-mono">Saved!</span>}
          </div>
        </div>
      )}

      {tab === 'submission' && (
        <div className="space-y-4">
          <div>
            <label className={labelCls}>Protocol</label>
            <select
              value={selectedProtocol}
              onChange={e => { setSelectedProtocol(e.target.value); setProtocolParams({}) }}
              className={`${inputCls} cursor-pointer`}
            >
              <option value="">Select protocol...</option>
              {protocols.map(p => <option key={p.name} value={p.name}>{p.display_name}</option>)}
            </select>
          </div>

          {proto && (
            <div className="bg-farm-bg border border-farm-border rounded-lg p-4">
              <h3 className="text-[9px] font-bold tracking-[0.1em] uppercase text-farm-sub mb-3">{proto.display_name} Parameters</h3>
              <ProtocolForm schema={proto.params_schema} values={protocolParams} onChange={setProtocolParams} />
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={labelCls}>Submit Period (s)</label>
              <input
                type="number"
                className={inputCls}
                value={submission.submit_period || 10}
                onChange={e => setSubmission(s => ({ ...s, submit_period: Number(e.target.value) }))}
              />
            </div>
            <div>
              <label className={labelCls}>Flags per Batch</label>
              <input
                type="number"
                className={inputCls}
                value={submission.submit_flag_limit || 100}
                onChange={e => setSubmission(s => ({ ...s, submit_flag_limit: Number(e.target.value) }))}
              />
            </div>
          </div>

          <div className="flex items-center gap-3 pt-1">
            <button onClick={saveSubmission} disabled={saving} className={saveBtnCls}>
              {saving ? 'Saving...' : 'Save Submission Settings'}
            </button>
            {saved && <span className="text-farm-green text-xs font-mono">Saved!</span>}
          </div>
        </div>
      )}

      {tab === 'server' && (
        <div className="space-y-5">
          <div>
            <h2 className="text-[9px] font-bold tracking-[0.1em] uppercase text-farm-sub mb-3">Change Password</h2>
            {pwStatus === 'success' && <p className="text-farm-green text-xs mb-2 font-mono">Password changed successfully.</p>}
            {pwStatus && pwStatus !== 'success' && <p className="text-farm-red text-xs mb-2">{pwStatus}</p>}
            <div className="flex gap-3">
              <input
                type="password"
                placeholder="New password"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && changePassword()}
                className={`flex-1 ${inputCls}`}
              />
              <button
                onClick={changePassword}
                disabled={!newPassword}
                className="bg-farm-blue/20 text-farm-blue border border-farm-blue/30 font-bold px-4 py-2 rounded text-xs uppercase tracking-wide disabled:opacity-50 hover:bg-farm-blue/30 transition-all"
              >
                Change
              </button>
            </div>
          </div>

          <div className="border-t border-farm-border pt-4">
            <h2 className="text-[9px] font-bold tracking-[0.1em] uppercase text-farm-sub mb-3">Security Notes</h2>
            <ul className="text-xs text-farm-sub space-y-1.5 list-disc list-inside">
              <li>Exploits run directly in the server container — treat uploaded scripts as trusted code</li>
              <li>Only use in isolated CTF network environments</li>
              <li>No HTTPS by default — add a reverse proxy for remote access</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}
