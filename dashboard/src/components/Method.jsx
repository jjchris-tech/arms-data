import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import Validation from './Validation'

const LIVES = [
  ['Naval, armour, artillery', 35],
  ['Combat aircraft, support aircraft, helicopters', 30],
  ['Air defence', 25],
  ['Sensors & components (radars, engines, turrets)', 20],
  ['Missiles & munitions', 12],
]

function H({ children, id }) {
  return <h2 id={id} className="mt-10 text-lg font-semibold tracking-tight scroll-mt-6">{children}</h2>
}

export default function Method() {
  // HashRouter puts the route in the URL hash, so "#/method#validation" needs a manual scroll
  const { hash } = useLocation()
  useEffect(() => {
    if (!hash) return
    const t = setTimeout(() => document.getElementById(hash.slice(1))?.scrollIntoView(), 300)
    return () => clearTimeout(t)
  }, [hash])

  return (
    <article className="max-w-3xl leading-relaxed text-stone-700 dark:text-stone-300">
      <h1 className="text-3xl font-semibold tracking-tight text-stone-900 dark:text-stone-100">How this works</h1>
      <p className="mt-4">
        A military that buys its weapons abroad keeps depending on the country that designed them long after the sale:
        for spare parts, maintenance, upgrades and munitions. This site estimates that dependency for every country that
        imports major conventional weapons.
      </p>

      <H>Source</H>
      <p className="mt-3">
        The <a className="underline" href="https://www.sipri.org/databases/armstransfers" target="_blank" rel="noreferrer">SIPRI Arms Transfers Database</a>:
        about 29,500 deals for major conventional weapons since 1950, each with the system, the order year, the
        delivery years and the number of units.
      </p>
      <p className="mt-3">
        Volumes are in SIPRI <em>trend-indicator values</em> (TIV). TIV measures military capability, not money: it values
        a weapon by what it can do, so a fighter outweighs a truck regardless of price. Use it to compare volumes, not costs.
      </p>

      <H>Design origin, not seller</H>
      <p className="mt-3">
        SIPRI records who sold each weapon. Dependency follows who <em>designed</em> it. The two differ for second-hand
        resales (Dutch F-16s sold to Jordan are still American aircraft) and for Soviet-era designs sold by Ukraine, Belarus or
        Central European states. For each weapon family, the design origin is the country that most often sells it new.
        The Soviet Union and Russia count as one origin, except for designs from bureaux based in Ukraine (Antonov aircraft,
        Ivchenko engines), which count as Ukrainian. Every deal shows which rule assigned its origin.
      </p>

      <H>Estimating what is still in service</H>
      <p className="mt-3">
        SIPRI does not record retirements, so each delivery is assumed to stay in service for a typical working life for
        its type, then retire. Second-hand equipment is assumed to have half that life left.
      </p>
      <table className="mt-4 text-sm">
        <tbody>
          {LIVES.map(([label, years]) => (
            <tr key={label} className="border-b border-stone-200 dark:border-stone-800">
              <td className="py-1.5 pr-6">{label}</td>
              <td className="py-1.5 tabular text-right">{years} years</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3">
        This is a deliberately simple model. Real fleets are retired early, upgraded or kept far longer than average. The
        shares are most reliable for large arsenals and over several years; for small ones, a single delivery can swing them.
      </p>

      <H id="reexports">Equipment passed on to others</H>
      <p className="mt-3">
        When a country resells or donates second-hand equipment, it no longer has it. SIPRI records these transfers, so
        each one is matched against the exporter’s own earlier imports of the same weapon family that are still in service,
        oldest first, and removed from the export year onward. This matters most for countries that gave Soviet-era
        equipment to Ukraine after 2022: Slovakia, for example, no longer shows Russian-designed kit after passing on its
        MiG-29s and S-300s. Only systems the exporter did not design are adjusted, and inherited equipment is never
        adjusted because it is already a current count.
      </p>

      <H>What is on order</H>
      <p className="mt-3">
        A deal counts as on order when fewer units have been delivered than ordered and it has seen an order or delivery in
        the last five years of data. Older incomplete deals are usually cancelled or unrecorded, so they are left out.
      </p>

      <H id="inherited">Equipment inherited at independence</H>
      <p className="mt-3">
        When the USSR and Yugoslavia broke up, their successor states took over the equipment on their territory. No
        transfer was ever recorded, so SIPRI — and an estimate built only on SIPRI — cannot see it, and the Russian/Soviet
        share for these countries would be badly understated.
      </p>
      <p className="mt-3">
        For 16 successor states we read Wikipedia’s equipment lists (CC BY-SA 4.0, mostly citing IISS <em>Military
        Balance</em>) and keep Soviet- and Yugoslav-origin systems listed as in service today. Each is matched to the same
        system in SIPRI’s data, which gives its capability area and unit value; it is valued as second-hand (×0.4, SIPRI’s own
        convention). Long-range air-defence systems are listed per launcher but valued by SIPRI per battalion, so launchers
        are converted (e.g. 12 per S-300 battalion). Anything SIPRI already counts as in service for that country is
        subtracted, so nothing is counted twice. Items SIPRI does not track (trucks, small arms, light mortars) drop out.
      </p>
      <p className="mt-3">
        Quantities exist for 12 of the 16; Kyrgyzstan, Turkmenistan, Montenegro and Croatia list systems without counts and
        are not adjusted. Today’s counts are applied back to 1992, so earlier years are approximate — especially for Ukraine,
        whose Soviet stocks have been heavily used up since 2022. Every country page lists exactly what was added and links
        the page revision it came from.
      </p>

      <H id="validation">How well it matches an independent source</H>
      <Validation />

      <H>Limits to keep in mind</H>
      <ul className="mt-3 list-disc pl-5 space-y-2">
        <li><strong>Imported equipment only.</strong> Weapons a country builds itself are not covered, so large producers
          (the US, Russia, China, France, India in part) look far more import-dependent here than they are.</li>
        <li><strong>Major conventional weapons only.</strong> SIPRI excludes small arms, light weapons and most ammunition.</li>
        <li><strong>Inherited equipment is approximate.</strong> It is added from Wikipedia counts for 12 successor states
          (see above); four have no counts and remain understated.</li>
        <li><strong>Re-exports of a country’s own designs are not adjusted.</strong> A designer reselling its own system
          (Germany’s Leopard 2s) was most likely exporting domestic production, which this import-based model cannot see.</li>
        <li><strong>Uncertain figures.</strong> SIPRI flags roughly half of all deals as having an uncertain order year or unit count.</li>
        <li><strong>Licensed production</strong> is attributed to the licensing country, which matches how parts dependency usually works.</li>
      </ul>
    </article>
  )
}
