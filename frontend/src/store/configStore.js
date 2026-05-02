import { create } from 'zustand'
import api from '../api'

const useConfigStore = create((set) => ({
  config: {},
  protocols: [],
  loading: false,

  fetchConfig: async () => {
    set({ loading: true })
    try {
      const [cfg, protos] = await Promise.all([
        api.get('/api/config'),
        api.get('/api/config/protocols'),
      ])
      set({ config: cfg.data, protocols: protos.data })
    } catch {} finally {
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
