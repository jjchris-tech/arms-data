import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { downloadCsv } from '../lib/csv'
import { loadUnVotes } from '../lib/data'
import { pct } from '../lib/format'
import { STATUS } from './SupplierPage'

const REGION_COLORS = {
  Africa: '#d97706', Asia: '#dc2626', Europe: '#2563eb', 'North America': '#7c3aed',
  'South America': '#16a34a', Oceania: '#0891b2',
}

const MODEL_ROWS = [
  ['bivariate', 'Russian-designed share only'],
  ['controls', '+ democracy and region'],
  ['full', '+ US-designed share and former Soviet republic'],
  ['fullWithoutBelarus', 'Same, without Belarus'],
  ['fullAllSizes', 'Same, including small arsenals'],
]

const num = (x, d = 3) => (x == null ? '—' : `${x >= 0 ? '+' : '−'}${Math.abs(x).toFixed(d)}`)
const pval = p => (p == null ? '—' : p < 0.001 ? '<0.001' : p.toFixed(3))

function H({ children }) {
  return <h2 className="mt-12 text-lg font-semibold tracking-tight text-stone-900 dark:text-stone-100">{children}</h2>
}

function ScatterTip({ active, payload }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="rounded-md border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 px-3 py-2 text-xs shadow-sm">
      <div className="font-medium">{d.name}</div>
      <div>Russian-designed share (2021): {pct(d.rusShare)}</div>
      <div>Alignment with Russia: {d.alignment.toFixed(2)}</div>
      <div className="text-stone-500">Yes {d.votes.yes} · Abstain {d.votes.abstain} · No {d.votes.no}{d.votes.absent ? ` · Absent ${d.votes.absent}` : ''}</div>
    </div>
  )
}

function MainChart({ r }) {
  const navigate = useNavigate()
  const points = r.countries.filter(c => c.inSample).map(c => ({ ...c, x: c.rusShare, y: c.alignment, z: 1 }))
  const regions = Object.keys(REGION_COLORS)
  return (
    <div>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 8, right: 16, bottom: 24, left: 0 }}>
            <CartesianGrid strokeOpacity={0.15} />
            <XAxis type="number" dataKey="x" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tickFormatter={v => pct(v)} tick={{ fontSize: 11 }}
              label={{ value: `Russian-designed share of arsenal, ${r.baseYear}`, position: 'insideBottom', offset: -12, fontSize: 11 }} />
            <YAxis type="number" dataKey="y" domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} tick={{ fontSize: 11 }}
              label={{ value: 'Alignment with Russia', angle: -90, position: 'insideLeft', offset: 14, fontSize: 11, dy: 60 }} />
            <ZAxis type="number" dataKey="z" range={[36, 36]} />
            <Tooltip content={<ScatterTip />} cursor={false} />
            {regions.map(reg => (
              <Scatter key={reg} data={points.filter(p => p.region === reg)} fill={REGION_COLORS[reg]} fillOpacity={0.6}
                onClick={p => navigate(`/country/${p.iso3}`)} cursor="pointer" isAnimationActive={false} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs">
        {regions.map(reg => (
          <span key={reg} className="inline-flex items-center gap-1.5">
            <span className="inline-block size-2 rounded-full" style={{ backgroundColor: REGION_COLORS[reg] }} />{reg}
          </span>
        ))}
      </div>
    </div>
  )
}

function Bars({ rows, labelKey, color }) {
  return (
    <div className="space-y-2 max-w-xl">
      {rows.map(b => (
        <div key={b[labelKey]} className="grid grid-cols-[8.5rem_1fr_6rem] items-center gap-3 text-sm">
          <span>{b.label ?? STATUS[b.status]?.label}</span>
          <div className="h-3 rounded-full bg-stone-200 dark:bg-stone-800 overflow-hidden">
            <div className="h-full rounded-full" style={{ width: `${(b.meanAlignment || 0) * 100}%`, backgroundColor: color(b) }} />
          </div>
          <span className="tabular text-right">{b.meanAlignment == null ? '—' : b.meanAlignment.toFixed(2)} <span className="text-xs text-stone-500">n={b.n}</span></span>
        </div>
      ))}
    </div>
  )
}

export default function UnVotes() {
  const [r, setR] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => { loadUnVotes().then(setR).catch(e => setError(e.message)) }, [])
  if (error) return <p className="text-red-600">{error}</p>
  if (!r) return <p className="text-stone-500">Loading…</p>

  const low = r.bands[0], high = r.bands[r.bands.length - 1]
  const full = r.models.full.terms
  const ideal = r.models.idealFull.terms.rus_share_10
  const core = r.resolutions.filter(x => x.core)
  const later = r.resolutions.find(x => !x.core)
  const sample = r.countries.filter(c => c.inSample)
  const exceptionsHigh = sample.filter(c => c.rusShare >= 0.5 && c.votes.yes > 0 && c.votes.no === 0 && c.votes.abstain === 0)
  const exceptionsLow = sample.filter(c => c.rusShare < 0.1 && c.votes.yes === 0)
  const byStatus = r.byStatus.filter(s => s.n > 0 && s.status !== 'few_orders')
  const staying = r.byStatus.find(s => s.status === 'staying'), moving = r.byStatus.find(s => s.status === 'moving_away')

  const csv = () => downloadCsv('un_votes_vs_russian_equipment.csv',
    ['iso3', 'name', 'region', 'rusShare', 'usaShare', 'alignment', 'yes', 'abstain', 'no', 'absent', 'idealPoint', 'democracy', 'postSoviet', 'russiaStatus', 'inSample'],
    r.countries.map(c => ({ ...c, ...c.votes })))

  return (
    <article className="max-w-3xl leading-relaxed text-stone-700 dark:text-stone-300">
      <p className="text-sm text-stone-500">Research</p>
      <h1 className="mt-1 text-3xl font-semibold tracking-tight text-stone-900 dark:text-stone-100">
        Do militaries that rely on Russian arms vote with Russia?
      </h1>
      <p className="mt-4 text-lg">
        They lean towards Russia — but only on Russia’s own war. Countries whose arsenals were at least half
        Russian-designed before the invasion abstained or voted with Russia far more often on the UN’s 2022–23 Ukraine
        votes (average alignment <strong className="text-stone-900 dark:text-stone-100">{high.meanAlignment.toFixed(2)}</strong>,
        against <strong className="text-stone-900 dark:text-stone-100">{low.meanAlignment.toFixed(2)}</strong> for countries
        under 10%, on a scale where 0.5 means abstaining throughout). The link survives controls for democracy, region and
        US-designed equipment. But once democracy and region are accounted for, the same countries are not measurably more
        anti-Western across UN votes in general.
      </p>

      <H>The pattern</H>
      <p className="mt-3 text-sm">
        Each dot is a country ({r.sample.n} with arsenals of at least {r.minArsenal} TIV; Russia and Ukraine excluded).
        Alignment: 0 = voted against Russia on all {core.length} resolutions, 0.5 = abstained throughout, 1 = voted with
        Russia every time. Rank correlation: {r.spearman.toFixed(2)} ({r.spearmanExcludingPostSoviet.toFixed(2)} excluding
        former Soviet republics).
      </p>
      <div className="mt-4"><MainChart r={r} /></div>

      <h3 className="mt-8 font-medium text-stone-900 dark:text-stone-100">Average alignment by dependence on Russian designs</h3>
      <div className="mt-3"><Bars rows={r.bands} labelKey="label" color={() => '#dc2626'} /></div>
      <p className="mt-2 text-xs text-stone-500">
        Share that never once voted for the resolutions: {pct(low.shareNeverYes)} of the least dependent group,{' '}
        {pct(high.shareNeverYes)} of the most dependent.
      </p>

      <H>Does it survive controls?</H>
      <p className="mt-3 text-sm">
        Countries that rely on Russian equipment differ in other ways: they are less democratic on average, concentrated in
        some regions, and many were part of the Soviet Union. Each row adds controls; the figure is the change in alignment
        for every 10 percentage points more of the arsenal being Russian-designed (OLS, robust standard errors).
      </p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-sm min-w-[32rem]">
          <thead>
            <tr className="text-left text-xs text-stone-500 border-b border-stone-200 dark:border-stone-800">
              <th className="py-2 pr-3 font-medium">Model</th>
              <th className="py-2 pr-3 font-medium text-right">Per +10 pts</th>
              <th className="py-2 pr-3 font-medium text-right">95% interval</th>
              <th className="py-2 pr-3 font-medium text-right">p</th>
              <th className="py-2 font-medium text-right">n</th>
            </tr>
          </thead>
          <tbody>
            {MODEL_ROWS.map(([key, label]) => {
              const m = r.models[key], t = m.terms.rus_share_10
              return (
                <tr key={key} className={`border-b border-stone-100 dark:border-stone-900 ${key === 'full' ? 'font-medium text-stone-900 dark:text-stone-100' : ''}`}>
                  <td className="py-2 pr-3">{label}</td>
                  <td className="py-2 pr-3 text-right tabular">{num(t.coef)}</td>
                  <td className="py-2 pr-3 text-right tabular">{num(t.ci[0])} to {num(t.ci[1])}</td>
                  <td className="py-2 pr-3 text-right tabular">{pval(t.p)}</td>
                  <td className="py-2 text-right tabular">{m.n}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-sm">
        In the full model, US-designed equipment pulls the other way ({num(full.usa_share_10.coef)} per 10 points,
        p = {pval(full.usa_share_10.p)}), and being a former Soviet republic adds little once equipment is accounted for
        ({num(full.post_soviet.coef, 2)}, p = {pval(full.post_soviet.p)}). Going from no Russian-designed equipment to an
        arsenal that is 80% Russian-designed corresponds to about {(full.rus_share_10.coef * 8).toFixed(2)} on the 0–1
        alignment scale — roughly the difference between voting for every resolution and abstaining on two of five.
      </p>

      <H>Specific to Russia’s war, not general alignment</H>
      <p className="mt-3 text-sm">
        As a check we used each country’s overall position across all recorded UN votes in {r.idealYear} (Voeten et al.’s
        ideal points; higher = closer to the US-led bloc). With the same controls, Russian-designed equipment shows no clear
        relationship with it ({num(ideal.coef)} per 10 points, interval {num(ideal.ci[0])} to {num(ideal.ci[1])},
        p = {pval(ideal.p)}). Dependence on Russian equipment goes with caution on votes about Russia itself, not with a
        broader anti-Western stance. (Distance from Russia’s own ideal point is not a usable measure: Russia sits mid-way
        along that scale at {num(r.idealPointRussia, 2)}, so states more anti-Western than Russia, like Syria or Iran,
        would look “far” from it.)
      </p>

      <H>Does switching suppliers go with switching votes?</H>
      <p className="mt-3 text-sm">
        Among countries at least a quarter dependent on Russian designs, those whose recent orders show them{' '}
        <Link to="/supplier/RUS" className="underline">staying with Russia</Link> sided with it most; those moving away, least.
      </p>
      <div className="mt-3"><Bars rows={byStatus} labelKey="status" color={b => STATUS[b.status].color} /></div>
      <ul className="mt-3 space-y-1 text-xs text-stone-500">
        {byStatus.map(s => <li key={s.status}><span className="font-medium">{STATUS[s.status].label}:</span> {s.countries.join(', ')}</li>)}
      </ul>
      <p className="mt-2 text-sm">
        The gap ({staying?.meanAlignment?.toFixed(2)} vs {moving?.meanAlignment?.toFixed(2)}) fits a story in which political
        and procurement choices move together. With so few countries per group it is descriptive, not a test.
      </p>

      <H>The exceptions</H>
      <p className="mt-3 text-sm">
        <strong className="text-stone-900 dark:text-stone-100">Heavily Russian-equipped, voted against Russia every time:</strong>{' '}
        {exceptionsHigh.map(c => c.name).join(', ')}. Most are EU or NATO members or candidates — alliance politics
        outweighed equipment.
      </p>
      <p className="mt-2 text-sm">
        <strong className="text-stone-900 dark:text-stone-100">Barely Russian-equipped, never voted against Russia:</strong>{' '}
        {exceptionsLow.map(c => c.name).join(', ')}. Several have long-standing political ties to Moscow dating from
        liberation movements, which arms data cannot capture.
      </p>

      <H>What this does and does not show</H>
      <ul className="mt-3 list-disc pl-5 space-y-2 text-sm">
        <li><strong>Association, not leverage.</strong> The data cannot tell whether Russia used arms dependence as leverage,
          whether governments avoided antagonising the supplier of their spare parts, or whether the same political
          closeness drove both arms purchases and votes.</li>
        <li><strong>Dependence is measured before the votes</strong> ({r.baseYear}), so the votes cannot have caused it —
          but decades of shared history shape both.</li>
        <li><strong>Imported and inherited equipment only.</strong> Big producers’ own arsenals are invisible; see the{' '}
          <Link to="/method" className="underline">method</Link>.</li>
        <li><strong>Later votes are not comparable.</strong> On {later?.id} ({later?.date}) the United States voted with
          Russia against Ukraine’s resolution, so “voting with Russia” stopped meaning the same thing.</li>
      </ul>

      <H>Data and method</H>
      <p className="mt-3 text-sm">
        Votes: recorded votes on {core.map(x => x.id).join(', ')} ({core[0].date} – {core[core.length - 1].date}), where
        Russia voted no each time. Per-country votes come from Wikipedia’s resolution pages (CC BY-SA 4.0); each was checked
        against the official tally, and only exact matches are used: ES-11/5 (November 2022) was left out because one
        country’s vote on the page disagrees with the tally.
        No = 1, abstain = 0.5, yes = 0; absences are not scored. Equipment: this site’s estimate for {r.baseYear}.
        Democracy: V-Dem electoral democracy index via Our World in Data (CC BY 4.0). Overall UN position: Voeten, Strezhnev
        and Bailey ideal points (CC0).
      </p>
      <p className="mt-3 text-sm">
        <button onClick={csv} className="underline underline-offset-2">Download the country-level data (CSV)</button>
      </p>
    </article>
  )
}
