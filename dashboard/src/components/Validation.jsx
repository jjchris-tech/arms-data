import { Fragment, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { loadIndex, loadValidation } from '../lib/data'
import { originName, pct } from '../lib/format'
import { VerdictBadge } from './FactbookCheck'

function Score({ label, r, note }) {
  if (!r?.n) return null
  return (
    <div className="rounded-lg border border-stone-200 dark:border-stone-800 p-4">
      <div className="text-3xl font-semibold tabular text-stone-900 dark:text-stone-100">{pct(r.agreeRate)}</div>
      <div className="mt-1 text-sm font-medium text-stone-900 dark:text-stone-100">{label}</div>
      <div className="mt-1 text-xs text-stone-500">
        {r.agree} agree{r.partial ? `, ${r.partial} partly` : ''}, {r.disagree} differ, of {r.n} countries. {note}
      </div>
    </div>
  )
}

/** Method-page section: how our estimates compare with the CIA World Factbook. */
export default function Validation() {
  const [data, setData] = useState(null)
  const [open, setOpen] = useState(null)

  useEffect(() => {
    Promise.all([loadValidation(), loadIndex()]).then(([v, index]) => setData({ v, index })).catch(() => setData(false))
  }, [])

  if (data === false) return <p className="mt-3 text-sm text-stone-500">Validation results could not be loaded.</p>
  if (!data) return <p className="mt-3 text-sm text-stone-500">Loading…</p>

  const { v, index } = data
  const names = Object.fromEntries(index.countries.map(c => [c.iso3, c.name]))
  const rows = Object.entries(v.countries)
    .filter(([, r]) => r.verdict === 'partial' || r.verdict === 'disagree')
    .sort(([a, ra], [b, rb]) => ra.verdict.localeCompare(rb.verdict) || (names[a] || a).localeCompare(names[b] || b))

  return (
    <>
      <p className="mt-3">
        The CIA World Factbook (final edition, 2025; public domain) describes each military’s equipment in a sentence such as
        <em> “the inventory consists mostly of Russian/Soviet-origin equipment along with smaller quantities from China”</em>.
        That is an independent source, so every country page compares it with our estimate. We parse which origins the
        Factbook names as the main source and which it merely lists, then ask whether our largest design origin matches.
      </p>
      <div className="mt-5 grid gap-3 sm:grid-cols-2 not-prose">
        <Score label="Strong test: Factbook names a main source" r={v.summary.dominant}
          note="Agree = our largest origin is that main source." />
        <Score label="Weak test: Factbook only lists suppliers" r={v.summary.mixed}
          note="Agree = our largest origin is among those listed." />
      </div>

      <h3 className="mt-6 font-medium text-stone-900 dark:text-stone-100">Where we differ, and why</h3>
      <ul className="mt-2 list-disc pl-5 space-y-2">
        <li><strong>Inherited stockpiles.</strong> Former Soviet and Yugoslav republics (Ukraine, Uzbekistan, Turkmenistan,
          Tajikistan, Serbia, Montenegro, Bosnia) took over equipment at independence. No sale was ever recorded, so it is
          invisible to SIPRI and to us. The Factbook says “mostly Soviet”; we see only what they bought afterwards.</li>
        <li><strong>Old equipment kept in service.</strong> Some militaries (e.g. Bulgaria, Namibia) still operate Soviet
          kit delivered 40+ years ago, beyond our assumed service lives. Lengthening every service life by 25–50% raises the
          strong-test agreement to roughly 85–87%. We have not tuned the lives to this source, so the score above stays an
          honest out-of-sample check.</li>
        <li><strong>Different measures.</strong> We weight equipment by military capability (TIV), so a few large ships
          can outweigh many older land vehicles that a prose description would emphasise.</li>
      </ul>

      <h3 className="mt-6 font-medium text-stone-900 dark:text-stone-100">All countries where we differ ({rows.length})</h3>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-sm min-w-[32rem]">
          <thead>
            <tr className="text-left text-xs text-stone-500 border-b border-stone-200 dark:border-stone-800">
              <th className="py-2 pr-3 font-medium">Country</th>
              <th className="py-2 pr-3 font-medium">Factbook main source</th>
              <th className="py-2 pr-3 font-medium">Our largest origins</th>
              <th className="py-2 font-medium">Result</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([iso3, r]) => (
              <Fragment key={iso3}>
                <tr onClick={() => setOpen(open === iso3 ? null : iso3)}
                  className="border-b border-stone-100 dark:border-stone-900 cursor-pointer hover:bg-stone-100 dark:hover:bg-stone-900 align-top">
                  <td className="py-2 pr-3">
                    <Link to={`/country/${iso3}`} onClick={e => e.stopPropagation()} className="underline underline-offset-2">{names[iso3] || iso3}</Link>
                    {r.smallArsenal && <span className="ml-1 text-xs text-stone-400">small</span>}
                  </td>
                  <td className="py-2 pr-3">
                    {r.factbookPrimary.length
                      ? r.factbookPrimary.map(o => originName(index.origins, o)).join(', ')
                      : <span className="text-stone-400">none named</span>}
                    {r.factbookDomestic && <div className="text-xs text-stone-500">notes major domestic production</div>}
                  </td>
                  <td className="py-2 pr-3 tabular">{r.ours.slice(0, 2).map(o => `${originName(index.origins, o.origin)} ${pct(o.share)}`).join(', ')}</td>
                  <td className="py-2"><VerdictBadge verdict={r.verdict} /></td>
                </tr>
                {open === iso3 && (
                  <tr className="border-b border-stone-100 dark:border-stone-900 bg-stone-100/60 dark:bg-stone-900/60">
                    <td colSpan={4} className="px-3 py-3 text-xs text-stone-600 dark:text-stone-400">“{r.factbookText}”</td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-stone-500">
        “Western” and “European” in the Factbook are matched against any US or European design origin. Click a row for
        the full Factbook text.
      </p>
    </>
  )
}
