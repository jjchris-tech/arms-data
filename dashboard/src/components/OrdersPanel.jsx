import { originColor, originName, pct, tiv } from '../lib/format'
import { orderPeriods } from '../lib/profile'

function StackedBar({ shares, keys, height = 'h-3' }) {
  return (
    <div className={`flex ${height} w-full overflow-hidden rounded-full bg-stone-200 dark:bg-stone-800`}>
      {keys.map(k => shares[k] > 0 && (
        <div key={k} style={{ width: `${shares[k] * 100}%`, backgroundColor: originColor(k) }} />
      ))}
    </div>
  )
}

export default function OrdersPanel({ profile, onShowBacklog }) {
  const { total, byOrigin } = profile.backlog
  const backlogKeys = Object.keys(byOrigin)
  const backlogShares = Object.fromEntries(backlogKeys.map(k => [k, byOrigin[k] / total]))
  const { keys, periods } = orderPeriods(profile)

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <div>
        <h3 className="text-sm font-medium">On order, not yet delivered</h3>
        {total > 0 ? (
          <>
            <div className="mt-3"><StackedBar shares={backlogShares} keys={backlogKeys} /></div>
            <ul className="mt-3 space-y-1 text-sm">
              {backlogKeys.slice(0, 6).map(k => (
                <li key={k} className="flex items-center gap-2">
                  <span className="inline-block size-2.5 rounded-sm" style={{ backgroundColor: originColor(k) }} />
                  <span className="flex-1">{originName(profile.origins, k)}</span>
                  <span className="tabular text-stone-500">{tiv(byOrigin[k])}</span>
                  <span className="tabular w-10 text-right">{pct(backlogShares[k])}</span>
                </li>
              ))}
            </ul>
            {onShowBacklog && <button onClick={onShowBacklog} className="mt-3 text-sm underline underline-offset-2">
              Show the {tiv(total)} TIV of open deals
            </button>}
          </>
        ) : (
          <p className="mt-2 text-sm text-stone-500">No open deals recorded.</p>
        )}
      </div>

      <div>
        <h3 className="text-sm font-medium">New orders by period</h3>
        <p className="mt-1 text-xs text-stone-500">Orders lead deliveries by years, so a change of supplier shows here first.</p>
        <div className="mt-3 space-y-2.5">
          {periods.map(p => (
            <div key={p.label} className="grid grid-cols-[4.5rem_1fr_3.5rem] items-center gap-3 text-sm">
              <span className="tabular text-stone-600 dark:text-stone-400">{p.label}</span>
              {p.total > 0 ? <StackedBar shares={p.shares} keys={keys} height="h-2.5" /> : <span className="text-xs text-stone-400">no orders</span>}
              <span className="tabular text-right text-xs text-stone-500">{p.total > 0 ? tiv(p.total) : ''}</span>
            </div>
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs">
          {keys.map(k => (
            <span key={k} className="flex items-center gap-1.5">
              <span className="inline-block size-2 rounded-sm" style={{ backgroundColor: originColor(k) }} />
              {originName(profile.origins, k)}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
