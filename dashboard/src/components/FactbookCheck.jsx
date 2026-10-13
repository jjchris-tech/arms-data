import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { loadValidation } from '../lib/data'
import { originName, pct } from '../lib/format'

export const VERDICTS = {
  agree: { label: 'Agrees', className: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300' },
  partial: { label: 'Partly agrees', className: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300' },
  disagree: { label: 'Differs', className: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300' },
  not_comparable: { label: 'Not comparable', className: 'bg-stone-200 text-stone-700 dark:bg-stone-800 dark:text-stone-300' },
}

const EXPLAIN = {
  dominant: {
    agree: 'Our largest design origin is the main source the Factbook names.',
    partial: 'The Factbook names a different main source; ours appears only as our second origin or as a secondary supplier there.',
    disagree: 'Our largest design origin is not among the sources the Factbook names.',
  },
  mixed: {
    agree: 'The Factbook lists suppliers without naming a main one; our largest origin is among them.',
    disagree: 'The Factbook lists suppliers without naming a main one; our largest origin is not among them.',
  },
}

export function VerdictBadge({ verdict }) {
  const v = VERDICTS[verdict] || VERDICTS.not_comparable
  return <span className={`inline-block whitespace-nowrap rounded px-1.5 py-0.5 text-xs font-medium ${v.className}`}>{v.label}</span>
}

/** Independent check of one country's estimate against the CIA World Factbook. */
export default function FactbookCheck({ profile }) {
  const [check, setCheck] = useState(undefined)
  useEffect(() => {
    loadValidation().then(v => setCheck(v.countries[profile.iso3] || null)).catch(() => setCheck(null))
  }, [profile.iso3])
  if (!check) return null

  return (
    <div className="rounded-lg border border-stone-200 dark:border-stone-800 p-4 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium">Independent check: CIA World Factbook</span>
        <VerdictBadge verdict={check.verdict} />
      </div>
      <blockquote className="mt-2 border-l-2 border-stone-300 dark:border-stone-700 pl-3 text-stone-600 dark:text-stone-400">
        “{check.factbookText}”
      </blockquote>
      <p className="mt-2 text-xs text-stone-500">
        {EXPLAIN[check.test]?.[check.verdict]}{' '}
        Our estimate: {check.ours.map(o => `${originName(profile.origins, o.origin)} ${pct(o.share)}`).join(', ')}.
        {check.factbookDomestic && ' The Factbook also notes significant domestic production, which our import-based estimate cannot see.'}
        {' '}<Link to="/method#validation" className="underline">About this check</Link>
      </p>
    </div>
  )
}
