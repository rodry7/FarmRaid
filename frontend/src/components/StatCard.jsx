export default function StatCard({ label, value, color = 'text-farm-text' }) {
  return (
    <div className="bg-farm-card border border-farm-border rounded-lg px-[15px] py-[13px] flex flex-col gap-0.5 min-w-0">
      <span className="text-[9px] font-semibold tracking-[0.12em] uppercase text-farm-sub">
        {label}
      </span>
      <span className={`text-[26px] font-bold leading-none font-mono ${color}`}>
        {value ?? '—'}
      </span>
    </div>
  )
}
