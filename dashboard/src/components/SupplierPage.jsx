import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Area, AreaChart, CartesianGrid, LabelList, ReferenceLine, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
} from 'recharts'
import { loadSupplier } from '../lib/data'
import { originColor, originInSentence, pct, tiv, TIV_HELP } from '../lib/format'

export const STATUS = {
  staying: { label: 'Staying', color: '#1d4ed8', help: 'Recent orders keep pace with current dependence (at least 80% of it)' },
  diversifying: { label: 'Diversifying', color: '#d97706', help: 'Still ordering, but less than current dependence (40–80% of it)' },
  moving_away: { label: 'Moving away', color: '#0d9488', help: 'Recent orders well below current dependence (under 40% of it)' },
  few_orders: { label: 'Few orders', color: '#a8a29e', help: 'Too few new orders in the period to judge' },
}

function StatusBadge({ status }) {
  const s = STATUS[status]
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap" title={s.help}>
      <span className="inline-block size-2 rounded-full" style={{ backgroundColor: s.color }} />{s.label}
    </span>
  )
}

function Section({ title, subtitle, children }) {
  return (
    <section className="mt-12">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      {subtitle && <p className="mt-1 text-sm text-stone-600 dark:text-stone-400 max-w-3xl">{subtitle}</p>}
      <div className="mt-4">{children}</div>
    </section>
  )
}

function ScatterTip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-md border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 px-3 py-2 text-xs shadow-sm">
      <div className="font-medium">{d.name}</div>
      <div>Arsenal today: {pct(d.share)}</div>
      <div>Orders since {d.recentFrom}: {pct(d.orderShare)}</div>
      <div className="mt-1"><StatusBadge status={d.status} /></div>
    </div>
  )
}

/** Dependence today (x) against share of recent orders (y). Below the diagonal = buying less than they depend. */
function StillBuying({ s }) {
  const navigate = useNavigate()
  const points = s.dependents
    .filter(d => !d.small && d.share >= 0.25 && d.status !== 'few_orders')
    .map(d => ({ ...d, x: d.share, y: d.orderShare, z: d.arsenalTiv, recentFrom: s.recentFrom }))
  // Name the largest arsenals on the chart; the rest are in the tooltip and the table below
  const labelled = new Set([...points].sort((a, b) => b.z - a.z).slice(0, 10).map(p => p.iso3))
  points.forEach(p => { p.label = labelled.has(p.iso3) ? p.name : '' })
  if (!points.length) return <p className="text-sm text-stone-500">No country depends on {s.name} for a quarter or more of a sizeable arsenal.</p>

  return (
    <div>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
            <CartesianGrid strokeOpacity={0.15} />
            <XAxis type="number" dataKey="x" domain={[0.25, 1]} ticks={[0.25, 0.5, 0.75, 1]} tickFormatter={v => pct(v)} tick={{ fontSize: 11 }}
              label={{ value: 'Share of arsenal today', position: 'insideBottom', offset: -12, fontSize: 11 }} />
            <YAxis type="number" dataKey="y" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={v => pct(v)} tick={{ fontSize: 11 }}
              label={{ value: `Share of orders since ${s.recentFrom}`, angle: -90, position: 'insideLeft', offset: 14, fontSize: 11, dy: 70 }} />
            <ZAxis type="number" dataKey="z" range={[40, 400]} />
            <ReferenceLine segment={[{ x: 0.25, y: 0.25 }, { x: 1, y: 1 }]} stroke="#78716c" strokeDasharray="4 4" />
            <Tooltip content={<ScatterTip />} cursor={false} />
            {Object.entries(STATUS).filter(([k]) => k !== 'few_orders').map(([k, v]) => (
              <Scatter key={k} data={points.filter(p => p.status === k)} fill={v.color} fillOpacity={0.75}
                onClick={p => navigate(`/country/${p.iso3}`)} cursor="pointer" isAnimationActive={false}>
                <LabelList dataKey="label" position="right" offset={8} style={{ fontSize: 10, fill: '#78716c' }} />
              </Scatter>
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {Object.entries(STATUS).filter(([k]) => k !== 'few_orders').map(([k]) => <StatusBadge key={k} status={k} />)}
        <span className="text-stone-500">Dot size = size of arsenal. Dashed line = ordering in proportion to current dependence.</span>
      </div>
    </div>
  )
}

const COLUMNS = [
  { key: 'name', label: 'Country', sort: d => d.name, asc: true },
  { key: 'share', label: 'Share of arsenal', sort: d => d.share },
  { key: 'change', label: 'Change', sort: d => (d.shareThen == null ? -9 : d.share - d.shareThen), className: 'hidden sm:table-cell' },
  { key: 'orders', label: 'Recent orders', sort: d => d.orderShare ?? -1 },
  { key: 'status', label: 'Still buying?', sort: d => Object.keys(STATUS).indexOf(d.status), asc: true },
  { key: 'area', label: 'Most exposed area', sort: d => d.topArea?.share ?? -1, className: 'hidden md:table-cell' },
]

function DependentsTable({ s }) {
  const [sort, setSort] = useState({ key: 'share', asc: false })
  const [showSmall, setShowSmall] = useState(false)
  const [only, setOnly] = useState(null)
  const rows = useMemo(() => {
    const col = COLUMNS.find(c => c.key === sort.key)
    return s.dependents
      .filter(d => showSmall || !d.small)
      .filter(d => !only || d.status === only)
      .sort((a, b) => {
        const va = col.sort(a), vb = col.sort(b)
        const cmp = typeof va === 'string' ? va.localeCompare(vb) : va - vb
        return sort.asc ? cmp : -cmp
      })
  }, [s, sort, showSmall, only])

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        {[null, ...Object.keys(STATUS)].map(k => (
          <button key={k ?? 'all'} onClick={() => setOnly(k)} aria-pressed={only === k}
            className={`rounded-full border px-3 py-1 ${only === k
              ? 'border-stone-900 bg-stone-900 text-white dark:border-stone-100 dark:bg-stone-100 dark:text-stone-900'
              : 'border-stone-300 dark:border-stone-700 hover:border-stone-500'}`}>
            {k ? STATUS[k].label : 'All'}
          </button>
        ))}
        <label className="ml-auto flex items-center gap-2 text-stone-600 dark:text-stone-400">
          <input type="checkbox" checked={showSmall} onChange={e => setShowSmall(e.target.checked)} />
          Include small arsenals
        </label>
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-sm min-w-[34rem]">
          <thead>
            <tr className="text-left text-xs text-stone-500 border-b border-stone-200 dark:border-stone-800">
              {COLUMNS.map(c => (
                <th key={c.key} className={`py-2 pr-3 font-medium ${c.className || ''}`}>
                  <button onClick={() => setSort(p => p.key === c.key ? { key: c.key, asc: !p.asc } : { key: c.key, asc: !!c.asc })}
                    className="hover:text-stone-900 dark:hover:text-stone-100">
                    {c.label}{sort.key === c.key ? (sort.asc ? ' ↑' : ' ↓') : ''}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map(d => (
              <tr key={d.iso3} className="border-b border-stone-100 dark:border-stone-900">
                <td className="py-2 pr-3">
                  <Link to={`/country/${d.iso3}`} className="font-medium underline-offset-2 hover:underline">{d.name}</Link>
                  {d.inherited && <span className="ml-1 text-xs text-stone-400" title="Includes equipment inherited at independence">inherited</span>}
                  {d.small && <span className="ml-1 text-xs text-stone-400">small</span>}
                </td>
                <td className="py-2 pr-3">
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-20 rounded-full bg-stone-200 dark:bg-stone-800 overflow-hidden">
                      <div className="h-full rounded-full" style={{ width: `${d.share * 100}%`, backgroundColor: originColor(s.iso3) }} />
                    </div>
                    <span className="tabular">{pct(d.share)}</span>
                  </div>
                </td>
                <td className="py-2 pr-3 tabular text-stone-600 dark:text-stone-400 hidden sm:table-cell">
                  {d.shareThen == null ? '—' : `${pct(d.shareThen)} → ${pct(d.share)}`}
                </td>
                <td className="py-2 pr-3 tabular" title={`${tiv(d.ordersTiv)} TIV ordered since ${s.recentFrom}`}>
                  {d.orderShare == null ? '—' : pct(d.orderShare)}
                </td>
                <td className="py-2 pr-3"><StatusBadge status={d.status} /></td>
                <td className="py-2 hidden md:table-cell text-stone-600 dark:text-stone-400">
                  {d.topArea ? `${d.topArea.capability} (${pct(d.topArea.share)})` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && <p className="py-4 text-sm text-stone-500">No countries match.</p>}
      </div>
    </div>
  )
}

function Trend({ s }) {
  const rows = s.series.years.map((y, i) => ({ year: y, abroad: s.series.abroadTiv[i], majority: s.series.nMajority[i] }))
    .filter(r => r.abroad > 0)
  const color = originColor(s.iso3)
  return (
    <div className="grid gap-6 md:grid-cols-2">
      {[['abroad', 'Equipment in service abroad (TIV)', v => tiv(v)], ['majority', 'Countries where it is the majority of the arsenal', v => v]].map(([key, label, fmt]) => (
        <div key={key}>
          <div className="text-xs text-stone-500 mb-2">{label}</div>
          <div className="h-40">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={rows} margin={{ top: 4, right: 4, bottom: 0, left: -8 }}>
                <CartesianGrid vertical={false} strokeOpacity={0.15} />
                <XAxis dataKey="year" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={24} />
                <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={fmt} allowDecimals={false} />
                <Tooltip formatter={v => fmt(v)} labelClassName="text-xs" contentStyle={{ fontSize: 12 }} />
                <Area dataKey={key} type="monotone" stroke={color} fill={color} fillOpacity={0.25} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function SupplierPage() {
  const { iso3 } = useParams()
  const [s, setS] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setS(null); setError(null)
    loadSupplier(iso3.toUpperCase()).then(setS).catch(() => setError(`No supplier profile for “${iso3}”.`))
  }, [iso3])

  if (error) return <p>{error} <Link className="underline" to="/suppliers">Back to suppliers</Link></p>
  if (!s) return <p className="text-stone-500">Loading…</p>

  const name = originInSentence({ [s.iso3]: s.name }, s.iso3)
  const c = s.statusCounts
  const judged = c.staying + c.diversifying + c.moving_away

  return (
    <article>
      <Link to="/suppliers" className="text-sm text-stone-500 hover:text-stone-900 dark:hover:text-stone-100">← All suppliers</Link>
      <h1 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight">{s.name}</h1>
      <p className="mt-3 text-lg leading-relaxed max-w-3xl text-stone-700 dark:text-stone-300">
        <strong className="text-stone-900 dark:text-stone-100">{s.nMajority}</strong> {s.nMajority === 1 ? 'military runs' : 'militaries run'} mostly
        on equipment designed in {name}, and <strong className="text-stone-900 dark:text-stone-100">{s.nQuarter}</strong> depend
        on it for at least a quarter of their arsenal.
        {judged > 0 && <> Judging by their orders since {s.recentFrom}, {c.staying} are staying with it, {c.diversifying} are diversifying and {c.moving_away} are moving away.</>}
      </p>

      <Section title="Still buying?"
        subtitle={`Each dot is a country that depends on ${name} for at least a quarter of its arsenal. Dots below the dashed line are ordering less from ${name} than they currently depend on it — their dependence will shrink as old equipment retires.`}>
        <StillBuying s={s} />
      </Section>

      <Section title={`Countries that depend on ${name}`}
        subtitle={`Share of each country’s estimated arsenal designed in ${name} (${s.dataYear}), change since ${s.compareYear}, and share of equipment ordered since ${s.recentFrom}.`}>
        <DependentsTable s={s} />
      </Section>

      <Section title="Where the dependence sits"
        subtitle={`For each capability area, the number of countries where ${name}-designed equipment is the majority of that area.`}>
        <table className="w-full max-w-xl text-sm">
          <thead>
            <tr className="text-left text-xs text-stone-500 border-b border-stone-200 dark:border-stone-800">
              <th className="py-2 pr-3 font-medium">Capability area</th>
              <th className="py-2 pr-3 font-medium text-right">Countries, majority</th>
              <th className="py-2 font-medium text-right" title={TIV_HELP}>In service abroad (TIV)</th>
            </tr>
          </thead>
          <tbody>
            {[...s.areas].sort((a, b) => b.nMajority - a.nMajority || b.tiv - a.tiv).map(a => (
              <tr key={a.capability} className="border-b border-stone-100 dark:border-stone-900">
                <td className="py-2 pr-3">{a.capability}</td>
                <td className="py-2 pr-3 text-right tabular">{a.nMajority || '—'}</td>
                <td className="py-2 text-right tabular text-stone-600 dark:text-stone-400">{tiv(a.tiv)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="Over time" subtitle="Estimated equipment of this design origin in service outside it, and how many militaries it dominates.">
        <Trend s={s} />
      </Section>

      <p className="mt-12 text-xs text-stone-500 max-w-3xl">
        Based on imported and inherited equipment, net of re-exports; a country’s own production is not counted.
        “Recent orders” are by design origin, so Soviet-designed equipment bought second-hand from a third country still
        counts. Countries with arsenals under {s.smallArsenal} TIV are left out of counts and the chart.{' '}
        <Link to="/method#suppliers" className="underline">How this works</Link>.
      </p>
    </article>
  )
}
