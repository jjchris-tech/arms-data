"""
Step 4: Supplier view — who depends on each design origin.

The country profiles answer "who does country X depend on?". This step turns
them around: for each design origin (Russia, the US, China, ...), which
militaries run on its equipment, in which capability areas, and are they still
buying from it?

"Still buying?" compares two shares for each dependent country:
  arsenal share — origin's share of its in-service equipment now
  order share   — origin's share of the equipment it ordered in the last ten years
                  (by design origin, so Soviet-designed tanks bought from Poland
                  count as Russian/Soviet: they still need Russian-pattern parts)
  status:
    staying      order share >= 80% of arsenal share
    diversifying order share 40-80% of arsenal share
    moving_away  order share  < 40% of arsenal share
    few_orders   under FEW_ORDERS TIV ordered in the window: too little to judge

Inputs:  dashboard/public/data/country/*.json (step 3)
Outputs: dashboard/public/data/suppliers.json, supplier/{ISO3}.json
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config
from pipeline.utils.capabilities import CAPABILITY_ORDER

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ORDER_WINDOW = 10          # years of orders that count as "recent"
FEW_ORDERS = 50            # TIV ordered in the window below which status is not judged
SMALL_ARSENAL = 100        # TIV; smaller arsenals are listed but not counted in headline numbers
MIN_DEPENDENT_SHARE = 0.10  # list a country as a dependent at this share or above...
MIN_DEPENDENT_TIV = 50      # ...or with at least this much of the origin's equipment
MIN_SUPPLIER_TIV = 50      # origins with less equipment abroad than this get no page
COMPARE_YEAR = 2010
WEIGHTY_AREA = 0.05        # a capability area must be this share of an arsenal to count as "most exposed"


def _r(x, nd=1):
    return None if x is None else round(float(x), nd)


def status(arsenal_share: float, order_share: float | None, orders_tiv: float) -> str:
    if orders_tiv < FEW_ORDERS or order_share is None:
        return "few_orders"
    ratio = order_share / arsenal_share if arsenal_share > 0 else 0
    if ratio >= 0.8:
        return "staying"
    if ratio >= 0.4:
        return "diversifying"
    return "moving_away"


def load_profiles() -> list[dict]:
    profiles = []
    for path in sorted((config.APP_DATA_DIR / "country").glob("*.json")):
        with open(path, encoding="utf-8") as f:
            profiles.append(json.load(f))
    return profiles


def country_view(p: dict, origin: str, recent_from: int) -> dict | None:
    """How country p depends on `origin` (None if it holds none of its equipment)."""
    years, by_origin = p["inService"]["years"], p["inService"]["byOrigin"]
    i = years.index(p["dataYear"])
    totals = [sum((s[k] or 0) for s in by_origin.values()) for k in range(len(years))]
    series = by_origin.get(origin)
    if not series or totals[i] <= 0 or not (series[i] or 0) > 0:
        return None
    tiv = series[i]
    share = tiv / totals[i]
    j = years.index(COMPARE_YEAR) if COMPARE_YEAR in years else None
    share_then = (series[j] or 0) / totals[j] if j is not None and totals[j] > 0 else None

    oyears, orders = p["orders"]["years"], p["orders"]["byOrigin"]
    recent = [k for k, y in enumerate(oyears) if y >= recent_from]
    orders_total = sum(sum((s[k] or 0) for k in recent) for s in orders.values())
    orders_origin = sum((orders.get(origin, [0] * len(oyears))[k] or 0) for k in recent)
    order_share = orders_origin / orders_total if orders_total > 0 else None

    backlog = p["backlog"]["byOrigin"] or {}
    backlog_total = p["backlog"]["total"] or 0

    arsenal = sum(e["total"] for e in p["exposure"])
    areas = [
        {"capability": e["capability"], "share": (e["byOrigin"].get(origin, 0)) / e["total"],
         "weight": e["total"] / arsenal if arsenal else 0, "tiv": e["byOrigin"].get(origin, 0)}
        for e in p["exposure"]
    ]
    weighty = [a for a in areas if a["weight"] >= WEIGHTY_AREA and a["tiv"] > 0]
    top_area = max(weighty, key=lambda a: a["share"]) if weighty else None

    return {
        "iso3": p["iso3"], "name": p["name"],
        "arsenalTiv": _r(totals[i]), "tiv": _r(tiv), "share": _r(share, 3),
        "shareThen": _r(share_then, 3) if share_then is not None else None,
        "ordersTiv": _r(orders_total), "orderShare": _r(order_share, 3) if order_share is not None else None,
        "backlogShare": _r(backlog.get(origin, 0) / backlog_total, 3) if backlog_total > 0 else None,
        "status": status(share, order_share, orders_total),
        "topArea": {"capability": top_area["capability"], "share": _r(top_area["share"], 3)} if top_area else None,
        "inherited": (p.get("inherited") or {}).get("status") == "added",
        "small": totals[i] < SMALL_ARSENAL,
        "_areas": areas,
        "_series": series, "_totals": totals,
    }


def build():
    profiles = load_profiles()
    data_year = profiles[0]["dataYear"]
    years = profiles[0]["inService"]["years"]
    recent_from = data_year - ORDER_WINDOW + 1
    origins = sorted({o for p in profiles for o in p["inService"]["byOrigin"]})
    names = {}
    for p in profiles:
        names.update(p["origins"])

    out_dir = config.APP_DATA_DIR / "supplier"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.json"):
        old.unlink()

    index = []
    for origin in origins:
        views = [v for p in profiles if p["iso3"] != origin and (v := country_view(p, origin, recent_from))]
        abroad = sum(v["tiv"] for v in views)
        if abroad < MIN_SUPPLIER_TIV:
            continue
        counted = [v for v in views if not v["small"]]

        # Equipment abroad and number of majority-dependent countries, over time
        abroad_series, majority_series = [], []
        for k in range(len(years)):
            abroad_series.append(_r(sum((v["_series"][k] or 0) for v in views)))
            majority_series.append(sum(
                1 for v in counted if v["_totals"][k] >= SMALL_ARSENAL and (v["_series"][k] or 0) / v["_totals"][k] >= 0.5))

        # Capability areas: where dependence on this origin concentrates
        areas = []
        for cap in CAPABILITY_ORDER:
            rows = [a for v in counted for a in v["_areas"] if a["capability"] == cap]
            tiv = sum(a["tiv"] for a in rows)
            if tiv <= 0:
                continue
            areas.append({
                "capability": cap, "tiv": _r(tiv),
                "nMajority": sum(1 for a in rows if a["share"] >= 0.5 and a["weight"] >= WEIGHTY_AREA),
                "nCountries": sum(1 for a in rows if a["tiv"] > 0),
            })

        dependents = [
            {k: val for k, val in v.items() if not k.startswith("_")}
            for v in sorted(views, key=lambda v: -v["share"])
            if v["share"] >= MIN_DEPENDENT_SHARE or v["tiv"] >= MIN_DEPENDENT_TIV
        ]
        n_majority = sum(1 for v in counted if v["share"] >= 0.5)
        n_quarter = sum(1 for v in counted if v["share"] >= 0.25)
        j = years.index(COMPARE_YEAR)
        supplier = {
            "iso3": origin, "name": names.get(origin, origin), "dataYear": data_year,
            "recentFrom": recent_from, "compareYear": COMPARE_YEAR, "smallArsenal": SMALL_ARSENAL,
            "abroadTiv": _r(abroad), "nMajority": n_majority, "nQuarter": n_quarter,
            "series": {"years": years, "abroadTiv": abroad_series, "nMajority": majority_series},
            "areas": areas, "dependents": dependents,
            "statusCounts": {s: sum(1 for d in dependents if d["status"] == s and not d["small"] and d["share"] >= 0.25)
                             for s in ("staying", "diversifying", "moving_away", "few_orders")},
        }
        with open(out_dir / f"{origin}.json", "w", encoding="utf-8") as f:
            json.dump(supplier, f, separators=(",", ":"), ensure_ascii=False)
        index.append({
            "iso3": origin, "name": supplier["name"], "abroadTiv": supplier["abroadTiv"],
            "abroadTivThen": abroad_series[j], "nMajority": n_majority, "nQuarter": n_quarter,
            "nCountries": len(views), "topDependents": [d["iso3"] for d in dependents[:5]],
        })

    index.sort(key=lambda s: -s["abroadTiv"])
    with open(config.APP_DATA_DIR / "suppliers.json", "w", encoding="utf-8") as f:
        json.dump({"dataYear": data_year, "compareYear": COMPARE_YEAR, "recentFrom": recent_from,
                   "suppliers": index}, f, separators=(",", ":"), ensure_ascii=False)
    return index


def main():
    logger.info("=== Step 4: Supplier view ===")
    index = build()
    logger.info("Wrote %d supplier profiles", len(index))
    for s in index[:8]:
        logger.info("  %-16s abroad %7.0f TIV  %3d countries  %2d majority-dependent  %2d >=25%%",
                    s["name"][:16], s["abroadTiv"], s["nCountries"], s["nMajority"], s["nQuarter"])


if __name__ == "__main__":
    main()
