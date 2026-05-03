import { create } from 'zustand'
import api from '../api'

const useConfigStore = create((set) => ({
  config: {},
  protocols: [],
  loading: false,

  fetchConfig: async () => {
    set({ loading: true })
    try {
      const [cfgRes, protosRes] = await Promise.allSettled([
        api.get('/api/config'),
        api.get('/api/config/protocols'),
      ])
      if (cfgRes.status === 'fulfilled') {
        set({ config: cfgRes.value.data })
      } else {
        console.error('Failed to fetch config:', cfgRes.reason)
      }
      if (protosRes.status === 'fulfilled') {
        set({ protocols: protosRes.value.data })
      } else {
        console.error('Failed to fetch protocols:', protosRes.reason)
      }
    } finally {
      set({ loading: false })
    }
  },

  setConfig: async (key, value) => {
    await api.post('/api/config', { key, value })
    const res = await api.get('/api/config')
    set({ config: res.data })
  },
}))

export default useConfigStore
