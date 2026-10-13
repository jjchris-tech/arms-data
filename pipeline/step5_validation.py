"""
Step 5: Check our estimates against the CIA World Factbook.

The Factbook (final edition, 2025) describes each military's equipment in a
sentence: "the inventory consists mostly of Russian/Soviet-origin equipment
along with smaller quantities from China and Israel". That is an independent,
public-domain statement we can test our in-service estimate against.

Two strengths of test, kept separate because they mean different things:
  dominant — the Factbook names a main source. Strong test: is our top
             design origin one of the sources it names as main?
  mixed    — the Factbook only lists suppliers. Weak test: is our top origin
             among the suppliers it names at all?

Verdicts:
  agree         our top origin is a named main source (dominant) / is named (mixed)
  partial       dominant only: our #2 origin is a main source, or our #1 is
                named as a secondary supplier
  disagree      none of the above
  not_comparable  the Factbook names no origins, or we estimate nothing in service

Inputs:  data/reference/factbook_equipment.csv (public domain, committed)
         dashboard/public/data/country/*.json  (step 3)
Output:  dashboard/public/data/validation.json
"""

import csv
import json
import logging
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config
from pipeline.utils.design_origin import EUROPEAN as EUROPEAN_ISO3
from pipeline.utils.factbook import EUROPEAN, WESTERN, parse

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REFERENCE_CSV = config.PROJECT_ROOT / "data" / "reference" / "factbook_equipment.csv"
OUT = config.APP_DATA_DIR / "validation.json"
SMALL_ARSENAL = 100   # TIV in service; below this one delivery swings the shares
MIN_SHARE = 0.05      # an origin must hold at least this share to count as "ours"

BLOCS = {
    EUROPEAN: set(EUROPEAN_ISO3),
    WESTERN: set(EUROPEAN_ISO3) | {"USA", "CAN"},
}


def expand(origins: list[str]) -> set[str]:
    out = set()
    for o in origins:
        out |= BLOCS.get(o, {o})
    return out


def our_ranking(profile: dict) -> list[tuple[str, float]]:
    """Design origins in service in the data year, by share, largest first."""
    i = profile["inService"]["years"].index(profile["dataYear"])
    values = {o: (s[i] or 0) for o, s in profile["inService"]["byOrigin"].items()}
    total = sum(values.values())
    if total <= 0:
        return []
    return sorted(((o, v / total) for o, v in values.items() if v > 0), key=lambda x: -x[1])


def verdict(claim: dict, ranking: list[tuple[str, float]]) -> str:
    if claim["mode"] == "none" or not ranking:
        return "not_comparable"
    top1 = ranking[0][0]
    top2 = ranking[1][0] if len(ranking) > 1 and ranking[1][1] >= MIN_SHARE else None
    primary, mentioned = expand(claim["primary"]), expand(claim["mentioned"])
    if claim["mode"] == "dominant":
        if top1 in primary:
            return "agree"
        if (top2 and top2 in primary) or top1 in mentioned:
            return "partial"
        return "disagree"
    return "agree" if top1 in mentioned else "disagree"


def build() -> dict:
    with open(REFERENCE_CSV, encoding="utf-8") as f:
        reference = {r["iso3"]: r for r in csv.DictReader(f)}

    countries = {}
    for path in sorted((config.APP_DATA_DIR / "country").glob("*.json")):
        with open(path, encoding="utf-8") as f:
            profile = json.load(f)
        iso3 = profile["iso3"]
        ref = reference.get(iso3)
        if not ref:
            continue
        claim = parse(ref["text"], iso3)
        ranking = our_ranking(profile)
        total = sum(profile["inService"]["byOrigin"][o][-1] or 0 for o in profile["inService"]["byOrigin"])
        countries[iso3] = {
            "verdict": verdict(claim, ranking),
            "test": claim["mode"],
            "factbookText": ref["text"],
            "factbookYear": claim["year"],
            "factbookPrimary": claim["primary"],
            "factbookMentioned": claim["mentioned"],
            "factbookDomestic": claim["domestic"],
            "ours": [{"origin": o, "share": round(s, 3)} for o, s in ranking[:3]],
            "smallArsenal": total < SMALL_ARSENAL,
        }

    def rate(rows):
        n = len(rows)
        c = Counter(r["verdict"] for r in rows)
        return {"n": n, **{k: c.get(k, 0) for k in ("agree", "partial", "disagree")},
                "agreeRate": round(c.get("agree", 0) / n, 3) if n else None}

    comparable = [r for r in countries.values() if r["verdict"] != "not_comparable"]
    summary = {
        "source": "CIA World Factbook, final edition (2025), field 'Military equipment inventories and acquisitions'",
        "dominant": rate([r for r in comparable if r["test"] == "dominant"]),
        "mixed": rate([r for r in comparable if r["test"] == "mixed"]),
        "dominantLargeArsenals": rate([r for r in comparable if r["test"] == "dominant" and not r["smallArsenal"]]),
        "notComparable": len(countries) - len(comparable),
    }
    return {"summary": summary, "countries": countries}


def main():
    logger.info("=== Step 5: Validation against CIA World Factbook ===")
    result = build()
    s = result["summary"]
    for key in ("dominant", "dominantLargeArsenals", "mixed"):
        r = s[key]
        logger.info("%-22s n=%3d  agree %d  partial %d  disagree %d  (agree rate %.0f%%)",
                    key, r["n"], r["agree"], r["partial"], r["disagree"], (r["agreeRate"] or 0) * 100)
    logger.info("not comparable: %d", s["notComparable"])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, separators=(",", ":"), ensure_ascii=False)
    logger.info("Wrote %s", OUT.name)


if __name__ == "__main__":
    main()
