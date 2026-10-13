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
  step4_suppliers.py      supplier view: who depends on each design origin, 'still buying?' status -> suppliers.json, supplier/{ISO3}.json
  step5_validation.py     compares our top design origin with the CIA World Factbook's equipment text -> validation.json
  step6_downloads.py      analyst CSVs + manifest.json (column dictionary) -> dashboard/public/data/downloads/
                          (derived estimates only, never SIPRI deal records)
  checks.py               sanity checks against known facts; run_all.py fails loudly if one breaks
  build_factbook_reference.py  one-off: regenerates data/reference/factbook_equipment.csv (CC0, committed)
  utils/factbook.py       parses Factbook prose into main / mentioned origins
  build_legacy_reference.py  one-off: Wikipedia equipment lists -> data/reference/legacy_holdings.csv (CC BY-SA, needs lxml)
  utils/legacy.py         inherited Soviet/Yugoslav kit: match to SIPRI families, subtract SIPRI-recorded units, value x0.4
  utils/design_origin.py  who designed a system (not who sold it); USSR -> RUS; Antonov/Ivchenko -> UKR
  utils/capabilities.py   weapon_desc -> capability area + service life
dashboard/                React 19 + Vite + Tailwind v4 + Recharts, HashRouter, base path /arms-data/
  src/lib/profile.js      all share/aggregation maths for the UI lives here, not in components
data/raw/                 sipri-trade-register.csv (input), SIPRI milex xlsx (unused, kept for later)
data/reference/           openly licensed reference data, safe to commit (Factbook CC0, Wikipedia CC BY-SA)
docs/data-sources.md      researched candidate datasets for future features
```

## Commands

- Pipeline: `python pipeline/run_all.py` (~25 s). Deps: `pip install -r pipeline/requirements.txt`
- App: `cd dashboard && npm run dev` (port 5173) / `npm run build`. Preview config: `.claude/launch.json` -> `dashboard`
- Deploy: push to `main` on github.com/jjchris-tech/arms-data -> `.github/workflows/deploy.yml` re-downloads SIPRI,
  runs the pipeline + checks, builds, publishes to https://jjchris-tech.github.io/arms-data/ (also runs monthly).
  `gh` is at `C:\Program Files\GitHub CLI\gh.exe` (may not be on PATH in older shells).

## Licensing (SIPRI)

Republishing >10% of SIPRI data needs SIPRI's permission. Public builds set `ARMS_INCLUDE_DEALS=0` (no deal records);
local builds include them. Never commit `dashboard/public/data/` or `data/raw/` — the repo is public. Required
attribution: "Information from the Stockholm International Peace Research Institute (SIPRI), <URL>".

## Data rules that are easy to get wrong

- TIV (SIPRI trend-indicator value) measures capability, not money. Never present it as dollars.
- SIPRI codes the Soviet Union as `SUN`; always use `seller_successor_iso3` / `design_origin_iso3`, never raw `seller_iso3`.
- Order year leads delivery by years; use orders for "who is switching supplier", deliveries/in-service for "who depends on whom".
- ~half of deals carry SIPRI `?` uncertainty flags (kept as `*_uncertain` columns) — surface this, don't hide it.
- Imported equipment only: domestic production is invisible, so big producers look import-dependent. Always caveat.
- Re-exports: step 3 adds negative tranches (reexport_tranches) matching second-hand exports to the exporter's own
  imports of the same family, oldest first; skipped when the exporter designed the system (domestic production).
- After changing classification or origin logic, read the `report()` output of step 2 and run `checks.py`.
- Validation (step 4) is an out-of-sample check: don't tune model parameters (e.g. service lives) to raise the
  Factbook agreement score, or the published score stops meaning anything.
- Inherited stocks (successor states): Wikipedia counts launchers, SIPRI values long-range SAMs per battalion ->
  LAUNCHERS_PER_UNIT in utils/legacy.py. KGZ, TKM, MNE, HRV pages have no quantities, so they stay unadjusted.

## Working conventions

- The user prefers honest assessments over enthusiasm, and one feature done well over many done roughly.
- Audience is analysts: traceability, downloads and method transparency matter more than polish.
- Keep the UI minimal: countries, suppliers, method and data pages. New features must earn their place.
