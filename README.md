# Arms Dependency

For every country that imports major conventional weapons, an estimate of which countries designed the equipment
it still operates — and so who it relies on for spare parts, upgrades and munitions.

Built for analysts: every figure is traceable to the method, and (where licensing allows) to the individual deals
behind it.

## How it works

1. **Deals** — the [SIPRI Arms Transfers Database](https://www.sipri.org/databases/armstransfers) (~30,000 deals,
   1950–2025).
2. **Design origin, not seller** — resold and licence-built equipment is attributed to the country that designed it
   (Dutch F-16s sold to Jordan count as American; the Soviet Union and Russia are one origin, except Ukrainian design
   bureaux such as Antonov).
3. **In-service estimate** — each delivery stays in service for a typical life for its type (12 years for munitions
   to 35 for ships and armour; half for second-hand), since SIPRI does not record retirements.

4. **Independent check** — each estimate is compared with the CIA World Factbook's description of that military's
   equipment (final edition, 2025). Currently our largest design origin matches the Factbook's stated main source
   for about 80% of countries; the site lists every disagreement and the likely reason.

Full method and limitations are on the site's Method page. Key limits: imported equipment only (domestic
production is invisible), re-exports are not yet subtracted, and SIPRI flags about half of all deals as having
uncertain figures.

## Running it

```bash
pip install -r pipeline/requirements.txt
python pipeline/run_all.py            # add --refresh to re-download from SIPRI
cd dashboard && npm install && npm run dev
```

`run_all.py` ends with sanity checks (`pipeline/checks.py`) against independently known facts; a failing check
stops the deploy.

## Data and licensing

Information from the Stockholm International Peace Research Institute (SIPRI),
https://www.sipri.org/databases/armstransfers. SIPRI permits analysis and charts based on its data with
attribution, but republishing more than 10% of a dataset needs its permission. The public site therefore shows
estimates and aggregates only; deal-level records are withheld (`ARMS_INCLUDE_DEALS=0`) until permission is
granted. SIPRI data is not committed to this repository — the deploy workflow downloads it at build time.

Candidate additional sources are reviewed in [docs/data-sources.md](docs/data-sources.md).
