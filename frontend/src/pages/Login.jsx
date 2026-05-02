import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import useAuthStore from '../store/authStore'

export default function Login() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { setToken } = useAuthStore()
  const navigate = useNavigate()

  const submit = async e => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/api/auth/login', { password })
      setToken(res.data.token)
      navigate('/')
    } catch {
      setError('Invalid password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-farm-bg flex items-center justify-center">
      <form onSubmit={submit} className="bg-farm-card border border-farm-border rounded-xl p-8 w-80 flex flex-col gap-5 shadow-2xl">
        <div className="text-center">
          <h1 className="font-mono font-bold text-2xl tracking-tight">
            <span className="text-farm-green">FARM</span>
            <span className="text-farm-text">RAID</span>
          </h1>
          <p className="text-farm-sub text-xs mt-1 tracking-widest uppercase">CTF Exploit Farm</p>
        </div>

        {error && (
          <div className="text-farm-red text-xs text-center bg-farm-red/10 border border-farm-red/20 rounded px-3 py-2">
            {error}
          </div>
        )}

        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          className="bg-farm-bg rounded px-4 py-2.5 text-farm-text border border-farm-border focus:outline-none focus:border-farm-green placeholder:text-farm-sub text-sm"
          autoFocus
        />

        <button
          type="submit"
          disabled={loading}
          className="bg-farm-green text-black font-bold py-2.5 rounded text-sm tracking-wide uppercase disabled:opacity-50 hover:brightness-110 transition-all"
        >
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>
    </div>
  )
}
