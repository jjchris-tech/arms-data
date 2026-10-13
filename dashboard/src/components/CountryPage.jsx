import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { loadCountry } from '../lib/data'
import { originInSentence, pct } from '../lib/format'
import { headline, holdingsAt, sharesOf } from '../lib/profile'
import DealsTable from './DealsTable'
import ExposurePanel from './ExposurePanel'
import HoldingsChart from './HoldingsChart'
import OrdersPanel from './OrdersPanel'

function Section({ title, subtitle, children, sectionRef }) {
  return (
    <section ref={sectionRef} className="mt-12 scroll-mt-6">
      <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
      {subtitle && <p className="mt-1 text-sm text-stone-600 dark:text-stone-400">{subtitle}</p>}
      <div className="mt-4">{children}</div>
    </section>
  )
}

function Headline({ profile }) {
  const h = headline(profile)
  if (!h) {
    return <p className="mt-3 text-lg text-stone-600 dark:text-stone-400">No imported equipment from the deals SIPRI records is estimated to still be in service.</p>
  }
  const name = originInSentence(profile.origins, h.top)
  return (
    <p className="mt-3 text-lg leading-relaxed max-w-3xl text-stone-700 dark:text-stone-300">
      <strong className="text-stone-900 dark:text-stone-100">{pct(h.topShare)}</strong> of {profile.name}’s imported weapons still in
      service were designed in <strong className="text-stone-900 dark:text-stone-100">{name}</strong>
      {h.thenShare != null && Math.abs(h.thenShare - h.topShare) >= 0.03 && <>, {h.thenShare > h.topShare ? 'down' : 'up'} from {pct(h.thenShare)} in 2000</>}.
      {h.worst && h.worst.share >= 0.5 && h.worst.share > h.topShare + 0.05 && (
        <> Most exposed: <strong className="text-stone-900 dark:text-stone-100">{h.worst.cap.toLowerCase()}</strong> ({pct(h.worst.share)} from {name}).</>
      )}
    </p>
  )
}

export default function CountryPage() {
  const { iso3 } = useParams()
  const [profile, setProfile] = useState(null)
  const [error, setError] = useState(null)
  const [origin, setOrigin] = useState(null)
  const [filter, setFilter] = useState({ view: 'inService', origin: null, cap: null })
  const dealsRef = useRef(null)

  useEffect(() => {
    setProfile(null); setError(null)
    setFilter({ view: 'inService', origin: null, cap: null })
    loadCountry(iso3.toUpperCase())
      .then(p => {
        setProfile(p)
        const { shares } = sharesOf(holdingsAt(p, p.dataYear))
        setOrigin(Object.entries(shares).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null)
      })
      .catch(() => setError(`No profile for “${iso3}”.`))
  }, [iso3])

  if (error) return <p>{error} <Link className="underline" to="/">Back to countries</Link></p>
  if (!profile) return <p className="text-stone-500">Loading…</p>

  // Deal records are absent from public builds until SIPRI permits republishing them
  const hasDeals = Array.isArray(profile.deals)

  const showDeals = patch => {
    setFilter(f => ({ ...f, ...patch }))
    requestAnimationFrame(() => dealsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }

  return (
    <article>
      <Link to="/" className="text-sm text-stone-500 hover:text-stone-900 dark:hover:text-stone-100">← All countries</Link>
      <h1 className="mt-3 text-3xl sm:text-4xl font-semibold tracking-tight">{profile.name}</h1>
      <Headline profile={profile} />

      <Section
        title="What its imported arsenal is made of"
        subtitle={`Estimated share of imported equipment in service each year, by the country that designed it. ${profile.seriesStart}–${profile.dataYear}.`}
      >
        <HoldingsChart profile={profile} />
      </Section>

      {origin && (
        <Section
          title="If one supplier stopped"
          subtitle="Equipment depends on its designer for spare parts, upgrades and munitions. This is how much of each area that supplier props up."
        >
          <ExposurePanel
            profile={profile}
            origin={origin}
            onOriginChange={setOrigin}
            onSelectCapability={hasDeals ? cap => showDeals({ view: 'inService', origin, cap }) : null}
          />
        </Section>
      )}

      <Section title="What’s coming" subtitle="Deals that are ordered but not fully delivered, and where new orders have gone over time.">
        <OrdersPanel profile={profile} onShowBacklog={hasDeals ? () => showDeals({ view: 'open', origin: null, cap: null }) : null} />
      </Section>

      <Section title="The deals behind the numbers" sectionRef={dealsRef}>
        {hasDeals ? (
          <DealsTable profile={profile} filter={filter} setFilter={setFilter} />
        ) : (
          <p className="text-sm text-stone-600 dark:text-stone-400 max-w-3xl">
            These figures are built from {profile.quality.nDeals} deals in the SIPRI Arms Transfers Database. SIPRI’s terms
            don’t allow this site to republish the deal records themselves, so look them up directly in the{' '}
            <a className="underline" href="https://armstransfers.sipri.org/" target="_blank" rel="noreferrer">SIPRI Arms Transfers Database</a>{' '}
            (filter by recipient: {profile.name}).
          </p>
        )}
      </Section>

      <p className="mt-12 text-xs text-stone-500 max-w-3xl">
        Imported equipment only: weapons {profile.name} builds itself are not in SIPRI’s transfer data.
        {profile.quality.shareUncertain > 0 && <> SIPRI marks some figures as uncertain in {pct(profile.quality.shareUncertain)} of these deals.</>}
        {' '}<Link to="/method" className="underline">How the estimate works</Link>.
      </p>
    </article>
  )
}
