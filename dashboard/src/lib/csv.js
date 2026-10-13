function cell(v) {
  if (v == null) return ''
  const s = String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

/** Save rows as a CSV file. UTF-8 with BOM so Excel reads accented names correctly. */
export function downloadCsv(filename, columns, rows) {
  const lines = [columns.join(','), ...rows.map(r => columns.map(c => cell(r[c])).join(','))]
  const blob = new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** One country's in-service estimate by design origin and year (same columns as the full download). */
export function countrySeriesRows(profile) {
  const { years, byOrigin } = profile.inService
  const rows = []
  years.forEach((year, i) => {
    const total = Object.values(byOrigin).reduce((s, v) => s + (v[i] || 0), 0)
    for (const [o, s] of Object.entries(byOrigin)) {
      if ((s[i] || 0) > 0) {
        rows.push({
          iso3: profile.iso3, country: profile.name, year, design_origin_iso3: o,
          design_origin: profile.origins[o] || o, tiv_in_service: s[i], share: +(s[i] / total).toFixed(4),
        })
      }
    }
  })
  return rows
}
export const SERIES_COLUMNS = ['iso3', 'country', 'year', 'design_origin_iso3', 'design_origin', 'tiv_in_service', 'share']
