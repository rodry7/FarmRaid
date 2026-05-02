import { Link, useLocation } from 'react-router-dom'
import useAuthStore from '../store/authStore'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/exploits', label: 'Exploits' },
  { to: '/teams', label: 'Teams' },
  { to: '/flags', label: 'Flags' },
  { to: '/settings', label: 'Settings' },
]

export default function Navbar() {
  const { logout } = useAuthStore()
  const { pathname } = useLocation()

  return (
    <nav className="bg-farm-card border-b border-farm-border px-6 py-3 flex items-center gap-6">
      <span className="font-mono font-bold text-lg tracking-tight mr-4 select-none">
        <span className="text-farm-green">FARM</span>
        <span className="text-farm-text">RAID</span>
      </span>
      {links.map(l => (
        <Link
          key={l.to}
          to={l.to}
          className={`text-xs font-semibold tracking-wide uppercase transition-colors ${
            pathname === l.to
              ? 'text-farm-text'
              : 'text-farm-sub hover:text-farm-text'
          }`}
        >
          {l.label}
        </Link>
      ))}
      <button
        onClick={logout}
        className="ml-auto text-xs font-semibold tracking-wide uppercase text-farm-sub hover:text-farm-red transition-colors"
      >
        Logout
      </button>
    </nav>
  )
}
