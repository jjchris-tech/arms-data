"""
Sanity checks on pipeline output against facts we know independently.

Run after the pipeline (run_all.py does this automatically). A failure means a
code or data change has shifted results in a way that needs a human look —
not necessarily a bug, but never something to ship unexamined.

    python pipeline/checks.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config
from pipeline.step2_deals import DEALS_PARQUET
from pipeline.utils.capabilities import report_unmapped

failures = []

CAPABILITY_SHARE_BANDS = {
    "Combat aircraft": (0.15, 0.40),
    "Naval": (0.08, 0.25),
    "Armour": (0.06, 0.20),
    "Support aircraft & drones": (0.04, 0.16),
    "Air defence": (0.045, 0.16),
    "Missiles & munitions": (0.04, 0.16),
    "Helicopters": (0.04, 0.16),
    "Sensors & components": (0.04, 0.16),
    "Artillery": (0.01, 0.05),
}


def check(ok: bool, message: str):
    print(("  ok   " if ok else "  FAIL ") + message)
    if not ok:
        failures.append(message)


def profile(iso3):
    with open(config.APP_DATA_DIR / "country" / f"{iso3}.json", encoding="utf-8") as f:
        return json.load(f)


def share_now(p, origin):
    i = p["inService"]["years"].index(p["dataYear"])
    total = sum(s[i] or 0 for s in p["inService"]["byOrigin"].values())
    return (p["inService"]["byOrigin"].get(origin, [0] * (i + 1))[i] or 0) / total


def main():
    deals = pd.read_parquet(DEALS_PARQUET)

    print("Classification")
    check(not report_unmapped(deals["weapon_desc"].dropna().unique()), "every weapon type maps to a capability area")
    for seller, family, origin in [
        ("Netherlands", "F16", "USA"),     # second-hand resale keeps US origin
        ("Ukraine", "R27", "RUS"),         # Soviet design resold by Ukraine
        ("Soviet Union", "AN26", "UKR"),   # Antonov is a Ukrainian bureau
        ("Soviet Union", "MIG21", "RUS"),  # USSR merged into Russia
    ]:
        rows = deals[(deals["seller"] == seller) & (deals["design_family"] == family)]
        check(len(rows) > 0 and (rows["design_origin_iso3"] == origin).all(),
              f"{family} sold by {seller} -> design origin {origin}")

    # Guards against SIPRI renaming weapon types so they silently fall into the
    # wrong area (March 2026: "SAM" -> "surface-to-air missile" moved all air
    # defence into munitions). Bands are roughly half to double the 1990-2025 shares.
    recent = deals[deals["first_delivery"] >= 1990]
    shares = recent.groupby("capability")["tiv_delivered"].sum()
    shares = shares / shares.sum()
    for cap, (lo, hi) in CAPABILITY_SHARE_BANDS.items():
        s = shares.get(cap, 0)
        check(lo <= s <= hi, f"{cap} is {s:.0%} of deliveries since 1990 (expected {lo:.0%} to {hi:.0%})")

    print("Country profiles (well-documented arsenals)")
    india, poland, vietnam = profile("IND"), profile("POL"), profile("VNM")
    check(0.55 <= share_now(india, "RUS") <= 0.75, f"India mostly Russian-designed ({share_now(india, 'RUS'):.0%})")
    check(share_now(poland, "USA") > share_now(poland, "RUS"), "Poland now more US- than Russian-designed")
    check(share_now(vietnam, "RUS") >= 0.75, f"Viet Nam overwhelmingly Russian-designed ({share_now(vietnam, 'RUS'):.0%})")

    with open(config.APP_DATA_DIR / "countries.json", encoding="utf-8") as f:
        index = json.load(f)
    check(len(index["countries"]) >= 150, f"index covers {len(index['countries'])} countries")

    if failures:
        print(f"\n{len(failures)} check(s) failed")
        sys.exit(1)
    print("\nAll checks passed")


if __name__ == "__main__":
    main()
