"""
Design origin and successor-state handling.

SIPRI records the *selling state*, which is not always the country that
designed the weapon (and still controls its spare parts and upgrades):

  - The Soviet Union is coded separately (SUN) from Russia (RUS).
  - Second-hand kit is resold by third countries (Dutch F-16s to Jordan,
    Polish MiG-29s to Ukraine, Czech T-72s to Georgia).
  - Licensed production is already coded with the licensor as seller,
    so it needs no special handling.

Method — data-driven, per weapon family:
  1. Normalise each designation to a family key (Su-30MKI -> SU30, F-16C -> F16).
  2. Among *new* (not second-hand) deals for that family, take the seller
     (after successor merge) with the majority of deals. That is the design origin.
  3. Families with no clear majority fall back to a Soviet/Russian name-pattern
     check, then to the deal's own seller.

Every deal records which rule assigned its origin (`origin_method`) so the
attribution can be audited.
"""

import re

import pandas as pd

# Historical states -> the successor that inherited their defence industry
# (seller side) or the bulk of their inventory (buyer side).
# CSK -> CZE and YUG -> SRB are simplifications: Slovakia and the other
# Yugoslav successors also inherited equipment.
SUCCESSOR = {
    "SUN": "RUS",
    "DDR": "DEU",
    "CSK": "CZE",
    "YUG": "SRB",
}

EUROPEAN = {
    "FRA", "GBR", "DEU", "ITA", "ESP", "SWE", "NLD", "BEL", "NOR", "CHE",
    "AUT", "DNK", "FIN", "PRT", "IRL", "GRC", "POL", "CZE", "SVK", "ROU",
    "HUN", "BGR", "HRV", "SVN", "EST", "LVA", "LTU", "LUX",
}


def successor(iso3):
    return SUCCESSOR.get(iso3, iso3)


def design_bloc(iso3) -> str:
    if iso3 == "RUS":
        return "Soviet/Russian"
    if iso3 == "USA":
        return "United States"
    if iso3 == "CHN":
        return "Chinese"
    if iso3 in EUROPEAN:
        return "European"
    return "Other"


_FAMILY_RE = re.compile(r"^([A-Za-z]+)[\s\-]?(\d+)")


def family_key(designation, weapon_desc=None) -> str | None:
    """
    'Su-30MKI' -> 'SU30', 'F-16C' -> 'F16', 'Type-054A' -> 'TYPE054',
    'Super Etendard' -> 'SUPERETENDARD'.

    Returns None for generic designations ('aircraft engine', 'vehicle engine'),
    which SIPRI uses when the exact system is unknown — they say nothing about
    who designed it.
    """
    if not isinstance(designation, str) or not designation.strip():
        return None
    d = designation.strip()
    if d.islower() or (isinstance(weapon_desc, str) and d.lower() == weapon_desc.strip().lower()):
        return None
    m = _FAMILY_RE.match(d)
    if m:
        return f"{m.group(1)}{m.group(2)}".upper()
    return re.sub(r"[^A-Za-z0-9]", "", d).upper() or None


# Fallback only, for families never seen as a new-build deal (e.g. only ever
# resold second-hand) that are unambiguously Soviet/Russian designs. Kept
# deliberately narrow: bare 'M-', 'S-', 'D-', 'R-' prefixes also match
# Western designations (M-24 Chaffee, S-70, R-550 Magic).
_SOVIET_RE = re.compile(
    r"^(Su|MiG|Mi|Ka|Yak|Tu|Il|An|Be)-\d"
    r"|^T-(34|54|55|62|64|72|80|90)\b"
    r"|^(BMP|BTR|BRDM|BMD|MT-LB|ZSU|ZU|BM|TOS|2S|9K|9M|SA|Kh)-\d"
    r"|^S-(75|125|200|300|400|500)\b|^D-(20|30|44)\b|^R-(27|60|73|77)\b"
    r"|^(Igla|Strela|Kornet|Konkurs|Fagot|Malyutka|Osa|Kub|Krug|Tor|Buk|Pantsir|Tunguska|Shilka|Grad|Smerch|Uragan)\b"
    r"|^(Kilo|Foxtrot|Petya|Koni|Grisha|Tarantul|Nanuchka|Polnocny)\b",
    re.IGNORECASE,
)


# Antonov (An- aircraft) and Ivchenko-Progress (AI- engines) family keys
_UKRAINIAN_BUREAU_RE = re.compile(r"^(AN|AI)\d")


def _majority_origin(new: pd.DataFrame, keys: list[str], min_share: float) -> dict:
    """{key tuple: seller} where one seller has >= min_share of new-build deals."""
    counts = new.groupby(keys + ["seller_successor_iso3"]).size()
    grp = counts.groupby(level=list(range(len(keys))))
    share = grp.max() / grp.sum()
    top = grp.idxmax().map(lambda ix: ix[-1])
    return top[share >= min_share].to_dict()


def assign_design_origin(deals: pd.DataFrame, min_share: float = 0.5) -> pd.DataFrame:
    """
    Add design_family, design_origin_iso3, design_bloc, origin_method columns.

    Families are matched at two levels so that name collisions across weapon
    types don't leak (Cobra helicopter vs Cobra APC, KS-1 gun vs KS-1 SAM):
      1. family + exact weapon_desc   ('M30', 'towed gun')
      2. family + capability area     ('M30', 'Artillery')
    """
    df = deals.copy()
    df["design_family"] = [family_key(d, w) for d, w in zip(df["designation"], df["weapon_desc"])]
    df["seller_successor_iso3"] = df["seller_iso3"].map(successor)

    new = df[(df["status"] == "New") & df["design_family"].notna() & df["seller_successor_iso3"].notna()]
    by_desc = _majority_origin(new, ["design_family", "weapon_desc"], min_share)
    by_cat = _majority_origin(new, ["design_family", "capability"], min_share)

    origins, methods = [], []
    for fam, desc, cat, des, seller in zip(
        df["design_family"], df["weapon_desc"], df["capability"], df["designation"], df["seller_successor_iso3"]
    ):
        if (fam, desc) in by_desc:
            origins.append(by_desc[(fam, desc)])
            methods.append("family_majority")
        elif (fam, cat) in by_cat:
            origins.append(by_cat[(fam, cat)])
            methods.append("family_majority")
        elif isinstance(des, str) and _SOVIET_RE.match(des.strip()):
            origins.append("RUS")
            methods.append("soviet_pattern")
        else:
            origins.append(seller)
            methods.append("seller")

    # Soviet design bureaux based in Ukraine: their products were sold by the
    # USSR (merged into RUS above) but parts and upgrades now come from Ukraine.
    for i, fam in enumerate(df["design_family"]):
        if origins[i] == "RUS" and isinstance(fam, str) and _UKRAINIAN_BUREAU_RE.match(fam):
            origins[i] = "UKR"
            methods[i] = "design_bureau"

    df["design_origin_iso3"] = origins
    df["origin_method"] = methods
    df["design_bloc"] = df["design_origin_iso3"].map(design_bloc)
    return df
