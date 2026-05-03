import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import useAuthStore from './store/authStore'
import api from './api'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Exploits from './pages/Exploits'
import Teams from './pages/Teams'
import Flags from './pages/Flags'
import Settings from './pages/Settings'

function ProtectedRoute({ children }) {
  const { token } = useAuthStore()
  const [checking, setChecking] = useState(!!token)

  useEffect(() => {
    if (!token) { setChecking(false); return }
    api.get('/api/auth/verify')
      .then(() => setChecking(false))
      .catch(() => setChecking(false)) // 401 interceptor already called logout()
  }, [])

  if (!token) return <Navigate to="/login" replace />
  if (checking) return null
  return children
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="exploits" element={<Exploits />} />
          <Route path="teams" element={<Teams />} />
          <Route path="flags" element={<Flags />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
