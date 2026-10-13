"""
One-off: extract the CIA World Factbook field "Military equipment inventories
and acquisitions" into data/reference/factbook_equipment.csv.

The Factbook was discontinued on 4 Feb 2026; its final public data is mirrored,
public domain (CC0), at https://github.com/factbook/factbook.json. The extracted
CSV is committed to this repo, so this script only needs re-running if the
reference changes.

    git clone --depth 1 https://github.com/factbook/factbook.json <dir>
    python pipeline/build_factbook_reference.py <dir>
"""

import csv
import glob
import html
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config
from pipeline.utils.country_codes import sipri_name_to_iso3

OUT = config.PROJECT_ROOT / "data" / "reference" / "factbook_equipment.csv"
FIELD = "Military equipment inventories and acquisitions"


def country_name(d: dict) -> str | None:
    names = d.get("Government", {}).get("Country name", {})
    for form in ("conventional short form", "conventional long form"):
        text = names.get(form, {}).get("text")
        if text and text.strip().lower() != "none":
            return text.strip()
    return None


def main(src: str):
    rows = []
    for path in sorted(glob.glob(os.path.join(src, "*", "*.json"))):
        if os.path.basename(os.path.dirname(path)) in ("meta", "world", "oceans", "antarctica"):
            continue
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        text = d.get("Military and Security", {}).get(FIELD, {}).get("text")
        name = country_name(d)
        iso3 = sipri_name_to_iso3(name) if name else None
        if not text or not iso3:
            continue
        rows.append({"iso3": iso3, "factbook_code": Path(path).stem, "name": name, "text": html.unescape(text).strip()})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["iso3", "factbook_code", "name", "text"])
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["iso3"]))
    print(f"Wrote {len(rows)} countries to {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
