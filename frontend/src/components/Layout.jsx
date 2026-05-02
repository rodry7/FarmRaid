import { useEffect } from 'react'
import { Outlet, Link } from 'react-router-dom'
import Navbar from './Navbar'
import useConfigStore from '../store/configStore'

export default function Layout() {
  const { config, fetchConfig } = useConfigStore()

  useEffect(() => { fetchConfig() }, [])

  const setupComplete = config?.server?.setup_complete !== false

  return (
    <div className="min-h-screen bg-farm-bg text-farm-text flex flex-col">
      <Navbar />
      {!setupComplete && (
        <div className="bg-farm-amber/10 border-b border-farm-amber/30 px-6 py-2 text-xs text-farm-amber tracking-wide">
          Setup not complete.{' '}
          <Link to="/settings" className="underline font-semibold">
            Configure your competition settings
          </Link>{' '}
          to get started.
        </div>
      )}
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  )
}
