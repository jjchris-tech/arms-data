// Fixed colours for the origins that recur across many countries, so Russia is
// the same red on every page. Anything else gets a muted fallback colour.
const ORIGIN_COLORS = {
  RUS: '#dc2626',
  USA: '#2563eb',
  FRA: '#7c3aed',
  GBR: '#0891b2',
  DEU: '#ca8a04',
  CHN: '#ea580c',
  ISR: '#0d9488',
  ITA: '#16a34a',
  KOR: '#db2777',
  ESP: '#9333ea',
  SWE: '#4f46e5',
  UKR: '#eab308',
  NLD: '#f97316',
  TUR: '#be123c',
  IND: '#65a30d',
  CZE: '#0284c7',
}
const FALLBACK = ['#64748b', '#78716c', '#71717a', '#6b7280', '#57534e']
export const OTHER = 'OTHER'
export const OTHER_COLOR = '#cbd5e1'

// Derived from the code itself so an origin keeps its colour across panels
export function originColor(iso3) {
  if (iso3 === OTHER) return OTHER_COLOR
  if (ORIGIN_COLORS[iso3]) return ORIGIN_COLORS[iso3]
  const h = [...(iso3 || '')].reduce((a, c) => a + c.charCodeAt(0), 0)
  return FALLBACK[h % FALLBACK.length]
}

export function originName(origins, iso3) {
  if (iso3 === OTHER) return 'Other'
  return origins?.[iso3] || iso3
}

/** Name for use mid-sentence: "designed in the United States". */
export function originInSentence(origins, iso3) {
  const name = originName(origins, iso3)
  return /^(United |Netherlands|Philippines|UAE|Czech Republic)/.test(name) ? `the ${name}` : name
}

export function pct(x, digits = 0) {
  if (x == null || Number.isNaN(x)) return '—'
  return `${(x * 100).toFixed(digits)}%`
}

export function tiv(x) {
  if (x == null || Number.isNaN(x)) return '—'
  if (x >= 100) return Math.round(x).toLocaleString('en-US')
  if (x >= 1) return x.toFixed(1)
  return x > 0 ? '<1' : '0'
}

export const TIV_HELP =
  "SIPRI trend-indicator value (millions). It measures military capability transferred, not money paid — use it to compare volumes, not prices."
