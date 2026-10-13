"""
One-off: reference data for the UN votes research piece.

Writes three small files to data/reference/:

  un_votes_es11.csv   Recorded votes by country on UN General Assembly emergency
                      session resolutions on Ukraine (ES-11/1 to ES-11/9), parsed
                      from Wikipedia's resolution pages (CC BY-SA 4.0). Each
                      resolution is checked against its official tally.
  ideal_points.csv    Voeten et al. UN General Assembly ideal point estimates,
                      2015-2025 (Harvard Dataverse hdl:1902.1/12379, CC0).
  democracy.csv       V-Dem electoral democracy index, 2015-2025, with OWID
                      region, via Our World in Data (CC BY 4.0).

The UN Digital Library is the primary source for votes but blocks automated
access, so votes come from Wikipedia and are validated against the tallies.

    python pipeline/build_research_reference.py   (needs lxml)
"""

import io
import re
import sys
import time
from pathlib import Path

import lxml.html
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config
from pipeline.utils.country_codes import sipri_name_to_iso3

REF = config.PROJECT_ROOT / "data" / "reference"
HEADERS = {"User-Agent": "arms-dependency-research/0.1 (https://jjchris-tech.github.io/arms-data/)"}
WIKI_API = "https://en.wikipedia.org/w/api.php"
VOETEN_FILE = "https://dataverse.harvard.edu/api/access/datafile/14098429"   # IdealpointestimatesFP_2026FP.csv
OWID_DEMOCRACY = "https://ourworldindata.org/grapher/electoral-democracy-index.csv"
YEARS = range(2015, 2026)

VOTE_CODES = {"approve": "Y", "in favour": "Y", "in favor": "Y", "against": "N", "abstain": "A",
              "abstained": "A", "absent": "X", "present not voting": "X", "non-voting": "X"}

# Wikipedia spellings that country_converter does not resolve
NAME_FIXES = {"Micronesia": "FSM", "Cape Verde": "CPV", "Ivory Coast": "CIV", "Eswatini": "SWZ",
              "Timor-Leste": "TLS", "East Timor": "TLS", "Federated States of Micronesia": "FSM"}


def wiki_votes(n: int) -> tuple[list[dict], dict]:
    title = f"United Nations General Assembly Resolution ES-11/{n}"
    r = requests.get(WIKI_API, params={"action": "parse", "page": title, "prop": "text|revid",
                                       "format": "json", "formatversion": 2}, headers=HEADERS, timeout=60)
    r.raise_for_status()
    page = r.json()["parse"]
    doc = lxml.html.fromstring(page["text"])
    infobox = doc.text_content()
    date = re.search(r"Date\s*(\d{1,2} \w+ \d{4})", infobox)
    subject = re.search(r"Subject\s*(.+?)\s*(Voting summary|Result)", infobox, re.S)

    rows, tallies = [], {}
    for table in doc.xpath("//table"):
        heads = [th.text_content().strip() for th in table.xpath(".//tr[1]/th")]
        if not any(h.startswith("Tally") for h in heads):
            continue
        for tr in table.xpath(".//tr[position()>1]"):
            cells = tr.xpath("./th|./td")
            if len(cells) < 3:
                continue
            label = re.sub(r"\[.*?\]", "", cells[0].text_content()).strip().lower()
            code = VOTE_CODES.get(label)
            if not code:
                continue
            tallies[code] = tallies.get(code, 0) + int(re.sub(r"\D", "", cells[1].text_content()) or 0)
            links = [a.text_content().strip() for a in cells[2].xpath(".//a")]
            names = [x for x in links if x and not x.startswith("[")] or \
                    [x.strip() for x in re.sub(r"\[.*?\]", "", cells[2].text_content()).split(",") if x.strip()]
            for name in names:
                rows.append({"resolution": f"ES-11/{n}", "country_name": name, "vote": code})
        break
    meta = {"resolution": f"ES-11/{n}", "date": date.group(1) if date else None,
            "subject": re.sub(r"\s+", " ", subject.group(1)).strip() if subject else None,
            "tallies": tallies, "revid": page["revid"]}
    return rows, meta


def main():
    REF.mkdir(parents=True, exist_ok=True)

    # 1. Votes
    votes, metas = [], []
    for n in range(1, 10):
        rows, meta = wiki_votes(n)
        counts = pd.Series([r["vote"] for r in rows]).value_counts().to_dict()
        ok = all(counts.get(k, 0) == v for k, v in meta["tallies"].items())
        print(f"ES-11/{n} {meta['date']}: parsed {counts} vs tally {meta['tallies']} -> {'OK' if ok else 'MISMATCH'}")
        meta["matches_tally"] = ok
        for r in rows:
            r.update(date=meta["date"], subject=meta["subject"], revid=meta["revid"], matches_tally=ok)
        votes += rows
        metas.append(meta)
        time.sleep(1)
    v = pd.DataFrame(votes)
    v["iso3"] = [NAME_FIXES.get(n) or sipri_name_to_iso3(n) for n in v["country_name"]]
    unresolved = sorted(v.loc[v["iso3"].isna(), "country_name"].unique())
    if unresolved:
        print("Unresolved names (dropped):", unresolved)
    v = v.dropna(subset=["iso3"])
    v[["resolution", "date", "subject", "iso3", "country_name", "vote", "matches_tally", "revid"]].to_csv(
        REF / "un_votes_es11.csv", index=False, encoding="utf-8")
    print(f"Wrote un_votes_es11.csv ({len(v)} rows)")

    # 2. Ideal points (CC0)
    r = requests.get(VOETEN_FILE, headers=HEADERS, timeout=120)
    r.raise_for_status()
    ip = pd.read_csv(io.BytesIO(r.content))
    ip = ip[ip["year"].isin(YEARS)][["iso3c", "Countryname", "year", "IdealPointFP", "NVotesFP"]]
    ip.columns = ["iso3", "country_name", "year", "ideal_point", "n_votes"]
    ip.to_csv(REF / "ideal_points.csv", index=False, encoding="utf-8")
    print(f"Wrote ideal_points.csv ({len(ip)} rows)")

    # 3. Democracy (CC BY)
    r = requests.get(OWID_DEMOCRACY, params={"v": 1, "csvType": "full", "useColumnShortNames": "true"}, headers=HEADERS, timeout=120)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    d = d[d["year"].isin(YEARS) & d["code"].str.len().eq(3)]
    d = d.rename(columns={"code": "iso3", "entity": "country_name", "electdem_vdem__estimate_best": "electoral_democracy",
                          "owid_region": "region"})
    d[["iso3", "country_name", "year", "electoral_democracy", "region"]].to_csv(REF / "democracy.csv", index=False, encoding="utf-8")
    print(f"Wrote democracy.csv ({len(d)} rows)")


if __name__ == "__main__":
    main()
