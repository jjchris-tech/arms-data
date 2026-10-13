import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { loadIndex, loadSuppliers } from '../lib/data'
import { originColor, tiv, TIV_HELP } from '../lib/format'

export default function SupplierList() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    Promise.all([loadSuppliers(), loadIndex()]).then(([s, index]) => setData({ s, index })).catch(e => setError(e.message))
  }, [])
  if (error) return <p className="text-red-600">{error}</p>
  if (!data) return <p className="text-stone-500">Loading…</p>

  const { s, index } = data
  const names = Object.fromEntries(index.countries.map(c => [c.iso3, c.name]))

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight">Who depends on each supplier?</h1>
      <p className="mt-3 max-w-2xl text-stone-600 dark:text-stone-400">
        The same estimates turned around: for each country that designs weapons, which militaries still run on its
        equipment — and so would be hurt if it stopped supplying parts, upgrades and munitions. Domestic production is not
        included, so a supplier’s own forces are never counted.
      </p>

      <div className="mt-6 overflow-x-auto border-t border-stone-200 dark:border-stone-800">
        <table className="w-full text-sm min-w-[36rem]">
          <thead>
            <tr className="text-left text-xs text-stone-500">
              <th className="py-2 pr-3 font-medium">Supplier (design origin)</th>
              <th className="py-2 pr-3 font-medium text-right" title={TIV_HELP}>In service abroad</th>
              <th className="py-2 pr-3 font-medium text-right" title="Countries where this origin is at least half of the estimated arsenal">Majority of arsenal</th>
              <th className="py-2 pr-3 font-medium text-right" title="Countries where this origin is at least a quarter of the estimated arsenal">A quarter or more</th>
              <th className="py-2 font-medium hidden md:table-cell">Most dependent</th>
            </tr>
          </thead>
          <tbody>
            {s.suppliers.map(r => (
              <tr key={r.iso3} onClick={() => navigate(`/supplier/${r.iso3}`)}
                className="border-t border-stone-100 dark:border-stone-900 cursor-pointer hover:bg-stone-100 dark:hover:bg-stone-900">
                <td className="py-2.5 pr-3 font-medium">
                  <span className="inline-flex items-center gap-2">
                    <span className="inline-block size-2.5 rounded-sm" style={{ backgroundColor: originColor(r.iso3) }} />
                    <Link to={`/supplier/${r.iso3}`} onClick={e => e.stopPropagation()}>{r.name}</Link>
                  </span>
                </td>
                <td className="py-2.5 pr-3 text-right tabular">
                  {tiv(r.abroadTiv)}
                  {r.abroadTivThen > 0 && (
                    <div className="text-xs text-stone-500">
                      {r.abroadTiv >= r.abroadTivThen ? '+' : '−'}{Math.abs(Math.round((r.abroadTiv / r.abroadTivThen - 1) * 100))}% since {s.compareYear}
                    </div>
                  )}
                </td>
                <td className="py-2.5 pr-3 text-right tabular">{r.nMajority || '—'}</td>
                <td className="py-2.5 pr-3 text-right tabular">{r.nQuarter || '—'}</td>
                <td className="py-2.5 hidden md:table-cell text-stone-600 dark:text-stone-400 truncate max-w-[18rem]">
                  {r.topDependents.slice(0, 3).map(i => names[i] || i).join(', ')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-xs text-stone-500">
        Counts exclude arsenals under 100 TIV, where one delivery swings the shares. Estimates for {s.dataYear}, including
        equipment inherited at independence and net of re-exports.
      </p>
    </div>
  )
}
