import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { originColor, originName, pct, tiv } from '../lib/format'
import { shareRows } from '../lib/profile'

function ChartTooltip({ active, payload, label, origins }) {
  if (!active || !payload?.length) return null
  const total = payload[0]?.payload?.total
  return (
    <div className="rounded-md border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 px-3 py-2 text-xs shadow-sm">
      <div className="font-medium mb-1">{label} · {tiv(total)} TIV in service</div>
      {[...payload].reverse().filter(p => p.value > 0.0005).map(p => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span className="inline-block size-2 rounded-sm" style={{ backgroundColor: p.color }} />
          <span className="flex-1">{originName(origins, p.dataKey)}</span>
          <span className="tabular">{pct(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

export default function HoldingsChart({ profile }) {
  const { keys, rows } = shareRows(profile)
  if (!rows.length) return <p className="text-sm text-stone-500">No imported equipment estimated in service since {profile.seriesStart}.</p>

  return (
    <div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 mb-3 text-xs">
        {keys.map(k => (
          <span key={k} className="flex items-center gap-1.5">
            <span className="inline-block size-2.5 rounded-sm" style={{ backgroundColor: originColor(k) }} />
            {originName(profile.origins, k)}
          </span>
        ))}
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={rows} margin={{ top: 4, right: 4, bottom: 0, left: -12 }}>
            <CartesianGrid vertical={false} strokeOpacity={0.15} />
            <XAxis dataKey="year" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} minTickGap={24} />
            <YAxis tickFormatter={v => pct(v)} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} domain={[0, 1]} ticks={[0, 0.25, 0.5, 0.75, 1]} />
            <Tooltip content={<ChartTooltip origins={profile.origins} />} />
            {keys.map(k => (
              <Area
                key={k} dataKey={k} stackId="1" type="monotone"
                stroke={originColor(k)} fill={originColor(k)} fillOpacity={0.85} strokeWidth={0}
                isAnimationActive={false}
              />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
