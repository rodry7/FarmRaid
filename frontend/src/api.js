import axios from 'axios'
import useAuthStore from './store/authStore'

const BASE = import.meta.env.VITE_API_URL || ''

const api = axios.create({ baseURL: BASE })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('auth')
  if (token) {
    try {
      const parsed = JSON.parse(token)
      const t = parsed?.state?.token
      if (t) cfg.headers.Authorization = `Bearer ${t}`
    } catch {}
  }
  return cfg
})

api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(err)
  }
)

export function openFeed(token) {
  const host = BASE ? new URL(BASE).host : window.location.host
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return new WebSocket(`${proto}://${host}/ws/feed?token=${token}`)
}

export default api
