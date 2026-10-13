"""
Step 7: Downloadable CSVs of this site's estimates, for analysts.

Writes dashboard/public/data/downloads/*.csv plus manifest.json, which
describes every file and column and drives the app's Data page.

These are the site's own derived estimates and aggregates (country x origin x
year/capability), not reproductions of SIPRI's deal records, so they can be
published with attribution. Deal-level records are never written here.

Files are UTF-8 with a byte-order mark so Excel opens names like "Türkiye"
correctly.
"""

import csv
import json
import logging
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

OUT_DIR = config.APP_DATA_DIR / "downloads"

ATTRIBUTION = (
    "Estimates by Arms Dependency (https://jjchris-tech.github.io/arms-data/) based on information from the "
    "Stockholm International Peace Research Institute (SIPRI), https://www.sipri.org/databases/armstransfers"
)

COMMON = {
    "iso3": "ISO 3166-1 alpha-3 code of the country holding the equipment (successor-state codes: Soviet Union -> RUS)",
    "country": "Country name as used by SIPRI",
    "design_origin_iso3": "Country that designed the equipment (Soviet Union -> RUS; Antonov/Ivchenko -> UKR; Yugoslavia -> SRB)",
    "design_origin": "Name of the design-origin country",
}

FILES = {
    "countries.csv": {
        "title": "Country summary",
        "description": "One row per country: size of the estimated in-service arsenal, main design origin, Russian share then and now, backlog, adjustments and independent-check result.",
        "columns": {
            "iso3": COMMON["iso3"], "country": COMMON["country"],
            "tiv_in_service": "Estimated equipment in service in the data year (SIPRI TIV, millions; imported + inherited, minus re-exported)",
            "top_origin_iso3": "Largest design origin", "top_origin_share": "Its share of tiv_in_service (0-1)",
            "concentration_hhi": "Herfindahl index of design-origin shares (1 = a single origin)",
            "russia_share_2010": "Russian/Soviet-designed share in 2010", "russia_share_now": "Russian/Soviet-designed share in the data year",
            "backlog_tiv": "Ordered but undelivered equipment in open deals (TIV)",
            "inherited_tiv": "Equipment inherited at independence added to tiv_in_service (TIV); blank if not applicable",
            "inherited_status": "added / no_quantities (inherited but not sized) / blank",
            "reexported_tiv": "Imported equipment since passed on second-hand, deducted from tiv_in_service (TIV)",
            "factbook_verdict": "Comparison with the CIA World Factbook: agree / partial / disagree / not_comparable",
        },
    },
    "in_service_by_origin.csv": {
        "title": "In-service estimate by design origin and year",
        "description": "Estimated equipment in service each year, by country and design origin. The main time series behind each country chart.",
        "columns": {
            "iso3": COMMON["iso3"], "country": COMMON["country"], "year": "Year",
            "design_origin_iso3": COMMON["design_origin_iso3"], "design_origin": COMMON["design_origin"],
            "tiv_in_service": "Estimated equipment in service (SIPRI TIV, millions)",
            "share": "Share of the country's estimated in-service equipment that year (0-1)",
        },
    },
    "exposure_by_capability.csv": {
        "title": "Exposure by capability area",
        "description": "For the data year: in-service equipment by capability area and design origin — how much of each area depends on each supplier.",
        "columns": {
            "iso3": COMMON["iso3"], "country": COMMON["country"], "year": "Data year",
            "capability": "Capability area (Combat aircraft, Air defence, Naval, Armour, ...)",
            "design_origin_iso3": COMMON["design_origin_iso3"], "design_origin": COMMON["design_origin"],
            "tiv_in_service": "Estimated equipment in service in this area from this origin (TIV)",
            "share_of_capability": "Share of this capability area (0-1)",
            "capability_share_of_arsenal": "This capability area's share of the whole estimated arsenal (0-1)",
        },
    },
    "supplier_dependents.csv": {
        "title": "Who depends on each supplier",
        "description": "For each design origin, every country that holds its equipment: share of the country's arsenal, change since 2010, share of recent orders and the 'still buying?' status.",
        "columns": {
            "supplier_iso3": "Design origin (supplier)", "supplier": "Name of the design origin",
            "iso3": COMMON["iso3"], "country": COMMON["country"],
            "tiv_in_service": "Equipment of this origin in the country's estimated arsenal in the data year (TIV)",
            "share_of_arsenal": "Share of the country's estimated arsenal (0-1)", "share_2010": "Same share in 2010",
            "recent_orders_tiv": "Everything the country ordered in the last ten years (TIV)",
            "recent_order_share": "Share of those orders for equipment of this origin (0-1)",
            "status": "staying / diversifying / moving_away / few_orders (see Method page)",
            "most_exposed_area": "Capability area (at least 5% of the arsenal) most dependent on this origin",
            "most_exposed_area_share": "This origin's share of that area (0-1)",
            "small_arsenal": "Arsenal under 100 TIV: shares are volatile; excluded from headline counts",
        },
    },
    "orders_by_origin.csv": {
        "title": "New orders by design origin and order year",
        "description": "Value of new orders placed each year, by design origin. Orders lead deliveries by years, so supplier switches show here first.",
        "columns": {
            "iso3": COMMON["iso3"], "country": COMMON["country"], "order_year": "Year the order was placed",
            "design_origin_iso3": COMMON["design_origin_iso3"], "design_origin": COMMON["design_origin"],
            "tiv_ordered": "SIPRI TIV for the total order (millions)",
        },
    },
    "backlog_by_origin.csv": {
        "title": "Open orders (backlog) by design origin",
        "description": "Ordered but not yet delivered equipment in deals active in the last five years of data.",
        "columns": {
            "iso3": COMMON["iso3"], "country": COMMON["country"],
            "design_origin_iso3": COMMON["design_origin_iso3"], "design_origin": COMMON["design_origin"],
            "tiv_outstanding": "Undelivered units x SIPRI unit TIV (millions)",
        },
    },
    "inherited_equipment.csv": {
        "title": "Equipment inherited at independence",
        "description": "Soviet/Yugoslav-origin systems still in service in successor states, as added to the estimate. From Wikipedia equipment lists (mostly citing IISS Military Balance).",
        "licence": "CC BY-SA 4.0 (derived from Wikipedia); share under the same licence and attribute Wikipedia contributors",
        "columns": {
            "iso3": COMMON["iso3"], "country": COMMON["country"], "system": "System as named on the source page",
            "design_origin_iso3": COMMON["design_origin_iso3"], "capability": "Capability area",
            "listed_quantity": "Quantity in service per the source page",
            "launchers_per_unit": "Launchers per SIPRI unit (long-range air defence is valued per battalion); 1 otherwise",
            "units_already_in_sipri": "Units SIPRI already counts in service for this country and system (subtracted)",
            "units_added": "Units added to the estimate", "unit_tiv_new": "SIPRI TIV of one new unit",
            "tiv_added": "units_added x unit_tiv_new x 0.4 (second-hand valuation)",
            "source_page": "Wikipedia page title", "source_revid": "Wikipedia revision id used",
        },
    },
    "un_votes_research.csv": {
        "title": "Research: UN votes vs Russian-designed equipment",
        "description": "Country-level data behind the research piece: Russian/US-designed shares in 2021, votes on the 2022-23 Ukraine resolutions, alignment score and controls.",
        "licence": "Vote lists derived from Wikipedia (CC BY-SA 4.0); democracy index from V-Dem via Our World in Data (CC BY 4.0); ideal points CC0",
        "columns": {
            "iso3": COMMON["iso3"], "country": COMMON["country"], "region": "Region (Our World in Data)",
            "rus_share_2021": "Russian/Soviet-designed share of the estimated arsenal in 2021",
            "usa_share_2021": "US-designed share of the estimated arsenal in 2021",
            "votes_yes": "Votes for the resolutions (against Russia's position)", "votes_abstain": "Abstentions",
            "votes_no": "Votes against the resolutions (with Russia)", "votes_absent": "Absent / not voting",
            "alignment": "Mean of No=1, Abstain=0.5, Yes=0 over votes cast (0 = always against Russia)",
            "ideal_point_2023": "Voeten et al. UN ideal point, 2023 (higher = closer to the US-led bloc)",
            "electoral_democracy_2021": "V-Dem electoral democracy index, 2021 (0-1)",
            "former_soviet": "Former Soviet republic", "russia_supplier_status": "Status on the Russia supplier page",
            "in_main_sample": "In the main analysis (arsenal >= 100 TIV in 2021; Russia and Ukraine excluded)",
        },
    },
    "factbook_validation.csv": {
        "title": "Independent check against the CIA World Factbook",
        "description": "Our largest design origins compared with the Factbook's description of each military's equipment (final edition, 2025).",
        "licence": "Factbook text is public domain",
        "columns": {
            "iso3": COMMON["iso3"], "country": COMMON["country"],
            "test": "dominant (Factbook names a main source) or mixed (only lists suppliers)",
            "verdict": "agree / partial / disagree / not_comparable",
            "factbook_main_origins": "Origins the Factbook names as main source (WESTERN/EUROPEAN = generic blocs)",
            "factbook_mentioned_origins": "All origins the Factbook names",
            "factbook_notes_domestic": "Factbook notes significant domestic production",
            "our_top_origin": "Our largest design origin", "our_top_share": "Its share",
            "our_second_origin": "Our second-largest design origin", "our_second_share": "Its share",
            "factbook_text": "The Factbook's text",
        },
    },
}


def sipri_release() -> str | None:
    """'Data generated: ...' line from the downloaded SIPRI register."""
    try:
        with open(config.TRANSFERS_CSV, encoding="utf-8") as f:
            for _, line in zip(range(15), f):
                if line.startswith("Data generated:"):
                    return line.split(":", 1)[1].strip()
    except FileNotFoundError:
        pass
    return None


def write(name: str, rows: list[dict]):
    cols = list(FILES[name]["columns"])
    with open(OUT_DIR / name, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    FILES[name]["rows"] = len(rows)
    FILES[name]["bytes"] = (OUT_DIR / name).stat().st_size


def build():
    with open(config.APP_DATA_DIR / "countries.json", encoding="utf-8") as f:
        index = json.load(f)
    with open(config.APP_DATA_DIR / "validation.json", encoding="utf-8") as f:
        validation = json.load(f)["countries"]
    names, origin_names, data_year = {c["iso3"]: c["name"] for c in index["countries"]}, index["origins"], index["dataYear"]
    oname = lambda o: origin_names.get(o, o)

    summary, series, exposure, orders, backlog = [], [], [], [], []
    for c in index["countries"]:
        iso3 = c["iso3"]
        with open(config.APP_DATA_DIR / "country" / f"{iso3}.json", encoding="utf-8") as f:
            p = json.load(f)
        base = {"iso3": iso3, "country": p["name"]}
        inh, rex = p.get("inherited") or {}, p.get("reexported") or {}
        summary.append({
            **base, "tiv_in_service": c["inService"], "top_origin_iso3": c["topOrigin"], "top_origin_share": c["topShare"],
            "concentration_hhi": c["concentration"], "russia_share_2010": c["russiaShareThen"], "russia_share_now": c["russiaShare"],
            "backlog_tiv": c["backlog"], "inherited_tiv": inh.get("total"), "inherited_status": inh.get("status"),
            "reexported_tiv": rex.get("total"), "factbook_verdict": validation.get(iso3, {}).get("verdict"),
        })

        years, by_origin = p["inService"]["years"], p["inService"]["byOrigin"]
        for i, y in enumerate(years):
            total = sum(s[i] or 0 for s in by_origin.values())
            for o, s in by_origin.items():
                if (s[i] or 0) > 0:
                    series.append({**base, "year": y, "design_origin_iso3": o, "design_origin": oname(o),
                                   "tiv_in_service": s[i], "share": round(s[i] / total, 4)})

        # Shares from the published (rounded) values, so each file is internally consistent
        cap_totals = {e["capability"]: sum(e["byOrigin"].values()) for e in p["exposure"]}
        arsenal = sum(cap_totals.values())
        for e in p["exposure"]:
            for o, v in e["byOrigin"].items():
                exposure.append({**base, "year": data_year, "capability": e["capability"], "design_origin_iso3": o,
                                 "design_origin": oname(o), "tiv_in_service": v,
                                 "share_of_capability": round(v / cap_totals[e["capability"]], 4),
                                 "capability_share_of_arsenal": round(cap_totals[e["capability"]] / arsenal, 4) if arsenal else None})

        for o, s in p["orders"]["byOrigin"].items():
            for y, v in zip(p["orders"]["years"], s):
                if (v or 0) > 0:
                    orders.append({**base, "order_year": y, "design_origin_iso3": o, "design_origin": oname(o), "tiv_ordered": v})

        for o, v in (p["backlog"]["byOrigin"] or {}).items():
            backlog.append({**base, "design_origin_iso3": o, "design_origin": oname(o), "tiv_outstanding": v})

    inherited = []
    for iso3 in sorted(names):
        with open(config.APP_DATA_DIR / "country" / f"{iso3}.json", encoding="utf-8") as f:
            inh = json.load(f).get("inherited") or {}
        if inh.get("status") != "added":
            continue
        revid = {p["title"]: p["revid"] for p in inh["pages"]}
        for r in inh["rows"]:
            page = r["page"]
            inherited.append({
                "iso3": iso3, "country": names[iso3], "system": r["system"], "design_origin_iso3": r["origin"],
                "capability": r["cap"], "listed_quantity": r["quantity"], "launchers_per_unit": r["launchersPerUnit"],
                "units_already_in_sipri": r["recordedUnits"], "units_added": r["countedUnits"], "unit_tiv_new": r["unitTiv"],
                "tiv_added": r["tiv"], "source_page": page, "source_revid": revid.get(page),
            })

    dependents = []
    for path in sorted((config.APP_DATA_DIR / "supplier").glob("*.json")):
        with open(path, encoding="utf-8") as f:
            sp = json.load(f)
        for d in sp["dependents"]:
            dependents.append({
                "supplier_iso3": sp["iso3"], "supplier": sp["name"], "iso3": d["iso3"], "country": d["name"],
                "tiv_in_service": d["tiv"], "share_of_arsenal": d["share"], "share_2010": d["shareThen"],
                "recent_orders_tiv": d["ordersTiv"], "recent_order_share": d["orderShare"], "status": d["status"],
                "most_exposed_area": (d["topArea"] or {}).get("capability"),
                "most_exposed_area_share": (d["topArea"] or {}).get("share"), "small_arsenal": d["small"],
            })

    research = []
    with open(config.APP_DATA_DIR / "research" / "un_votes.json", encoding="utf-8") as f:
        for c in json.load(f)["countries"]:
            research.append({
                "iso3": c["iso3"], "country": c["name"], "region": c["region"], "rus_share_2021": c["rusShare"],
                "usa_share_2021": c["usaShare"], "votes_yes": c["votes"]["yes"], "votes_abstain": c["votes"]["abstain"],
                "votes_no": c["votes"]["no"], "votes_absent": c["votes"]["absent"], "alignment": c["alignment"],
                "ideal_point_2023": c["idealPoint"], "electoral_democracy_2021": c["democracy"], "former_soviet": c["postSoviet"],
                "russia_supplier_status": c["russiaStatus"], "in_main_sample": c["inSample"],
            })

    checks = []
    for iso3, v in sorted(validation.items()):
        ours = v["ours"] + [{}, {}]
        checks.append({
            "iso3": iso3, "country": names.get(iso3, iso3), "test": v["test"], "verdict": v["verdict"],
            "factbook_main_origins": ";".join(v["factbookPrimary"]), "factbook_mentioned_origins": ";".join(v["factbookMentioned"]),
            "factbook_notes_domestic": v["factbookDomestic"], "our_top_origin": ours[0].get("origin"), "our_top_share": ours[0].get("share"),
            "our_second_origin": ours[1].get("origin"), "our_second_share": ours[1].get("share"), "factbook_text": v["factbookText"],
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write("countries.csv", summary)
    write("in_service_by_origin.csv", series)
    write("exposure_by_capability.csv", exposure)
    write("supplier_dependents.csv", dependents)
    write("orders_by_origin.csv", orders)
    write("backlog_by_origin.csv", backlog)
    write("inherited_equipment.csv", inherited)
    write("factbook_validation.csv", checks)
    write("un_votes_research.csv", research)

    manifest = {
        "generated": date.today().isoformat(),
        "sipriRelease": sipri_release(),
        "dataYear": data_year,
        "attribution": ATTRIBUTION,
        "units": "SIPRI trend-indicator values (TIV), millions. TIV measures military capability, not money.",
        "files": [{"file": name, **meta} for name, meta in FILES.items()],
    }
    with open(OUT_DIR / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    return manifest


def main():
    logger.info("=== Step 7: Downloads ===")
    manifest = build()
    for f in manifest["files"]:
        logger.info("  %-28s %7d rows  %6.0f KB", f["file"], f["rows"], f["bytes"] / 1024)


if __name__ == "__main__":
    main()
