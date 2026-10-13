# Arms Dependency

A research site answering one question well: **for any country, who does its military depend on for imported weapons?**
"Depend on" means the country that *designed* the equipment still in service, since that is who supplies parts,
upgrades and munitions. Features are added on top of this core only once it is solid.

## Layout

```
pipeline/                 Python data pipeline (run from project root)
  step1_acquire.py        downloads SIPRI trade register -> data/raw/  (--refresh to re-download)
  step2_deals.py          one row per deal + design origin, flags, backlog -> data/interim/deals.parquet
  step3_dependency.py     in-service model -> dashboard/public/data/countries.json + country/{ISO3}.json
  checks.py               sanity checks against known facts; run_all.py fails loudly if one breaks
  utils/design_origin.py  who designed a system (not who sold it); USSR -> RUS; Antonov/Ivchenko -> UKR
  utils/capabilities.py   weapon_desc -> capability area + service life
dashboard/                React 19 + Vite + Tailwind v4 + Recharts, HashRouter, base path /arms-data/
  src/lib/profile.js      all share/aggregation maths for the UI lives here, not in components
data/raw/                 sipri-trade-register.csv (input), SIPRI milex xlsx (unused, kept for later)
docs/data-sources.md      researched candidate datasets for future features
```

## Commands

- Pipeline: `python pipeline/run_all.py` (~25 s). Deps: `pip install -r pipeline/requirements.txt`
- App: `cd dashboard && npm run dev` (port 5173) / `npm run build`. Preview config: `.claude/launch.json` -> `dashboard`

## Data rules that are easy to get wrong

- TIV (SIPRI trend-indicator value) measures capability, not money. Never present it as dollars.
- SIPRI codes the Soviet Union as `SUN`; always use `seller_successor_iso3` / `design_origin_iso3`, never raw `seller_iso3`.
- Order year leads delivery by years; use orders for "who is switching supplier", deliveries/in-service for "who depends on whom".
- ~half of deals carry SIPRI `?` uncertainty flags (kept as `*_uncertain` columns) — surface this, don't hide it.
- Imported equipment only: domestic production is invisible, so big producers look import-dependent. Always caveat.
- Re-exports are not subtracted from the exporter's in-service estimate (known limitation).
- After changing classification or origin logic, read the `report()` output of step 2 and run `checks.py`.

## Working conventions

- The user prefers honest assessments over enthusiasm, and one feature done well over many done roughly.
- Keep the UI minimal: list page, country page, method page. New features must earn their place.
