import { OTHER } from './format'

/** In-service TIV by origin at a given year: { RUS: 123, ... } */
export function holdingsAt(profile, year) {
  const { years, byOrigin } = profile.inService
  const i = years.indexOf(year)
  const out = {}
  if (i < 0) return out
  for (const [o, series] of Object.entries(byOrigin)) {
    if (series[i] > 0) out[o] = series[i]
  }
  return out
}

export function sharesOf(values) {
  const total = Object.values(values).reduce((s, v) => s + v, 0)
  const out = {}
  for (const [k, v] of Object.entries(values)) out[k] = total > 0 ? v / total : 0
  return { total, shares: out }
}

/** Origins ranked by current holdings, then by historical holdings. */
export function rankedOrigins(profile) {
  const now = holdingsAt(profile, profile.dataYear)
  const ever = {}
  for (const [o, s] of Object.entries(profile.inService.byOrigin)) ever[o] = s.reduce((a, v) => a + (v || 0), 0)
  return Object.keys(ever).sort((a, b) => (now[b] || 0) - (now[a] || 0) || ever[b] - ever[a])
}

/**
 * Stacked-chart rows: one row per year with shares for the top `n` origins and
 * everything else folded into OTHER. Years with no holdings are dropped.
 */
export function shareRows(profile, n = 5) {
  const top = rankedOrigins(profile).slice(0, n)
  const { years, byOrigin } = profile.inService
  const rows = []
  years.forEach((year, i) => {
    let total = 0
    for (const s of Object.values(byOrigin)) total += s[i] || 0
    if (total <= 0) return
    const row = { year, total }
    let rest = total
    for (const o of top) {
      const v = byOrigin[o]?.[i] || 0
      row[o] = v / total
      rest -= v
    }
    row[OTHER] = Math.max(0, rest) / total
    rows.push(row)
  })
  return { keys: [...top, OTHER], rows }
}

/** Share of new orders by origin, grouped into periods. */
export const ORDER_PERIODS = [
  [1990, 1999], [2000, 2009], [2010, 2014], [2015, 2019], [2020, 2024],
]

export function orderPeriods(profile, n = 5) {
  const { years, byOrigin } = profile.orders
  const totals = {}
  for (const [o, s] of Object.entries(byOrigin)) totals[o] = s.reduce((a, v) => a + (v || 0), 0)
  const recent = {}
  years.forEach((y, i) => {
    if (y >= 2015) for (const [o, s] of Object.entries(byOrigin)) recent[o] = (recent[o] || 0) + (s[i] || 0)
  })
  const top = Object.keys(totals)
    .sort((a, b) => (recent[b] || 0) - (recent[a] || 0) || totals[b] - totals[a])
    .slice(0, n)

  return {
    keys: [...top, OTHER],
    periods: ORDER_PERIODS.filter(([start]) => start <= profile.dataYear).map(([start, end]) => {
      const sums = {}
      years.forEach((y, i) => {
        if (y < start || y > end) return
        for (const [o, s] of Object.entries(byOrigin)) {
          const key = top.includes(o) ? o : OTHER
          sums[key] = (sums[key] || 0) + (s[i] || 0)
        }
      })
      const { total, shares } = sharesOf(sums)
      return { label: `${start}–${String(Math.min(end, profile.dataYear)).slice(2)}`, total, shares }
    }),
  }
}

/** Plain-language headline for the country page. */
export function headline(profile) {
  const now = sharesOf(holdingsAt(profile, profile.dataYear))
  if (now.total <= 0) return null
  const [top, topShare] = Object.entries(now.shares).sort((a, b) => b[1] - a[1])[0]
  const then = sharesOf(holdingsAt(profile, 2000))
  const thenShare = then.total > 0 ? then.shares[top] || 0 : null

  // Capability most dependent on the top origin (ignoring tiny areas)
  const weighty = profile.exposure.filter(e => e.total >= now.total * 0.05)
  const worst = weighty
    .map(e => ({ cap: e.capability, share: (e.byOrigin[top] || 0) / e.total }))
    .sort((a, b) => b.share - a.share)[0]

  return { top, topShare, thenShare, worst }
}
