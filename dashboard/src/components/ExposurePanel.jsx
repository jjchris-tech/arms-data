import { originColor, originInSentence, originName, pct, tiv } from '../lib/format'
import { holdingsAt, sharesOf } from '../lib/profile'

/**
 * "If one design origin stopped supporting its equipment, how much of each
 * capability area would be affected?" Rows are clickable and open the deals
 * behind the number.
 */
export default function ExposurePanel({ profile, origin, onOriginChange, onSelectCapability }) {
  const { total, shares } = sharesOf(holdingsAt(profile, profile.dataYear))
  const choices = Object.entries(shares).filter(([, s]) => s >= 0.02).sort((a, b) => b[1] - a[1]).map(([o]) => o)
  if (!total || !profile.exposure.length) {
    return <p className="text-sm text-stone-500">No imported equipment estimated in service in {profile.dataYear}.</p>
  }
  const color = originColor(origin)

  return (
    <div>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Choose supplier">
        {choices.map(o => (
          <button
            key={o}
            onClick={() => onOriginChange(o)}
            aria-pressed={o === origin}
            className={`rounded-full border px-3 py-1 text-sm transition-colors ${
              o === origin
                ? 'border-stone-900 bg-stone-900 text-white dark:border-stone-100 dark:bg-stone-100 dark:text-stone-900'
                : 'border-stone-300 dark:border-stone-700 hover:border-stone-500'
            }`}
          >
            {originName(profile.origins, o)}
          </button>
        ))}
      </div>

      <p className="mt-4 text-sm text-stone-600 dark:text-stone-400">
        Share of each area’s imported equipment that was designed in <strong className="text-stone-900 dark:text-stone-100">{originInSentence(profile.origins, origin)}</strong> —
        {' '}{pct(shares[origin])} of the imported arsenal overall.
      </p>

      <ul className="mt-3 divide-y divide-stone-100 dark:divide-stone-900">
        {profile.exposure.map(e => {
          const v = e.byOrigin[origin] || 0
          const s = v / e.total
          const weight = e.total / total
          return (
            <li key={e.capability}>
              <button
                onClick={() => onSelectCapability?.(e.capability)}
                disabled={v <= 0 || !onSelectCapability}
                className="w-full grid grid-cols-[minmax(0,10rem)_1fr_3.5rem] sm:grid-cols-[12rem_1fr_3.5rem_6rem] items-center gap-3 py-2 text-left text-sm enabled:hover:bg-stone-100 dark:enabled:hover:bg-stone-900 rounded"
                title={v > 0 && onSelectCapability ? 'Show the deals behind this number' : undefined}
              >
                <span className="truncate">{e.capability}</span>
                <span className="h-2.5 rounded-full bg-stone-200 dark:bg-stone-800 overflow-hidden">
                  <span className="block h-full rounded-full" style={{ width: `${s * 100}%`, backgroundColor: color }} />
                </span>
                <span className={`tabular text-right ${s >= 0.5 ? 'font-semibold' : ''}`}>{pct(s)}</span>
                <span className="hidden sm:block tabular text-right text-xs text-stone-500" title="Share of the whole imported arsenal">
                  {pct(weight)} of arsenal
                </span>
              </button>
            </li>
          )
        })}
      </ul>
      <p className="mt-2 text-xs text-stone-500">
        In-service estimate for {profile.dataYear}.{onSelectCapability && <> Click an area to see the deals behind it.</>} Values in TIV: {tiv(total)} imported in total.
      </p>
    </div>
  )
}
