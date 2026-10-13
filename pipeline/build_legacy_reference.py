"""
One-off: extract Soviet- and Yugoslav-origin equipment still in service in the
successor states of the USSR and Yugoslavia, from Wikipedia's equipment lists.

Why: these states took over their arsenals at independence. No transfer was
recorded, so SIPRI (and our in-service model) cannot see that equipment, and our
estimate understates their dependence on Russian/Soviet designs. Wikipedia's
lists (mostly sourced from IISS Military Balance) give what is in service now.

Output: data/reference/legacy_holdings.csv — one row per system per country,
with the page title and revision id it came from. Wikipedia content is
CC BY-SA 4.0; this derived file carries the same licence and attribution.

Requires lxml (pip install lxml); only needed to rebuild the reference file.

    python pipeline/build_legacy_reference.py
"""

import csv
import io
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config

OUT = config.PROJECT_ROOT / "data" / "reference" / "legacy_holdings.csv"
API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "arms-dependency-research/0.1 (https://jjchris-tech.github.io/arms-data/)"

# Successor states and the Wikipedia pages listing their current equipment.
# Baltic states are omitted: Soviet forces withdrew and they inherited almost nothing.
PAGES = {
    "UKR": ["List of equipment of the Armed Forces of Ukraine", "Ukrainian Air Force"],
    "BLR": ["List of equipment of the Armed Forces of Belarus", "Belarusian Air Force"],
    "MDA": ["Moldovan Air Force"],
    "ARM": ["List of equipment of the Armenian Armed Forces"],
    "AZE": ["List of equipment of the Azerbaijani Land Forces", "Azerbaijani Air Forces"],
    "GEO": ["List of equipment of the Defense Forces of Georgia"],
    "KAZ": ["List of equipment of the Armed Forces of the Republic of Kazakhstan"],
    "KGZ": ["Armed Forces of the Kyrgyz Republic"],
    "TJK": ["Tajik Ground Forces", "Tajik Air Force"],
    "TKM": ["Armed Forces of Turkmenistan"],
    "UZB": ["List of equipment of the Armed Forces of the Republic of Uzbekistan"],
    "SRB": ["List of equipment of the Serbian Armed Forces"],
    "MNE": ["Armed Forces of Montenegro"],
    "BIH": ["List of equipment of the Armed Forces of Bosnia and Herzegovina"],
    "HRV": ["List of equipment of the Armed Forces of Croatia"],
    "MKD": ["List of equipment of the Army of North Macedonia"],
}

# Origins that mean "inherited from the USSR or Yugoslavia" (or a later Russian
# purchase of a Soviet design — the pipeline subtracts SIPRI-recorded deliveries).
LEGACY_ORIGIN = re.compile(r"soviet|ussr|u\.s\.s\.r|russia|yugoslav|sfry|sfr yugoslavia", re.IGNORECASE)

NAME_COLS = ("name", "model", "aircraft", "equipment", "vehicle", "system", "weapon")
ORIGIN_COLS = ("origin", "country of origin", "manufacturer")
QTY_COLS = ("quantity", "in service", "number", "qty", "active", "amount", "total")
TYPE_COLS = ("type", "role", "class")


def fetch(title: str) -> dict:
    params = {"action": "parse", "page": title, "redirects": 1, "prop": "text|revid",
              "format": "json", "formatversion": 2}
    resp = requests.get(API, params=params, headers={"User-Agent": USER_AGENT}, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"{title}: {data['error'].get('info')}")
    return data["parse"]


def pick(cols: list[str], wanted: tuple[str, ...]) -> str | None:
    for c in cols:
        if c.strip().lower().startswith(wanted):
            return c
    return None


def quantity(text) -> int | None:
    """
    '100+[5]' -> 100, '~30' -> 30, '12 (2 operational)' -> 12, 'Unknown' -> None.
    Variant lines separated by '¦' are summed: '296 ¦ 29' -> 325.
    """
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return None
    total, found = 0, False
    for part in str(text).split("¦"):
        s = re.sub(r"\[[^\]]*\]", "", part).replace(",", "")
        m = re.search(r"\d+", s)
        if m:
            total += int(m.group())
            found = True
    return total if found else None


_FLAG_IMG = re.compile(r'<img[^>]*?src="[^"]*?/(Flag_of_[^/"]+?)\.svg[^"]*"[^>]*>', re.IGNORECASE)


def extract(iso3: str, page: dict) -> list[dict]:
    rows = []
    # Many tables show origin only as a flag image with empty alt text; keep the
    # flag's file name ("Flag_of_the_Soviet_Union") as text so it can be matched.
    text = _FLAG_IMG.sub(lambda m: " " + m.group(1).replace("_", " ") + " ", page["text"])
    # Cells listing several variants on separate lines ("296<br>29") would otherwise
    # run together ("29629"); keep the line breaks as an explicit separator.
    text = re.sub(r"<br\s*/?>|<hr\s*/?>|</li>|</p>", " ¦ ", text, flags=re.IGNORECASE)
    try:
        tables = pd.read_html(io.StringIO(text))
    except ValueError:
        return rows
    for t in tables:
        if isinstance(t.columns, pd.MultiIndex):
            t.columns = [str(c[0]) for c in t.columns]
        cols = [str(c) for c in t.columns]
        origin_c, qty_c = pick(cols, ORIGIN_COLS), pick(cols, QTY_COLS)
        if not origin_c or not qty_c:
            continue
        name_c = pick(cols, NAME_COLS) or cols[0]
        type_c = pick(cols, TYPE_COLS)
        for _, r in t.iterrows():
            values = [str(v) for v in r.values]
            if len(set(values)) == 1:          # section header row ("Tanks | Tanks | Tanks")
                continue
            origin = str(r[origin_c])
            if not LEGACY_ORIGIN.search(origin):
                continue
            qty = quantity(r[qty_c])
            if not qty:
                continue
            rows.append({
                "iso3": iso3,
                "system": re.sub(r"\[[^\]]*\]", "", str(r[name_c])).split("¦")[0].strip(),
                "origin": origin.strip(),
                "type": "" if type_c is None or pd.isna(r[type_c]) else re.sub(r"\[[^\]]*\]", "", str(r[type_c])).strip(),
                "quantity": qty,
                "quantity_text": re.sub(r"\[[^\]]*\]", "", str(r[qty_c])).strip(),
                "page": page["title"],
                "revid": page["revid"],
            })
    return rows


def main():
    rows = []
    for iso3, titles in PAGES.items():
        for title in titles:
            page = fetch(title)
            got = extract(iso3, page)
            print(f"{iso3} {page['title'][:60]:60} rev {page['revid']}: {len(got)} legacy rows")
            rows += got
            time.sleep(1)  # be polite to the API

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["iso3", "system", "origin", "type", "quantity", "quantity_text", "page", "revid"])
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
