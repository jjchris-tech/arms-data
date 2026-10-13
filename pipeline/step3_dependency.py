"""
Step 3: Country dependency profiles.

For every state recipient, estimates which countries designed the imported
weapons it still operates, and how exposed each capability area would be if
one design origin stopped supplying parts, upgrades and munitions.

In-service model (deliberately simple and explainable):
  - Each deal's delivered TIV is spread evenly over its delivery years.
  - A delivery counts as in service for the typical service life of its
    capability area (see utils/capabilities.py), halved for second-hand kit.
  - In-service TIV at year Y = sum of deliveries still within their life at Y.

Measures imported equipment only: domestic production is not in SIPRI's
transfer data, so major producers (US, Russia, China, France...) look far
more import-dependent here than they are.

Inputs:  data/interim/deals.parquet (step 2)
Outputs: dashboard/public/data/countries.json        (index for the list page)
         dashboard/public/data/country/{ISO3}.json   (one profile per country)
"""

import json
import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config
from pipeline.step2_deals import DEALS_PARQUET
from pipeline.utils.capabilities import CAPABILITY_ORDER, SERVICE_LIFE
from pipeline.utils.legacy import COVERED, INDEPENDENCE_YEAR, legacy_holdings

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SERIES_START = 1990
APP_DATA_DIR = config.APP_DATA_DIR
ORIGIN_LABELS = {"RUS": "Russia / USSR"}
COMPARE_YEAR = 2010   # baseline for "change since" figures in the index

# Deal-level records reproduce SIPRI data directly. Included by default for local
# use; the public deploy sets ARMS_INCLUDE_DEALS=0 until SIPRI grants permission.
INCLUDE_DEALS = os.environ.get("ARMS_INCLUDE_DEALS", "1") != "0"


def _r(x, nd=1):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), nd)


def explode_deliveries(deals: pd.DataFrame) -> pd.DataFrame:
    """One row per (deal, delivery year) with that year's TIV tranche."""
    d = deals[deals["delivery_years"].str.len() > 0].copy()
    d["year"] = d["delivery_years"].str.split(";")
    d = d.explode("year")
    d["year"] = d["year"].astype(int)
    d["tiv"] = d["tiv_delivered"].fillna(0) / d["n_delivery_years"]
    return d[["deal_id", "buyer_successor_iso3", "design_origin_iso3", "capability", "life", "year", "tiv"]]


def reexport_tranches(deals: pd.DataFrame, tranches: pd.DataFrame) -> pd.DataFrame:
    """
    Negative tranches for equipment a country later passed on second-hand.

    Each second-hand export is matched against the exporter's own imports of the
    same weapon family that are still in service at the time, oldest first (old
    kit is what usually gets passed on), and removed from the export year until
    that import would have retired anyway. Only systems the exporter did not
    design are adjusted: a designer re-exporting its own system was most likely
    exporting domestic production, which is not in this import-based model.
    Inherited equipment is never adjusted — it is a current count already.
    """
    exports = deals[
        deals["is_second_hand"] & deals["seller_successor_iso3"].notna()
        & (deals["design_origin_iso3"] != deals["seller_successor_iso3"])
        & (deals["num_delivered"].fillna(0) > 0) & (deals["n_delivery_years"] > 0)
        & deals["design_family"].notna()
    ]
    if exports.empty:
        return tranches.iloc[0:0].assign(recipient=None)

    meta = deals.set_index("deal_id")[["design_family", "num_delivered", "n_delivery_years"]]
    imports = tranches.join(meta, on="deal_id")
    # Exploded tranches share index labels; make them unique for per-row updates
    imports = imports[imports["num_delivered"].fillna(0) > 0].reset_index(drop=True)
    imports["units"] = imports["num_delivered"] / imports["n_delivery_years"]
    imports["per_unit"] = imports["tiv"] / imports["units"]
    imports["remaining"] = imports["units"]
    pools = {k: g.sort_values("year") for k, g in imports.groupby(["buyer_successor_iso3", "design_family"])}

    out = []
    for e in exports.sort_values("first_delivery").itertuples():
        pool = pools.get((e.seller_successor_iso3, e.design_family))
        if pool is None:
            continue
        per_year = e.num_delivered / e.n_delivery_years
        for y in (int(v) for v in e.delivery_years.split(";")):
            need = per_year
            alive = pool[(pool["year"] <= y) & (y < pool["year"] + pool["life"]) & (pool["remaining"] > 0)]
            for idx, t in alive.iterrows():
                if need <= 0:
                    break
                take = min(need, pool.at[idx, "remaining"])
                pool.at[idx, "remaining"] -= take
                need -= take
                out.append({
                    "deal_id": t["deal_id"], "buyer_successor_iso3": e.seller_successor_iso3,
                    "design_origin_iso3": t["design_origin_iso3"], "capability": t["capability"],
                    "year": y, "life": t["year"] + t["life"] - y, "tiv": -take * t["per_unit"],
                    "recipient": e.buyer,
                })
    return pd.DataFrame(out)


def in_service_series(tranches: pd.DataFrame, years: range) -> pd.DataFrame:
    """In-service TIV by (year, origin, capability) for each year in `years`."""
    out = []
    for y in years:
        live = tranches[(tranches["year"] <= y) & (y < tranches["year"] + tranches["life"])]
        g = live.groupby(["design_origin_iso3", "capability"])["tiv"].sum().reset_index()
        g["at_year"] = y
        out.append(g)
    return pd.concat(out, ignore_index=True)


def deal_record(r) -> dict:
    """Compact deal row for the frontend table."""
    return {
        "id": int(r.deal_id),
        "seller": r.seller,
        "sellerCode": r.seller_successor_iso3,
        "origin": r.design_origin_iso3,
        "originMethod": r.origin_method,
        "designation": r.designation,
        "desc": r.weapon_desc,
        "cap": r.capability,
        "ordered": None if pd.isna(r.num_ordered) else int(r.num_ordered),
        "delivered": None if pd.isna(r.num_delivered) else int(r.num_delivered),
        "orderYear": None if pd.isna(r.order_year) else int(r.order_year),
        "deliveryYears": r.delivery_years or None,
        "tiv": _r(r.tiv_delivered),
        "tivInService": _r(r.tiv_in_service),
        "tivOutstanding": _r(r.tiv_outstanding),
        "state": r.deal_state,
        "secondHand": bool(r.is_second_hand),
        "licensed": bool(r.is_licensed),
        "uncertain": bool(r.order_year_uncertain or r.num_ordered_uncertain or r.num_delivered_uncertain),
        "plannedDelivery": None if pd.isna(r.planned_delivery_start) else
            f"{int(r.planned_delivery_start)}" + (
                f"–{int(r.planned_delivery_end)}" if r.planned_delivery_end != r.planned_delivery_start else ""),
        "comments": r.comments if isinstance(r.comments, str) else None,
    }


def reexport_record(removed: pd.DataFrame) -> dict | None:
    """Imported equipment this country has since passed on, still deducted in the data year."""
    total = -removed["tiv"].sum()
    if total < 0.5:
        return None
    by_recipient = (-removed.groupby("recipient")["tiv"].sum()).sort_values(ascending=False)
    return {"total": _r(total), "toRecipients": {k: _r(v) for k, v in by_recipient.head(5).items() if v >= 0.5}}


def inherited_record(iso3: str, legacy: pd.DataFrame) -> dict | None:
    """What was added for equipment inherited at independence, with sources."""
    if iso3 not in COVERED:
        return None
    rows = legacy[legacy["iso3"] == iso3]
    if rows.empty:
        return {"status": "no_quantities"}
    matched = rows[rows["family"].notna()].sort_values("tiv", ascending=False)
    pages = rows.drop_duplicates("page")
    return {
        "status": "added",
        "since": INDEPENDENCE_YEAR,
        "total": _r(matched["tiv"].sum()),
        "pages": [{"title": p.page, "revid": int(p.revid)} for p in pages.itertuples()],
        "unmatched": int(rows["family"].isna().sum()),
        "rows": [{
            "system": r.system, "quantity": int(r.quantity), "origin": r.origin, "cap": r.capability,
            "launchersPerUnit": int(r.launchers_per_unit), "recordedUnits": _r(r.recorded_units),
            "countedUnits": _r(r.counted_units), "unitTiv": _r(r.unit_tiv, 2), "tiv": _r(r.tiv), "page": r.page,
        } for r in matched.itertuples()],
    }


def build():
    deals = pd.read_parquet(DEALS_PARQUET)
    data_year = int(deals["data_year"].iloc[0])
    deals = deals[deals["buyer_is_state"] & deals["buyer_successor_iso3"].notna()].copy()
    deals = deals[deals["design_origin_iso3"].notna()]

    deals["life"] = deals["capability"].map(SERVICE_LIFE) / np.where(deals["is_second_hand"], 2, 1)

    tranches = explode_deliveries(deals)
    reexports = reexport_tranches(deals, tranches)
    removed_now = reexports[(reexports["year"] <= data_year) & (data_year < reexports["year"] + reexports["life"])]
    logger.info("Re-exports: %d adjustments, %.0f TIV removed in total, %.0f still relevant in %d",
                len(reexports), -reexports["tiv"].sum(), -removed_now["tiv"].sum(), data_year)
    tranches = pd.concat([tranches, reexports.drop(columns="recipient")], ignore_index=True)
    live_now = tranches[(tranches["year"] <= data_year) & (data_year < tranches["year"] + tranches["life"])]
    deals["tiv_in_service"] = deals["deal_id"].map(live_now.groupby("deal_id")["tiv"].sum()).fillna(0.0)

    years = range(SERIES_START, data_year + 1)

    # Equipment successor states inherited at independence (not in SIPRI)
    legacy = legacy_holdings(deals)
    legacy_matched = legacy[legacy["family"].notna() & (legacy["tiv"] > 0)]
    logger.info("Inherited equipment: %d of %d Wikipedia rows matched to SIPRI systems, %.0f TIV across %d countries",
                legacy["family"].notna().sum(), len(legacy), legacy_matched["tiv"].sum(), legacy_matched["iso3"].nunique())

    # Names: latest SIPRI spelling for each code
    buyer_names = deals.sort_values("order_year").groupby("buyer_successor_iso3")["buyer"].last().to_dict()
    origin_names = (
        deals[deals["seller_successor_iso3"] == deals["design_origin_iso3"]]
        .sort_values("order_year").groupby("design_origin_iso3")["seller"].last().to_dict()
    )
    origin_names.update(ORIGIN_LABELS)

    country_dir = APP_DATA_DIR / "country"
    country_dir.mkdir(parents=True, exist_ok=True)
    for old in country_dir.glob("*.json"):
        old.unlink()

    index = []
    for iso3, cdeals in deals.groupby("buyer_successor_iso3"):
        ctr = tranches[tranches["buyer_successor_iso3"] == iso3]
        cser = in_service_series(ctr, years)
        cleg = legacy_matched[legacy_matched["iso3"] == iso3]
        if not cleg.empty:
            # Observed in service today; assumed held since independence
            inherited = pd.concat([
                cleg.assign(at_year=y)[["origin", "capability", "tiv", "at_year"]]
                for y in years if y >= INDEPENDENCE_YEAR
            ]).rename(columns={"origin": "design_origin_iso3"})
            cser = pd.concat([cser, inherited], ignore_index=True)
        has_holdings = not cser.empty and cser[cser["at_year"] == data_year]["tiv"].sum() > 0
        has_orders = cdeals["tiv_outstanding"].fillna(0).sum() > 0
        if cser.empty or not (has_holdings or has_orders):
            continue

        # In-service share by origin over time
        by_origin_year = cser.groupby(["at_year", "design_origin_iso3"])["tiv"].sum().unstack(fill_value=0)
        by_origin_year = by_origin_year.reindex(list(years), fill_value=0)
        totals_now = by_origin_year.loc[data_year] if data_year in by_origin_year.index else pd.Series(dtype=float)
        origins_ranked = by_origin_year.sum().sort_values(ascending=False).index.tolist()

        # Exposure now: capability x origin
        now = cser[cser["at_year"] == data_year]
        exposure = []
        for cap in CAPABILITY_ORDER:
            c = now[now["capability"] == cap]
            total = c["tiv"].sum()
            if total <= 0:
                continue
            exposure.append({
                "capability": cap,
                "total": _r(total),
                "byOrigin": {o: _r(v) for o, v in c.groupby("design_origin_iso3")["tiv"].sum().sort_values(ascending=False).items() if v > 0},
            })

        # Orders by order year and origin (leading indicator)
        orders = (
            cdeals[cdeals["order_year"] >= SERIES_START]
            .groupby(["order_year", "design_origin_iso3"])["tiv_order"].sum().unstack(fill_value=0)
            .reindex(list(years), fill_value=0)
        )

        open_deals = cdeals[cdeals["deal_state"] == "open"]
        backlog = open_deals.groupby("design_origin_iso3")["tiv_outstanding"].sum()

        relevant = cdeals[(cdeals["tiv_in_service"] > 0) | (cdeals["deal_state"] == "open")
                          | (cdeals["order_year"] >= SERIES_START)]
        relevant = relevant.sort_values(["tiv_in_service", "order_year"], ascending=[False, False])

        n_unc = (relevant["order_year_uncertain"] | relevant["num_ordered_uncertain"] | relevant["num_delivered_uncertain"]).mean()

        profile = {
            "iso3": iso3,
            "name": buyer_names.get(iso3, iso3),
            "dataYear": data_year,
            "seriesStart": SERIES_START,
            "origins": {o: origin_names.get(o, o) for o in set(origins_ranked) | set(backlog.index) | set(orders.columns)},
            "inService": {
                "years": list(years),
                "byOrigin": {o: [_r(v) for v in by_origin_year[o].tolist()] for o in origins_ranked
                             if by_origin_year[o].sum() > 0},
            },
            "orders": {
                "years": list(years),
                "byOrigin": {o: [_r(v) for v in orders[o].tolist()] for o in orders.columns if orders[o].sum() > 0},
            },
            "exposure": exposure,
            "backlog": {
                "total": _r(backlog.sum()),
                "byOrigin": {o: _r(v) for o, v in backlog.sort_values(ascending=False).items() if v > 0},
            },
            # SIPRI's terms require permission to republish >10% of its data, so
            # deal records are left out of public builds unless explicitly enabled.
            "deals": [deal_record(r) for r in relevant.itertuples()] if INCLUDE_DEALS else None,
            "quality": {"shareUncertain": _r(n_unc, 3), "nDeals": int(len(relevant))},
            "inherited": inherited_record(iso3, legacy),
            "reexported": reexport_record(removed_now[removed_now["buyer_successor_iso3"] == iso3]),
        }
        with open(country_dir / f"{iso3}.json", "w", encoding="utf-8") as f:
            json.dump(profile, f, separators=(",", ":"), ensure_ascii=False)

        total_now = float(totals_now.sum())
        shares_now = (totals_now / total_now) if total_now > 0 else totals_now * 0
        top = shares_now.idxmax() if total_now > 0 else None
        base = by_origin_year.loc[COMPARE_YEAR] if COMPARE_YEAR in by_origin_year.index else None
        base_total = float(base.sum()) if base is not None else 0
        index.append({
            "iso3": iso3,
            "name": profile["name"],
            "inService": _r(total_now),
            "topOrigin": top,
            "topShare": _r(shares_now.max(), 3) if top else None,
            "concentration": _r(float((shares_now ** 2).sum()), 3) if total_now > 0 else None,
            "russiaShare": _r(shares_now.get("RUS", 0.0), 3) if total_now > 0 else None,
            "russiaShareThen": _r(base.get("RUS", 0.0) / base_total, 3) if base_total > 0 else None,
            "backlog": profile["backlog"]["total"],
            "nDeals": profile["quality"]["nDeals"],
        })

    index.sort(key=lambda r: -(r["inService"] or 0))
    with open(APP_DATA_DIR / "countries.json", "w", encoding="utf-8") as f:
        json.dump({"dataYear": data_year, "compareYear": COMPARE_YEAR,
                   "origins": origin_names, "countries": index}, f, separators=(",", ":"), ensure_ascii=False)
    return index


def main():
    logger.info("=== Step 3: Country dependency profiles ===")
    index = build()
    sizes = sorted((p.stat().st_size for p in (APP_DATA_DIR / "country").glob("*.json")), reverse=True)
    logger.info("Wrote %d country profiles (largest %.0f KB, median %.0f KB)",
                len(index), sizes[0] / 1024, sizes[len(sizes) // 2] / 1024)


if __name__ == "__main__":
    main()
