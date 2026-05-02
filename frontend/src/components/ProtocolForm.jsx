const inputCls = 'w-full bg-farm-bg rounded px-3 py-2 text-sm text-farm-text border border-farm-border focus:outline-none focus:border-farm-green placeholder:text-farm-sub'
const selectCls = 'w-full bg-farm-bg rounded px-3 py-2 text-sm text-farm-text border border-farm-border focus:outline-none focus:border-farm-green cursor-pointer'

export default function ProtocolForm({ schema, values, onChange }) {
  if (!schema) return null

  return (
    <div className="space-y-3">
      {Object.entries(schema).map(([key, def]) => {
        // Derive widget type from schema fields, in priority order:
        //  1. options array → <select>
        //  2. type === 'textarea' → <textarea>  (explicit in schema)
        //  3. type === 'integer'  → <input type="number">
        //  4. everything else     → <input type="text">
        const isSelect   = Array.isArray(def.options) && def.options.length > 0
        const isTextarea = !isSelect && def.type === 'textarea'
        const inputType  = def.type === 'integer' ? 'number' : 'text'
        const placeholder = def.placeholder !== undefined
          ? String(def.placeholder)
          : def.default !== undefined ? String(def.default) : ''
        const currentValue = values[key] !== undefined ? values[key] : (def.default ?? '')

        return (
          <div key={key}>
            <label className="block text-[9px] font-semibold tracking-[0.1em] uppercase text-farm-sub mb-1">
              {def.label || key}
              {def.required === false && (
                <span className="ml-1 normal-case font-normal text-farm-sub opacity-60">(optional)</span>
              )}
            </label>

            {isSelect ? (
              <select
                className={selectCls}
                value={currentValue}
                onChange={e => onChange({ ...values, [key]: e.target.value })}
              >
                {def.options.map(opt => (
                  <option key={opt} value={opt}>{opt}</option>
                ))}
              </select>
            ) : isTextarea ? (
              <textarea
                className={`${inputCls} font-mono h-24 resize-none`}
                placeholder={placeholder}
                value={values[key] || ''}
                onChange={e => onChange({ ...values, [key]: e.target.value })}
              />
            ) : (
              <input
                type={inputType}
                className={inputCls}
                placeholder={placeholder}
                value={currentValue}
                onChange={e => onChange({
                  ...values,
                  [key]: inputType === 'number' ? Number(e.target.value) : e.target.value,
                })}
              />
            )}

            {def.description && (
              <p className="text-[10px] text-farm-sub mt-1 leading-relaxed">{def.description}</p>
            )}
          </div>
        )
      })}
    </div>
  )
}
