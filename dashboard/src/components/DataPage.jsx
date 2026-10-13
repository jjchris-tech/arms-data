import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { downloadUrl, loadManifest } from '../lib/data'

function size(bytes) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export default function DataPage() {
  const [m, setM] = useState(null)
  const [error, setError] = useState(null)
  const [open, setOpen] = useState(null)

  useEffect(() => { loadManifest().then(setM).catch(e => setError(e.message)) }, [])
  if (error) return <p className="text-red-600">{error}</p>
  if (!m) return <p className="text-stone-500">Loading…</p>

  return (
    <article className="max-w-3xl leading-relaxed text-stone-700 dark:text-stone-300">
      <h1 className="text-3xl font-semibold tracking-tight text-stone-900 dark:text-stone-100">Data</h1>
      <p className="mt-4">
        Everything on this site as CSV files: the estimates behind every chart, for all countries. Values are SIPRI
        trend-indicator values (TIV, millions) — a measure of military capability, not money.{' '}
        <Link to="/method" className="underline">How the estimates are made</Link>.
      </p>
      <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        <dt className="text-stone-500">Data year</dt><dd>{m.dataYear}</dd>
        <dt className="text-stone-500">SIPRI release</dt><dd>{m.sipriRelease || '—'}</dd>
        <dt className="text-stone-500">Built</dt><dd>{m.generated}</dd>
      </dl>

      <ul className="mt-8 space-y-4">
        {m.files.map(f => (
          <li key={f.file} className="rounded-lg border border-stone-200 dark:border-stone-800 p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="font-medium text-stone-900 dark:text-stone-100">{f.title}</h2>
              <a href={downloadUrl(f.file)} download className="text-sm underline underline-offset-2">
                {f.file} · {f.rows.toLocaleString('en-US')} rows · {size(f.bytes)}
              </a>
            </div>
            <p className="mt-1 text-sm">{f.description}</p>
            {f.licence && <p className="mt-1 text-xs text-stone-500">Licence: {f.licence}</p>}
            <button onClick={() => setOpen(open === f.file ? null : f.file)} className="mt-2 text-xs underline underline-offset-2">
              {open === f.file ? 'Hide columns' : `Columns (${Object.keys(f.columns).length})`}
            </button>
            {open === f.file && (
              <table className="mt-2 w-full text-xs">
                <tbody>
                  {Object.entries(f.columns).map(([col, desc]) => (
                    <tr key={col} className="border-t border-stone-100 dark:border-stone-900 align-top">
                      <td className="py-1.5 pr-3 font-mono text-stone-900 dark:text-stone-100 whitespace-nowrap">{col}</td>
                      <td className="py-1.5">{desc}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </li>
        ))}
      </ul>

      <h2 className="mt-10 text-lg font-semibold tracking-tight text-stone-900 dark:text-stone-100">Citing and reuse</h2>
      <p className="mt-3 text-sm">{m.attribution}.</p>
      <p className="mt-2 text-sm">
        These files contain this site’s estimates and aggregates, not SIPRI’s deal records. For the underlying deals, use the{' '}
        <a className="underline" href="https://armstransfers.sipri.org/" target="_blank" rel="noreferrer">SIPRI Arms Transfers Database</a>{' '}
        directly. The inherited-equipment file derives from Wikipedia and is shared under CC BY-SA 4.0.
      </p>
    </article>
  )
}
