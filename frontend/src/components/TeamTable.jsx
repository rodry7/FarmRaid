import api from '../api'

export default function TeamTable({ teams, onRefresh }) {
  const toggle = async (team) => {
    await api.put(`/api/teams/${team.id}`, { active: !team.active })
    onRefresh()
  }

  const del = async (id) => {
    if (!confirm('Delete this team?')) return
    await api.delete(`/api/teams/${id}`)
    onRefresh()
  }

  const thCls = 'text-left text-[9px] font-bold tracking-[0.1em] uppercase text-farm-muted py-[7px] px-3 border-b border-farm-border'

  return (
    <table className="w-full text-sm">
      <thead>
        <tr>
          <th className={thCls}>Name</th>
          <th className={thCls}>IP</th>
          <th className={thCls}>Status</th>
          <th className={thCls}>Actions</th>
        </tr>
      </thead>
      <tbody>
        {teams.map(t => (
          <tr key={t.id} className="border-b border-farm-border hover:bg-farm-card2 transition-colors">
            <td className="py-2 px-3 text-farm-text">{t.name}</td>
            <td className="py-2 px-3 font-mono text-farm-green text-xs">{t.ip}</td>
            <td className="py-2 px-3">
              <span className={`text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded ${
                t.active
                  ? 'bg-farm-green/15 text-farm-green'
                  : 'bg-farm-dim text-farm-sub'
              }`}>
                {t.active ? 'active' : 'inactive'}
              </span>
            </td>
            <td className="py-2 px-3">
              <div className="flex gap-3">
                <button onClick={() => toggle(t)} className="text-[11px] text-farm-blue hover:text-farm-text transition-colors">
                  {t.active ? 'Disable' : 'Enable'}
                </button>
                <button onClick={() => del(t.id)} className="text-[11px] text-farm-red hover:text-farm-text transition-colors">
                  Delete
                </button>
              </div>
            </td>
          </tr>
        ))}
        {teams.length === 0 && (
          <tr>
            <td colSpan={4} className="text-center text-farm-sub py-8 text-sm">No teams yet.</td>
          </tr>
        )}
      </tbody>
    </table>
  )
}
