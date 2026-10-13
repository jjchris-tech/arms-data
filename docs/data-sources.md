# Candidate data sources

Researched October 2026. For each source: what it is, why it matters for this project, access/licence, and
caveats. Ranked by how much it strengthens the **core question** (who does each military depend on?) before
anything else. "Verify" marks details I could not confirm directly and that need checking before building on them.

**Effort**: S = an afternoon, M = a few days, L = a project in itself.

---

## Tier 1 — Makes the core feature more correct

These fix known weaknesses in the current estimate: the unvalidated in-service model, design-origin attribution,
and re-exports not being subtracted.

### 1. CIA World Factbook — final archive (military equipment field)
- **What**: The Factbook (discontinued 4 Feb 2026) had a field *"Military equipment inventories and acquisitions"*
  per country — a sentence like "inventory is mostly Russian/Soviet-origin; recent acquisitions from France, Israel".
- **Why**: A free, public-domain, *independent* statement of each country's equipment origin. Ideal for validating
  our headline ("64% Russian/Soviet") across ~170 countries at once — parse the named origins and check our top
  origin agrees. Exactly the validation step 3 needs.
- **Access**: Final snapshot (23 Jan 2026) on [Mozilla Data Collective, CC0](https://datacollective.mozillafoundation.org/datasets/cmll4w0ln00nemn07axe7mj09);
  structured history 1990–2025 in [MilkMp/CIA-World-Factbooks-Archive](https://github.com/MilkMp/CIA-World-Factbooks-Archive-1990-2025);
  [field example](https://cia.gov/the-world-factbook/about/archives/2021/field/military-equipment-inventories-and-acquisitions).
- **Caveats**: Qualitative text, not counts. Field only exists in recent editions (verify first year). Frozen at 2025/26.
- **Effort**: S. **Priority: highest.**

### 2. Wikipedia equipment lists ("List of equipment of the … Army/Air Force/Navy")
- **What**: Per-country tables of equipment in service with type, origin and quantity.
- **Why**: The closest free substitute for IISS *Military Balance*. Lets us compare estimated in-service shares with
  reported fleet counts for well-covered countries (India, Egypt, Poland, Vietnam, Algeria…) and tune service lives.
- **Access**: [Index of lists by country](https://en.wikipedia.org/wiki/Lists_of_currently_active_military_equipment_by_country);
  pull via the MediaWiki API. CC BY-SA 4.0 (attribution + share-alike if we republish derived tables).
- **Caveats**: Table formats vary by page and language; quantities are often unsourced or stale. Use for
  validation of a sample, not as a primary source.
- **Effort**: M (a robust parser for many layouts). Start with 5–10 hand-picked countries.

### 3. Wikidata (weapon systems: country of origin)
- **What**: Structured items for weapon systems with *country of origin* (P495), manufacturer, and sometimes
  operators (P137). Queryable via SPARQL at query.wikidata.org.
- **Why**: Independent check on our design-origin rules (which currently infer origin from who sells a family new).
  A live test returned sensible origins (MiG-21 → Soviet Union, IAI Harop → Israel, MT-55A → Czechoslovakia).
- **Access**: Free, CC0, SPARQL endpoint.
- **Caveats**: Tested: **operator coverage is patchy and mixed with civilian items** — useful for origin, not for
  inventories. Matching SIPRI designations to Wikidata items needs fuzzy name matching.
- **Effort**: S–M.

### 4. Kiel Institute — Ukraine Support Tracker
- **What**: Government-by-government military aid to Ukraine since 2022, including in-kind weapons
  ("allocations" vs "commitments"), with a heavy-weapons subset.
- **Why**: Fixes our biggest known bias: Eastern European donors (Poland, Czechia, Slovakia, Bulgaria) gave away
  large stocks of Soviet-era kit that our model still counts as theirs. Also documents Ukraine's shift from Soviet
  to Western designs at a granularity SIPRI lacks.
- **Access**: Excel data set on the [tracker page](https://ifw-kiel.de/topics/war-against-ukraine/ukraine-support-tracker/);
  [dataset documentation](https://www.ifw-kiel.de/fileadmin/Dateiverwaltung/Subject_Dossiers_Topics/Ukraine/Ukraine_Support_Tracker/Dataset_Documentation.pdf).
  Free; cite Kiel Working Paper 2218. Verify the latest release date and licence.
- **Caveats**: Delivery detail only for some heavy weapons; values are upper-bound market prices, not units.
- **Effort**: M.

### 5. SIPRI Military Expenditure (already in data/raw) + NATO equipment-spending shares
- **What**: SIPRI milex (we have it: 1949–2024, constant USD, % GDP). NATO's annual *Defence Expenditure of NATO
  Countries* report splits spending into equipment / personnel / infrastructure.
- **Why**: Lets us estimate **how much of a country's equipment spending goes abroad** — imports (TIV) relative to
  equipment budgets. That addresses the "imports only" caveat: it flags countries where imports are a small slice
  of procurement (US, France, Korea) so the page can say so instead of overstating dependency.
- **Access**: SIPRI milex already downloaded. NATO report tables on nato.int (verify current URL/format).
- **Caveats**: TIV and dollars aren't directly comparable — use ratios and trends, not levels. NATO data is NATO only.
- **Effort**: S for milex, S–M for NATO.

---

## Tier 2 — New research layers on top of the core

### 6. UN General Assembly voting records
- **What**: Every recorded GA vote by every member state, 1946–present (≈912k country-votes), including the
  Ukraine emergency-session resolutions (ES-11/1 in 2022: 141–5–35, through ES-11/10 in Feb 2026).
- **Why**: Tests the most interesting political question this data can ask: **do countries that depend on Russian
  equipment vote with Russia?** Abstention on ES-11/1 vs Russian-design share is an obvious first chart.
- **Access**: Official CSV in the [UN Digital Library](https://research.un.org/en/docs/unvoting/undl) (non-commercial,
  attribution). Academic version with issue categories (CC BY 4.0) via [GESIS / Princeton DSS](https://dss.princeton.edu/catalog/resource8514).
  Classic [Voeten dataset](https://dataverse.harvard.edu/dataset.xhtml?persistentId=hdl:1902.1/12379) with ideal points.
- **Caveats**: Only recorded votes; most resolutions pass without a vote. Correlation ≠ leverage.
- **Effort**: S.

### 7. UCDP conflict data (v26.1)
- **What**: Armed-conflict datasets (state-based, non-state, one-sided violence) and the geo-referenced event
  dataset GED with **battle deaths**, 1989–2025.
- **Why**: Replaces the old 2023-vintage file we deleted. Enables "do import surges precede conflict?" (our quick
  test found ~1.8× higher onset rates, n=19 — needs proper work) and wartime resupply dependency.
- **Access**: [UCDP download centre](https://ucdp.uu.se/downloads/), free, **CC BY 4.0**, also an API.
- **Caveats**: Thresholds (25 battle deaths/year) miss low-level violence.
- **Effort**: S to load, L to do the conflict research properly.

### 8. Sanctions and embargoes
- **Global Sanctions Data Base R4** — 1,547 cases 1950–2023, typed (arms, military assistance, trade…). Free on
  request (GSDB@drexel.edu). [Site](https://globalsanctionsdatabase.com/).
- **SIPRI Arms Embargoes Database** — all multilateral arms embargoes since 1950 with dates and scope.
  [Site](https://sipri.org/databases/embargoes) — no bulk export found; may need scraping or a request.
- **EU Sanctions Map** — current EU measures (verify bulk access).
- **US CAATSA cases** — hand-code ~20 rows (Turkey sanctioned over S-400, India's waiver, Egypt's dropped Su-35).
- **Why**: Shows *why* countries switch supplier — pressure vs choice. Also replaces our old 23-row hand-coded file.
- **Effort**: S (GSDB) to M (SIPRI embargoes).

### 9. Supplier-side: SIPRI Arms Industry Database (Top 100)
- **What**: Arms revenues of the 100 largest arms companies, 2002–2024, with country.
- **Why**: Measures each supplier country's production capacity over time — e.g. whether Russia's industry can
  still support the fleets that depend on it. Also supports a future "buyer becomes builder" story (Korea, Turkey).
- **Access**: Excel on [sipri.org/databases/armsindustry](https://sipri.org/databases/armsindustry). Free.
- **Caveats**: Chinese firms only partly covered (some from 2015). Revenues are estimates.
- **Effort**: S.

### 10. US arms sales pipeline (forward-looking)
- **Congressional notifications** of proposed sales (FMS and large DCS): moved from DSCA to the **State Department
  in Feb 2026**; earlier years via the [Forum on the Arms Trade tracker](https://forumarmstrade.org/major-arms-sales-notifications-tracker.html)
  and archived DSCA pages. Public domain, but needs scraping.
- **DSCA Historical Sales Book** (FMS agreements and deliveries by country and year, $) and **State DDTC Section 655
  reports** (licensed commercial exports by country and category) — from prior knowledge; verify current location.
- **Security Assistance Monitor** — curated notifications/authorizations/deliveries, downloadable from
  [internationalpolicy.org](https://internationalpolicy.org/programs/sam/) ([data guide](https://internationalpolicy.org/data-guide/)).
- **Why**: Sees US deals *before* they appear in SIPRI orders, with dollar values. US is ~56% of the global backlog.
- **Caveats**: Notifications are proposals, not contracts; thresholds ($14m MDE / $50m other) hide small sales.
- **Effort**: M.

### 11. European export licences
- **What**: EU annual report on arms exports (licence values by destination and category, all member states) —
  official online database run by the EEAS; [CAAT's EU Export Data Browser](https://data.caat.org.uk/exports-eu/faq)
  makes it usable.
- **Why**: Money values for European suppliers (complements TIV), and early signal of European orders.
- **Caveats**: Licences ≠ deliveries; France counts licence values differently since 2014; several states report
  licence values only.
- **Effort**: M.

### 12. Alliances and regime type
- **ATOP v5.1** (alliance treaties 1815–2018) via [QoG Data Finder](https://datafinder.qog.gu.se/dataset/atop);
  **COW Formal Alliances v4.1**.
- **V-Dem v16** (March 2026, democracy indices, free) — [v-dem.net](https://www.v-dem.net/dsarchive.html).
- **Why**: Explanatory variables for "who stays with a supplier": allies and autocracies vs others.
- **Caveats**: ATOP stops in 2018. V-Dem licence terms are in the download bundle (verify before redistributing).
- **Effort**: S each.

---

## Tier 3 — Context, scaling, and filling SIPRI's gaps

| Source | What it adds | Access / licence | Notes |
|---|---|---|---|
| **CEPII BACI** (HS chapter 93) | Bilateral trade in **arms & ammunition in USD**, 1995–2023, harmonised from Comtrade | [Free, Etalab 2.0](https://www.cepii.fr/DATA_DOWNLOAD/baci/doc/baci_webpage.html) | Fills SIPRI's small-arms/ammunition gap. Customs data under-reports military goods. |
| **UN Comtrade API** | Same, more recent years | Free key: ~500 calls/day (verify) | BACI is easier for bulk. |
| **World Bank WDI** | GDP, population, armed forces personnel | Free API, CC BY 4.0 | Per-capita scaling. |
| **COW National Material Capabilities v7** | Military personnel 1816–2022 | Free; also via [Our World in Data](https://ourworldindata.org/grapher/military-personnel) | Long-run context. |
| **Oryx / WarSpotting** | Visually confirmed equipment losses in Ukraine by system | Oryx scrapes on GitHub (e.g. [scrape_oryx](https://github.com/KuleRucket/scrape_oryx)); [WarSpotting API](https://ukr.warspotting.net/api/docs) (Russian losses only; check reuse terms) | Shows attrition of Soviet-design fleets → strain on Russia's ability to support customers. |
| **Lowy Asia Power Index** | Military capability indicators for Asia | [power.lowyinstitute.org](https://power.lowyinstitute.org/data/military-capability/defence-spending/) | Export options unclear — verify. |
| **EU TED** (Directive 2009/81 notices) | European defence contract awards | Free open data (verify bulk coverage of defence notices) | Early signal of European rearmament orders. |
| **USAspending.gov** | US DoD contracts incl. FMS-funded work naming foreign customers | Free API, public domain | Messy text; good for specific programmes. |

---

## Looked at and not recommended (for now)

| Source | Why not |
|---|---|
| **IISS Military Balance** | The gold standard for inventories, but paid and not redistributable. Worth it only via library access for one-off validation. |
| **UN Register of Conventional Arms / ATT annual reports** | Voluntary, declining participation, exporter/importer reports often disagree. Fine as a cross-check, not a source. [UNROCA](https://disarmament.unoda.org/convarms/Register/). |
| **NISAT small arms database** | Stopped updating in 2017 (data to ~2015). [PRIO](https://www.prio.org/data/2). |
| **ACLED** | Excellent event data, but terms forbid passing raw data on to users — awkward for a public site. Use UCDP. |
| **OpenSanctions** | CC BY-NC (fine for non-commercial research) but built for entity screening, not country-level arms embargoes. |
| **Global Firepower** | Opaque methods; not citable. |

---

## Transformations worth doing with what we already have or could add cheaply

1. **Validation score** (Factbook + Wikipedia): % of countries where our top design origin matches the Factbook's
   stated main origin. Publish it on the Method page — it turns "estimate" into "estimate, checked against X".
2. **Import share of procurement** (SIPRI milex/NATO): ratio of imported TIV to equipment spending trend, to flag
   countries with big domestic industries instead of a blanket caveat.
3. **Re-export adjustment** (Kiel + SIPRI's own second-hand exports): subtract donated/resold kit from the giver.
4. **Dependency vs alignment** (UN votes): Russian-design share against ES-11 voting — the first research piece.
5. **Supplier capacity index** (SIPRI Top 100 + Oryx): can each supplier still support its installed base?
6. **Order-led early warning**: combine SIPRI orders with US notifications and EU licences to see supplier
   switches 2–5 years before deliveries show them.

## Suggested order

1. Factbook validation (S) → publish a validation score.
2. UN votes (S) → first research piece: "Do arms dependents vote with their supplier?"
3. Kiel re-export adjustment (M) → removes the biggest known bias for Eastern Europe.
4. UCDP v26.1 + sanctions (S–M) → groundwork for the conflict and pressure questions.
