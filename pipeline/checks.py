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
from pipeline.utils.legacy import COVERED

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

    print("Re-exports")
    slovakia = profile("SVK")
    check(share_now(slovakia, "RUS") < 0.10,
          f"Slovakia's Soviet kit passed to Ukraine is removed (Russian-designed share {share_now(slovakia, 'RUS'):.0%})")

    print("Supplier view")
    with open(config.APP_DATA_DIR / "supplier" / "RUS.json", encoding="utf-8") as f:
        russia = json.load(f)
    status_of = {d["iso3"]: d["status"] for d in russia["dependents"]}
    check(russia["nMajority"] >= 15, f"{russia['nMajority']} militaries run mostly on Russian/Soviet designs (expect >= 15)")
    check(status_of.get("BLR") == "staying", f"Belarus is staying with Russia ({status_of.get('BLR')})")
    check(status_of.get("AZE") == "moving_away", f"Azerbaijan is moving away from Russia, now buying Israeli/Turkish ({status_of.get('AZE')})")

    print("Inherited equipment (successor states)")
    belarus, uzbekistan = profile("BLR"), profile("UZB")
    check(share_now(belarus, "RUS") >= 0.80, f"Belarus overwhelmingly Russian/Soviet-designed ({share_now(belarus, 'RUS'):.0%})")
    check(share_now(uzbekistan, "RUS") >= 0.60, f"Uzbekistan mainly Russian/Soviet-designed ({share_now(uzbekistan, 'RUS'):.0%})")
    rows = matched = 0
    for iso3 in COVERED:
        inh = profile(iso3).get("inherited") or {}
        if inh.get("status") == "added":
            rows += len(inh["rows"]) + inh["unmatched"]
            matched += len(inh["rows"])
    check(rows > 0 and matched / rows >= 0.60,
          f"{matched} of {rows} listed inherited systems matched to SIPRI ({matched / max(rows, 1):.0%}, need >= 60%)")

    with open(config.APP_DATA_DIR / "countries.json", encoding="utf-8") as f:
        index = json.load(f)
    check(len(index["countries"]) >= 150, f"index covers {len(index['countries'])} countries")

    print("Validation against the CIA World Factbook")
    with open(config.APP_DATA_DIR / "validation.json", encoding="utf-8") as f:
        summary = json.load(f)["summary"]
    rate = summary["dominant"]["agreeRate"]
    check(rate is not None and rate >= 0.70,
          f"top origin agrees with the Factbook's stated main source for {rate:.0%} of countries (need >= 70%)")

    if failures:
        print(f"\n{len(failures)} check(s) failed")
        sys.exit(1)
    print("\nAll checks passed")


if __name__ == "__main__":
    main()
