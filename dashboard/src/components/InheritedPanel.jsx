import { useState } from 'react'
import { Link } from 'react-router-dom'
import { originColor, originName, pct, tiv, TIV_HELP } from '../lib/format'
import { holdingsAt, sharesOf } from '../lib/profile'

const SHOWN = 12

function wikiLink(p) {
  return `https://en.wikipedia.org/w/index.php?title=${encodeURIComponent(p.title.replace(/ /g, '_'))}&oldid=${p.revid}`
}

/**
 * Equipment a successor state of the USSR or Yugoslavia took over at
 * independence. Not in SIPRI; sized from Wikipedia's equipment lists.
 */
export default function InheritedPanel({ profile }) {
  const [all, setAll] = useState(false)
  const inh = profile.inherited
  if (!inh) return null

  if (inh.status === 'no_quantities') {
    return (
      <p className="text-sm text-stone-600 dark:text-stone-400 max-w-3xl">
        {profile.name} took over Soviet or Yugoslav equipment at independence. No transfer was recorded, so SIPRI cannot
        see it, and the equipment lists we use give no quantities for {profile.name}, so it is <strong>not included</strong>.
        Its dependence on Soviet/Russian or Yugoslav designs is likely understated here.
      </p>
    )
  }

  const { total } = sharesOf(holdingsAt(profile, profile.dataYear))
  const rows = all ? inh.rows : inh.rows.slice(0, SHOWN)

  return (
    <div>
      <p className="text-sm text-stone-600 dark:text-stone-400 max-w-3xl">
        {profile.name} took over Soviet or Yugoslav equipment at independence. No transfer was recorded, so SIPRI cannot
        see it. We add what is listed as in service today, valued at SIPRI’s unit value for the same system as
        second-hand (×0.4), and subtract anything SIPRI already counts. It makes up{' '}
        <strong className="text-stone-900 dark:text-stone-100">{pct(inh.total / total)}</strong> of the arsenal above
        ({tiv(inh.total)} TIV), assumed held since {inh.since}.
      </p>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-sm min-w-[34rem]">
          <thead>
            <tr className="text-left text-xs text-stone-500 border-b border-stone-200 dark:border-stone-800">
              <th className="py-2 pr-3 font-medium">System</th>
              <th className="py-2 pr-3 font-medium">Design origin</th>
              <th className="py-2 pr-3 font-medium text-right" title="Quantity in service per the source list">Listed</th>
              <th className="py-2 pr-3 font-medium text-right" title="Units SIPRI already counts in service; subtracted to avoid double counting">In SIPRI</th>
              <th className="py-2 font-medium text-right" title={TIV_HELP}>Added (TIV)</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={`${r.system}-${i}`} className="border-b border-stone-100 dark:border-stone-900 align-top">
                <td className="py-2 pr-3">
                  <div className="font-medium">{r.system}</div>
                  <div className="text-xs text-stone-500">{r.cap}</div>
                </td>
                <td className="py-2 pr-3">
                  <span className="inline-flex items-center gap-1.5">
                    <span className="inline-block size-2 rounded-sm" style={{ backgroundColor: originColor(r.origin) }} />
                    {originName(profile.origins, r.origin)}
                  </span>
                </td>
                <td className="py-2 pr-3 tabular text-right">
                  {r.quantity}
                  {r.launchersPerUnit > 1 && (
                    <div className="text-xs text-stone-500" title="SIPRI counts this system per battalion, the list per launcher">
                      ≈{tiv(r.quantity / r.launchersPerUnit)} battalions
                    </div>
                  )}
                </td>
                <td className="py-2 pr-3 tabular text-right text-stone-500">{r.recordedUnits ? tiv(r.recordedUnits) : '—'}</td>
                <td className="py-2 tabular text-right">{tiv(r.tiv)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {inh.rows.length > SHOWN && (
        <button onClick={() => setAll(a => !a)} className="mt-2 text-sm underline underline-offset-2">
          {all ? 'Show fewer' : `Show all ${inh.rows.length} systems`}
        </button>
      )}

      <p className="mt-3 text-xs text-stone-500 max-w-3xl">
        Source: Wikipedia ({inh.pages.map((p, i) => (
          <span key={p.revid}>{i > 0 && ', '}<a className="underline" href={wikiLink(p)} target="_blank" rel="noreferrer">{p.title}</a></span>
        ))}; CC BY-SA 4.0), which mostly cites IISS <em>Military Balance</em>. Today’s counts are applied back to {inh.since},
        so earlier years are approximate.
        {inh.unmatched > 0 && <> {inh.unmatched} listed items could not be matched to a system SIPRI tracks — mostly trucks,
          small arms and light mortars, which are outside its scope — and are not counted.</>}
        {' '}<Link to="/method#inherited" className="underline">How this works</Link>.
      </p>
    </div>
  )
}
