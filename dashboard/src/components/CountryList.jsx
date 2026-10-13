import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { loadIndex } from '../lib/data'
import { originColor, originName, pct, tiv, TIV_HELP } from '../lib/format'

// Below this, a single delivery swings every share, so rankings are noise.
const SMALL_ARSENAL = 100

const COLUMNS = [
  { key: 'name', label: 'Country', sort: r => r.name, asc: true },
  { key: 'top', label: 'Main design origin', sort: r => r.topShare ?? -1 },
  { key: 'russia', label: 'Russia / USSR share', sort: r => r.russiaShare ?? -1, className: 'hidden sm:table-cell' },
  { key: 'backlog', label: 'On order', sort: r => r.backlog ?? 0, className: 'hidden md:table-cell text-right', help: TIV_HELP },
  { key: 'inService', label: 'Imported, in service', sort: r => r.inService ?? 0, className: 'text-right', help: TIV_HELP },
]

function ShareBar({ share, color }) {
  return (
    <div className="h-1.5 w-24 rounded-full bg-stone-200 dark:bg-stone-800 overflow-hidden">
      <div className="h-full rounded-full" style={{ width: `${Math.round((share || 0) * 100)}%`, backgroundColor: color }} />
    </div>
  )
}

export default function CountryList() {
  const [index, setIndex] = useState(null)
  const [error, setError] = useState(null)
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState({ key: 'inService', asc: false })
  const [hideSmall, setHideSmall] = useState(true)
  const navigate = useNavigate()

  useEffect(() => { loadIndex().then(setIndex).catch(e => setError(e.message)) }, [])

  const rows = useMemo(() => {
    if (!index) return []
    const q = query.trim().toLowerCase()
    const col = COLUMNS.find(c => c.key === sort.key)
    return index.countries
      .filter(r => !hideSmall || q || (r.inService ?? 0) >= SMALL_ARSENAL)
      .filter(r => !q || r.name.toLowerCase().includes(q) || r.iso3.toLowerCase() === q)
      .sort((a, b) => {
        const va = col.sort(a), vb = col.sort(b)
        const cmp = typeof va === 'string' ? va.localeCompare(vb) : va - vb
        return sort.asc ? cmp : -cmp
      })
  }, [index, query, sort, hideSmall])

  if (error) return <p className="text-red-600">{error}</p>
  if (!index) return <p className="text-stone-500">Loading…</p>

  const toggleSort = key => {
    const col = COLUMNS.find(c => c.key === key)
    setSort(s => s.key === key ? { key, asc: !s.asc } : { key, asc: !!col.asc })
  }

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">Who does each military depend on?</h1>
      <p className="mt-3 max-w-2xl text-stone-600 dark:text-stone-400">
        For every country that imports major weapons, an estimate of which countries designed the equipment it still
        operates — and therefore who it relies on for spare parts, upgrades and ammunition. Based on {index.countries.length} countries
        and SIPRI deliveries up to {index.dataYear}.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-3">
        <input
          type="search"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Search countries"
          aria-label="Search countries"
          className="w-full sm:w-72 rounded-md border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-stone-400"
        />
        <label className="flex items-center gap-2 text-sm text-stone-600 dark:text-stone-400">
          <input type="checkbox" checked={hideSmall} onChange={e => setHideSmall(e.target.checked)} />
          Hide small arsenals (under {SMALL_ARSENAL} TIV)
        </label>
      </div>

      <div className="mt-4 border-t border-stone-200 dark:border-stone-800">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-stone-500">
              {COLUMNS.map(c => (
                <th key={c.key} className={`py-2 pr-3 font-medium ${c.className || ''}`} title={c.help}>
                  <button onClick={() => toggleSort(c.key)} className="hover:text-stone-900 dark:hover:text-stone-100">
                    {c.label}{sort.key === c.key ? (sort.asc ? ' ↑' : ' ↓') : ''}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr
                key={r.iso3}
                onClick={() => navigate(`/country/${r.iso3}`)}
                className="border-t border-stone-100 dark:border-stone-900 cursor-pointer hover:bg-stone-100 dark:hover:bg-stone-900"
              >
                <td className="py-2.5 pr-3 font-medium">
                  <Link to={`/country/${r.iso3}`} onClick={e => e.stopPropagation()}>{r.name}</Link>
                </td>
                <td className="py-2.5 pr-3">
                  {r.topOrigin ? (
                    <div className="flex items-center gap-2">
                      <ShareBar share={r.topShare} color={originColor(r.topOrigin)} />
                      <span className="tabular w-9 text-right">{pct(r.topShare)}</span>
                      <span className="text-stone-600 dark:text-stone-400 truncate">{originName(index.origins, r.topOrigin)}</span>
                    </div>
                  ) : <span className="text-stone-400">—</span>}
                </td>
                <td className="py-2.5 pr-3 hidden sm:table-cell tabular text-stone-600 dark:text-stone-400">
                  {r.russiaShare == null || (r.russiaShare < 0.005 && (r.russiaShareThen ?? 0) < 0.005) ? '—' : (
                    <span>
                      {r.russiaShareThen != null && <span className="text-stone-400">{pct(r.russiaShareThen)} → </span>}
                      <span className="text-stone-900 dark:text-stone-100">{pct(r.russiaShare)}</span>
                    </span>
                  )}
                </td>
                <td className="py-2.5 pr-3 hidden md:table-cell text-right tabular">{r.backlog ? tiv(r.backlog) : '—'}</td>
                <td className="py-2.5 text-right tabular">{tiv(r.inService)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="py-6 text-sm text-stone-500">No countries match “{query}”.</p>}
      </div>
      <p className="mt-3 text-xs text-stone-500">
        Russia / USSR share: {index.compareYear} → {index.dataYear}. Values are SIPRI trend-indicator values (TIV), a measure of
        military capability rather than money.
      </p>
    </div>
  )
}
