"""
Inherited ("legacy") equipment for successor states of the USSR and Yugoslavia.

These states took over arsenals at independence without any recorded transfer,
so SIPRI cannot see them. data/reference/legacy_holdings.csv lists Soviet- and
Yugoslav-origin systems they operate today (from Wikipedia, CC BY-SA). This
module turns that list into in-service TIV on the same basis as the rest of the
model:

  1. Match each system to a SIPRI weapon family of Soviet/Russian, Ukrainian,
     Belarusian or Yugoslav design (by designator code or name token). Systems
     SIPRI does not cover (trucks, small arms, light mortars) do not match and
     are left out — the same scope as everything else on the site.
  2. Subtract units SIPRI already shows in service for that country and family,
     so recorded imports are never counted twice.
  3. Value the remainder at SIPRI's unit TIV for that family x 0.4, SIPRI's own
     valuation convention for second-hand equipment.
"""

import re
from collections import Counter, defaultdict

import pandas as pd

from .. import config

LEGACY_CSV = config.PROJECT_ROOT / "data" / "reference" / "legacy_holdings.csv"
SECOND_HAND_FACTOR = 0.4
LEGACY_ORIGINS = {"RUS", "UKR", "BLR", "SRB"}
INDEPENDENCE_YEAR = 1992

# Successor states whose Wikipedia pages were checked (see build_legacy_reference.py).
# Those with no rows in the CSV list systems without quantities, so cannot be sized.
COVERED = ["UKR", "BLR", "MDA", "ARM", "AZE", "GEO", "KAZ", "KGZ", "TJK", "TKM", "UZB",
           "SRB", "MNE", "BIH", "HRV", "MKD"]

# SIPRI counts long-range air-defence systems per battalion/battery, Wikipedia per
# launcher. Typical launchers per SIPRI unit (approximate, Soviet-era establishment):
LAUNCHERS_PER_UNIT = {
    "S300": 12, "S400": 8, "S200": 6, "S75": 6, "S125": 4,
    "BUK1": 6, "BUKM2": 6, "KVADRAT": 4, "2K11KRUG": 3,
}
# SIPRI's register discounts second-hand unit TIVs; divide to get the new-equivalent
SECOND_HAND_DISCOUNT = {"Second hand": 0.4, "Second hand but modernized": 0.66}

_STOP = {"MM", "SAM", "SYSTEM", "VERSION", "RADAR", "ENGINE", "TRUCK", "MOD", "MODEL", "TYPE",
         "MK", "VARIANT", "UPGRADE", "UPGRADED", "MODERNIZED", "LATE", "EARLY", "SERIES"}


def tokens(name: str) -> list[str]:
    """Candidate keys for a designation: 'T-72B' -> ['T72B', 'T72'], '122mm 2S1 Gvozdika' -> ['2S1', 'GVOZDIKA']."""
    if not isinstance(name, str):
        return []
    s = re.sub(r"\b\d+\s?mm\b", " ", name, flags=re.IGNORECASE)
    out = []
    for piece in re.split(r"[\s/,()'\"]+", s):
        norm = re.sub(r"[^A-Za-z0-9]", "", piece).upper()
        if not norm or norm in _STOP:
            continue
        if not re.search(r"\d", norm) and len(norm) < 3:
            continue
        out.append(norm)
        m = re.match(r"^([A-Z]+)(\d+)", norm)          # strip variant suffix: T72B -> T72
        if m and m.group(0) != norm:
            out.append(m.group(0))
    return list(dict.fromkeys(out))


def build_index(deals: pd.DataFrame) -> tuple[dict, pd.DataFrame]:
    """token -> SIPRI design family, plus per-family unit TIV, capability and origin."""
    d = deals[deals["design_family"].notna()]
    # Families of Soviet/Yugoslav lineage: designed there, or ever sold by the USSR,
    # Yugoslavia or their successors (Yugoslav designs often appear only as resales
    # by Croatia or Slovenia).
    lineage = set(d.loc[d["design_origin_iso3"].isin(LEGACY_ORIGINS), "design_family"]) | set(
        d.loc[d["seller_iso3"].isin({"SUN", "YUG"}), "design_family"])

    token_families = defaultdict(Counter)
    for fam, des in zip(d["design_family"], d["designation"]):
        for t in tokens(des):
            token_families[t][fam] += 1
    index = {}
    for t, c in token_families.items():
        if len(c) > 3:          # shared by many families; identifies nothing
            continue
        # Prefer Soviet/Yugoslav-lineage families, then the most common
        index[t] = max(c, key=lambda f: (f in lineage, c[f]))

    # Unit TIV of a new item: from new deals, else back out SIPRI's second-hand discount
    unit_new = d[(d["status"] == "New") & (d["tiv_unit"] > 0)].groupby("design_family")["tiv_unit"].median()
    used = d[d["status"].isin(SECOND_HAND_DISCOUNT) & (d["tiv_unit"] > 0)]
    unit_used = (used["tiv_unit"] / used["status"].map(SECOND_HAND_DISCOUNT)).groupby(used["design_family"]).median()
    fams = pd.DataFrame({
        "unit_tiv": unit_new.combine_first(unit_used),
        "capability": d.groupby("design_family")["capability"].agg(lambda s: s.mode().iloc[0]),
        "origin": d.groupby("design_family")["design_origin_iso3"].agg(lambda s: s.mode().iloc[0]),
        "lineage": pd.Series({f: f in lineage for f in d["design_family"].unique()}),
    }).dropna(subset=["unit_tiv"])
    return {t: f for t, f in index.items() if f in fams.index and fams.loc[f, "lineage"]}, fams


def _origin(wiki_origin: str, family_origin: str) -> str:
    """Yugoslav designs -> SRB (Yugoslavia's successor); Soviet designs keep a
    Soviet-lineage origin (RUS, or UKR/BLR for designs from bureaux there)."""
    if re.search(r"yugoslav|sfry", str(wiki_origin), re.IGNORECASE):
        return "SRB"
    return family_origin if family_origin in LEGACY_ORIGINS else "RUS"


def legacy_holdings(deals: pd.DataFrame) -> pd.DataFrame:
    """
    One row per Wikipedia system with its SIPRI match and the TIV added.
    `deals` must already carry `tiv_in_service` (step 3).
    """
    ref = pd.read_csv(LEGACY_CSV)
    index, fams = build_index(deals)

    # Units SIPRI already shows in service, per (country, family)
    d = deals[deals["tiv_delivered"] > 0]
    in_service_units = (
        (d["num_delivered"].fillna(0) * d["tiv_in_service"] / d["tiv_delivered"])
        .groupby([d["buyer_successor_iso3"], d["design_family"]]).sum()
    )

    rows = []
    for r in ref.itertuples():
        family = next((index[t] for t in tokens(r.system) if t in index), None)
        row = {"iso3": r.iso3, "system": r.system, "quantity": int(r.quantity), "page": r.page,
               "revid": int(r.revid), "family": family}
        if family:
            f = fams.loc[family]
            per_unit = LAUNCHERS_PER_UNIT.get(family, 1)
            units = r.quantity / per_unit
            recorded = float(in_service_units.get((r.iso3, family), 0.0))
            counted = max(0.0, units - recorded)
            row.update({
                "capability": f["capability"], "origin": _origin(r.origin, f["origin"]),
                "unit_tiv": float(f["unit_tiv"]), "launchers_per_unit": per_unit,
                "recorded_units": round(recorded, 1), "counted_units": round(counted, 1),
                "tiv": counted * float(f["unit_tiv"]) * SECOND_HAND_FACTOR,
            })
        rows.append(row)
    return pd.DataFrame(rows)
