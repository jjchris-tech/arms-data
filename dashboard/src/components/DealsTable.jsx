import { Fragment, useMemo, useState } from 'react'
import { originColor, originName, tiv, TIV_HELP } from '../lib/format'

const VIEWS = [
  { key: 'inService', label: 'In service', test: d => d.tivInService > 0, value: d => d.tivInService, valueLabel: 'In service' },
  { key: 'open', label: 'On order', test: d => d.state === 'open', value: d => d.tivOutstanding, valueLabel: 'Outstanding' },
  { key: 'all', label: 'All', test: () => true, value: d => d.tiv, valueLabel: 'Delivered' },
]
const PAGE = 40

const ORIGIN_NOTES = {
  family_majority: 'Design origin taken from the country that sells this system new most often.',
  soviet_pattern: 'Design origin inferred from a Soviet/Russian designation pattern.',
  design_bureau: 'Soviet-era design from a bureau based in Ukraine (Antonov / Ivchenko).',
  seller: 'Design origin assumed to be the seller (no better information).',
}

function years(d) {
  if (!d.deliveryYears) return d.plannedDelivery ? `planned ${d.plannedDelivery}` : '—'
  const ys = d.deliveryYears.split(';')
  return ys.length > 1 ? `${ys[0]}–${ys[ys.length - 1]}` : ys[0]
}

function units(d) {
  if (d.ordered == null) return d.delivered ?? '—'
  return d.delivered != null && d.delivered !== d.ordered ? `${d.delivered} / ${d.ordered}` : d.ordered
}

export default function DealsTable({ profile, filter, setFilter }) {
  const [query, setQuery] = useState('')
  const [shown, setShown] = useState(PAGE)
  const [open, setOpen] = useState(null)
  const view = VIEWS.find(v => v.key === filter.view) || VIEWS[0]

  const capabilities = useMemo(() => [...new Set(profile.deals.map(d => d.cap))].sort(), [profile])
  const origins = useMemo(() => {
    const counts = {}
    for (const d of profile.deals) counts[d.origin] = (counts[d.origin] || 0) + 1
    return Object.keys(counts).sort((a, b) => counts[b] - counts[a])
  }, [profile])

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    return profile.deals
      .filter(view.test)
      .filter(d => !filter.origin || d.origin === filter.origin)
      .filter(d => !filter.cap || d.cap === filter.cap)
      .filter(d => !q || `${d.designation} ${d.desc} ${d.seller}`.toLowerCase().includes(q))
      .sort((a, b) => (view.value(b) || 0) - (view.value(a) || 0) || (b.orderYear || 0) - (a.orderYear || 0))
  }, [profile, filter, view, query])

  const total = rows.reduce((s, d) => s + (view.value(d) || 0), 0)
  const update = patch => { setFilter(f => ({ ...f, ...patch })); setShown(PAGE); setOpen(null) }
  const select = 'rounded-md border border-stone-300 dark:border-stone-700 bg-white dark:bg-stone-900 px-2 py-1.5 text-sm'

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex rounded-md border border-stone-300 dark:border-stone-700 overflow-hidden text-sm" role="group" aria-label="Which deals">
          {VIEWS.map(v => (
            <button key={v.key} onClick={() => update({ view: v.key })} aria-pressed={v.key === view.key}
              className={`px-3 py-1.5 ${v.key === view.key ? 'bg-stone-900 text-white dark:bg-stone-100 dark:text-stone-900' : 'hover:bg-stone-100 dark:hover:bg-stone-900'}`}>
              {v.label}
            </button>
          ))}
        </div>
        <select aria-label="Design origin" value={filter.origin || ''} onChange={e => update({ origin: e.target.value || null })} className={select}>
          <option value="">All origins</option>
          {origins.map(o => <option key={o} value={o}>{originName(profile.origins, o)}</option>)}
        </select>
        <select aria-label="Capability" value={filter.cap || ''} onChange={e => update({ cap: e.target.value || null })} className={select}>
          <option value="">All capabilities</option>
          {capabilities.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <input type="search" value={query} onChange={e => { setQuery(e.target.value); setShown(PAGE) }}
          placeholder="Search systems" aria-label="Search systems" className={`${select} w-full sm:w-44`} />
      </div>

      <p className="mt-3 text-xs text-stone-500">
        {rows.length} deal{rows.length === 1 ? '' : 's'} · {tiv(total)} TIV {view.valueLabel.toLowerCase()}
        {(filter.origin || filter.cap) && (
          <button onClick={() => update({ origin: null, cap: null })} className="ml-2 underline">clear filters</button>
        )}
      </p>

      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-sm min-w-[36rem]">
          <thead>
            <tr className="text-left text-xs text-stone-500 border-b border-stone-200 dark:border-stone-800">
              <th className="py-2 pr-3 font-medium">System</th>
              <th className="py-2 pr-3 font-medium">Design origin</th>
              <th className="py-2 pr-3 font-medium">Ordered</th>
              <th className="py-2 pr-3 font-medium">Delivered</th>
              <th className="py-2 pr-3 font-medium text-right">Units</th>
              <th className="py-2 font-medium text-right" title={TIV_HELP}>{view.valueLabel} (TIV)</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, shown).map(d => (
              <Fragment key={d.id}>
                <tr onClick={() => setOpen(open === d.id ? null : d.id)}
                  className="border-b border-stone-100 dark:border-stone-900 cursor-pointer hover:bg-stone-100 dark:hover:bg-stone-900 align-top">
                  <td className="py-2 pr-3">
                    <div className="font-medium">{d.designation}</div>
                    <div className="text-xs text-stone-500">
                      {d.desc}
                      {d.secondHand && <span className="ml-1.5 rounded bg-stone-200 dark:bg-stone-800 px-1">second-hand</span>}
                      {d.licensed && <span className="ml-1.5 rounded bg-stone-200 dark:bg-stone-800 px-1">licensed / local</span>}
                    </div>
                  </td>
                  <td className="py-2 pr-3">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="inline-block size-2 rounded-sm" style={{ backgroundColor: originColor(d.origin) }} />
                      {originName(profile.origins, d.origin)}
                    </span>
                    {d.seller && d.sellerCode !== d.origin && (
                      <div className="text-xs text-stone-500">via {d.seller}</div>
                    )}
                  </td>
                  <td className="py-2 pr-3 tabular">{d.orderYear ?? '—'}{d.uncertain && <span className="text-stone-400" title="SIPRI marks some figures for this deal as uncertain"> ?</span>}</td>
                  <td className="py-2 pr-3 tabular">{years(d)}</td>
                  <td className="py-2 pr-3 tabular text-right">{units(d)}</td>
                  <td className="py-2 tabular text-right">{tiv(view.value(d))}</td>
                </tr>
                {open === d.id && (
                  <tr className="border-b border-stone-100 dark:border-stone-900 bg-stone-100/60 dark:bg-stone-900/60">
                    <td colSpan={6} className="px-3 py-3 text-xs text-stone-600 dark:text-stone-400 space-y-1">
                      {d.comments && <p><span className="font-medium text-stone-800 dark:text-stone-200">SIPRI note:</span> {d.comments}</p>}
                      <p>{ORIGIN_NOTES[d.originMethod]}</p>
                      <p>
                        Capability: {d.cap} · Delivered TIV {tiv(d.tiv)} · Still in service {tiv(d.tivInService)}
                        {d.state === 'open' && <> · Outstanding {tiv(d.tivOutstanding)}</>}
                        {d.uncertain && <> · Some figures marked uncertain by SIPRI</>}
                      </p>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="py-6 text-sm text-stone-500">No deals match these filters.</p>}
      </div>
      {rows.length > shown && (
        <button onClick={() => setShown(s => s + PAGE * 2)} className="mt-3 text-sm underline underline-offset-2">
          Show more ({rows.length - shown} remaining)
        </button>
      )}
    </div>
  )
}
