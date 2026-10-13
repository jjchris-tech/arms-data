"""
Step 6: Research — do militaries that depend on Russian equipment vote with Russia?

Outcome: alignment with Russia on the UN General Assembly's 2022-23 Ukraine
resolutions, using only those whose Wikipedia vote lists match the official
tally exactly (ES-11/1, /2, /3, /4, /6). Russia voted No on all five.
  per vote: No = 1, Abstain = 0.5, Yes = 0; absent = not counted
  alignment = mean over the votes a country cast (0 = always against Russia)

Exposure: Russian/Soviet-designed share of the estimated arsenal in 2021, i.e.
before the invasion, so the votes cannot have shaped it.

Models (OLS, heteroskedasticity-robust HC1 standard errors):
  1. alignment ~ Russian share
  2. + electoral democracy (V-Dem) + region
  3. + US-designed share + former Soviet republic
Robustness: same with each country's UN ideal point in 2023 (Voeten et al.,
all recorded votes, not just Ukraine; lower = further from the US-led bloc);
without Belarus; all arsenal sizes. Absolute distance from Russia's ideal
point is NOT used: Russia sits mid-way along that dimension, so countries more
anti-Western than Russia (Syria, Iran) would look "far from Russia".

Sample: UN members with an estimated arsenal of at least 100 TIV in 2021,
excluding the two parties to the war (Russia, Ukraine).

Output: dashboard/public/data/research/un_votes.json
"""

import json
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

REF = config.PROJECT_ROOT / "data" / "reference"
OUT = config.APP_DATA_DIR / "research" / "un_votes.json"
CORE = ["ES-11/1", "ES-11/2", "ES-11/3", "ES-11/4", "ES-11/6"]
LATER = "ES-11/7"          # Feb 2025: Ukraine's text; the US voted with Russia against it
BASE_YEAR = 2021
IDEAL_YEAR = 2023
MIN_ARSENAL = 100
EXCLUDE = {"RUS", "UKR"}
POST_SOVIET = {"ARM", "AZE", "BLR", "EST", "GEO", "KAZ", "KGZ", "LTU", "LVA", "MDA", "TJK", "TKM", "UKR", "UZB"}
SCORE = {"N": 1.0, "A": 0.5, "Y": 0.0}
BANDS = [(0, 0.10, "Under 10%"), (0.10, 0.25, "10–25%"), (0.25, 0.50, "25–50%"), (0.50, 1.01, "50% or more")]


def _r(x, nd=3):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), nd)


def shares(profile: dict, year: int) -> tuple[float, dict]:
    years, by_origin = profile["inService"]["years"], profile["inService"]["byOrigin"]
    if year not in years:
        return 0.0, {}
    i = years.index(year)
    vals = {o: (s[i] or 0) for o, s in by_origin.items()}
    total = sum(vals.values())
    return total, ({o: v / total for o, v in vals.items()} if total > 0 else {})


def load_countries() -> pd.DataFrame:
    rows = []
    for path in (config.APP_DATA_DIR / "country").glob("*.json"):
        with open(path, encoding="utf-8") as f:
            p = json.load(f)
        total, sh = shares(p, BASE_YEAR)
        _, sh_now = shares(p, p["dataYear"])
        rows.append({"iso3": p["iso3"], "name": p["name"], "arsenal": total,
                     "rus_share": sh.get("RUS", 0.0), "usa_share": sh.get("USA", 0.0),
                     "rus_share_now": sh_now.get("RUS", 0.0)})
    df = pd.DataFrame(rows)
    with open(config.APP_DATA_DIR / "supplier" / "RUS.json", encoding="utf-8") as f:
        status = {d["iso3"]: d["status"] for d in json.load(f)["dependents"]}
    df["russia_status"] = df["iso3"].map(status)
    return df


def alignment(votes: pd.DataFrame, resolutions: list[str]) -> pd.DataFrame:
    v = votes[votes["resolution"].isin(resolutions)].copy()
    v["score"] = v["vote"].map(SCORE)
    g = v.groupby("iso3")
    out = pd.DataFrame({
        "alignment": g["score"].mean(),
        "n_cast": g["score"].count(),
        "n_absent": g["vote"].apply(lambda s: (s == "X").sum()),
        "n_no": g["vote"].apply(lambda s: (s == "N").sum()),
        "n_abstain": g["vote"].apply(lambda s: (s == "A").sum()),
        "n_yes": g["vote"].apply(lambda s: (s == "Y").sum()),
    })
    return out


def fit(formula: str, data: pd.DataFrame) -> dict:
    m = smf.ols(formula, data=data).fit(cov_type="HC1")
    terms = {}
    for name in m.params.index:
        if name == "Intercept" or name.startswith("C(region)"):
            continue
        terms[name] = {"coef": _r(m.params[name], 4), "se": _r(m.bse[name], 4), "p": _r(m.pvalues[name], 4),
                       "ci": [_r(m.conf_int().loc[name, 0], 4), _r(m.conf_int().loc[name, 1], 4)]}
    return {"formula": formula, "n": int(m.nobs), "r2": _r(m.rsquared, 3), "terms": terms,
            "regionControls": "C(region)" in formula}


def build() -> dict:
    votes = pd.read_csv(REF / "un_votes_es11.csv")
    meta = votes.drop_duplicates("resolution").set_index("resolution")[["date", "subject", "matches_tally"]]
    ideal = pd.read_csv(REF / "ideal_points.csv")
    demo = pd.read_csv(REF / "democracy.csv")

    df = load_countries()
    df = df.join(alignment(votes, CORE), on="iso3")
    later = alignment(votes, [LATER])[["alignment"]].rename(columns={"alignment": "later_alignment"})
    df = df.join(later, on="iso3")

    ip = ideal[ideal["year"] == IDEAL_YEAR].set_index("iso3")["ideal_point"]
    ip_base = ideal[ideal["year"] == BASE_YEAR].set_index("iso3")["ideal_point"]
    df["ideal_point"] = df["iso3"].map(ip)
    df["ideal_point_base"] = df["iso3"].map(ip_base)

    d = demo[demo["year"] == BASE_YEAR].set_index("iso3")
    df["democracy"] = df["iso3"].map(d["electoral_democracy"])
    df["region"] = df["iso3"].map(d["region"])
    df["post_soviet"] = df["iso3"].isin(POST_SOVIET).astype(int)

    voted = df[df["alignment"].notna() & ~df["iso3"].isin(EXCLUDE)]
    main = voted[(voted["arsenal"] >= MIN_ARSENAL) & voted["democracy"].notna() & voted["region"].notna()].copy()
    # Coefficients per 10 percentage points of Russian/US share, which reads more naturally
    for col in ("rus_share", "usa_share"):
        main[col + "_10"] = main[col] * 10

    models = {
        "bivariate": fit("alignment ~ rus_share_10", main),
        "controls": fit("alignment ~ rus_share_10 + democracy + C(region)", main),
        "full": fit("alignment ~ rus_share_10 + democracy + C(region) + usa_share_10 + post_soviet", main),
        "idealFull": fit("ideal_point ~ rus_share_10 + democracy + C(region) + usa_share_10 + post_soviet",
                         main.dropna(subset=["ideal_point"])),
        "fullWithoutBelarus": fit("alignment ~ rus_share_10 + democracy + C(region) + usa_share_10 + post_soviet",
                                  main[main["iso3"] != "BLR"]),
    }
    all_sizes = voted[voted["democracy"].notna() & voted["region"].notna()].copy()
    for col in ("rus_share", "usa_share"):
        all_sizes[col + "_10"] = all_sizes[col] * 10
    models["fullAllSizes"] = fit("alignment ~ rus_share_10 + democracy + C(region) + usa_share_10 + post_soviet", all_sizes)

    bands = []
    for lo, hi, label in BANDS:
        g = main[(main["rus_share"] >= lo) & (main["rus_share"] < hi)]
        bands.append({"label": label, "n": int(len(g)), "meanAlignment": _r(g["alignment"].mean()),
                      "shareNeverYes": _r((g["n_yes"] == 0).mean()), "shareAlwaysYes": _r((g["n_yes"] == g["n_cast"]).mean())})

    status_rows = []
    dep = main[main["rus_share"] >= 0.25]
    for s in ("staying", "diversifying", "moving_away", "few_orders"):
        g = dep[dep["russia_status"] == s]
        status_rows.append({"status": s, "n": int(len(g)), "meanAlignment": _r(g["alignment"].mean()),
                            "countries": g.sort_values("alignment")["name"].tolist()})

    spearman = main[["rus_share", "alignment"]].corr(method="spearman").iloc[0, 1]
    within_soviet = main[main["post_soviet"] == 0][["rus_share", "alignment"]].corr(method="spearman").iloc[0, 1]

    countries = []
    for r in voted.sort_values("rus_share", ascending=False).itertuples():
        countries.append({
            "iso3": r.iso3, "name": r.name, "rusShare": _r(r.rus_share), "usaShare": _r(r.usa_share),
            "rusShareNow": _r(r.rus_share_now), "arsenal": _r(r.arsenal, 1), "alignment": _r(r.alignment),
            "votes": {"yes": int(r.n_yes), "abstain": int(r.n_abstain), "no": int(r.n_no), "absent": int(r.n_absent)},
            "laterAlignment": _r(r.later_alignment), "idealPoint": _r(r.ideal_point),
            "democracy": _r(r.democracy), "region": r.region if isinstance(r.region, str) else None,
            "postSoviet": bool(r.post_soviet),
            "russiaStatus": r.russia_status if isinstance(r.russia_status, str) else None,
            "inSample": bool(r.iso3 in set(main["iso3"])),
        })

    later_votes = votes[votes["resolution"] == LATER].set_index("iso3")["vote"]
    return {
        "question": "Do militaries that depend on Russian-designed equipment vote with Russia at the UN?",
        "baseYear": BASE_YEAR, "idealYear": IDEAL_YEAR, "minArsenal": MIN_ARSENAL,
        "resolutions": [{"symbol": f"A/RES/{k}", "id": k, "date": meta.loc[k, "date"], "subject": meta.loc[k, "subject"],
                         "core": k in CORE, "matchesTally": bool(meta.loc[k, "matches_tally"])}
                        for k in meta.index if k in CORE + [LATER]],
        "sample": {"n": int(len(main)), "excluded": sorted(EXCLUDE)},
        "spearman": _r(spearman), "spearmanExcludingPostSoviet": _r(within_soviet),
        "bands": bands, "models": models, "byStatus": status_rows,
        "idealPointRussia": _r(ip.get("RUS")), "idealPointUSA": _r(ip.get("USA")),
        "later": {"resolution": LATER, "usaVote": later_votes.get("USA"), "russiaVote": later_votes.get("RUS")},
        "countries": countries,
    }


def main():
    logger.info("=== Step 6: Research — UN votes ===")
    result = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, separators=(",", ":"), ensure_ascii=False, allow_nan=False)   # NaN is not valid JSON
    m = result["models"]
    logger.info("n=%d  Spearman rho=%.2f (excluding post-Soviet %.2f)", result["sample"]["n"], result["spearman"],
                result["spearmanExcludingPostSoviet"])
    for k in ("bivariate", "controls", "full", "idealFull", "fullWithoutBelarus", "fullAllSizes"):
        t = m[k]["terms"]["rus_share_10"]
        logger.info("  %-20s per +10pp Russian share: %+.3f (95%% CI %+.3f to %+.3f, p=%.3f)  n=%d R2=%.2f",
                    k, t["coef"], t["ci"][0], t["ci"][1], t["p"], m[k]["n"], m[k]["r2"])
    for b in result["bands"]:
        logger.info("  %-12s n=%2d mean alignment %.2f  never voted yes %.0f%%", b["label"], b["n"], b["meanAlignment"] or 0,
                    (b["shareNeverYes"] or 0) * 100)
    for s in result["byStatus"]:
        logger.info("  %-12s n=%2d mean alignment %s", s["status"], s["n"], s["meanAlignment"])


if __name__ == "__main__":
    main()
