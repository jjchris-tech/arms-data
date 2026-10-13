"""
Step 2: Deal-level table with design origin.

Builds one row per SIPRI deal (the raw register is already deal-level; the
step 2 table expands each deal into one row per delivery year). Adds:

  - Successor-state codes (SUN -> RUS etc.) for buyer and seller
  - Design origin: who designed the system, not just who sold it
  - Order vs delivery timing, units/TIV outstanding, deal state
  - Flags: second-hand, licensed/local production, aid, component,
    non-state recipient, SIPRI '?' uncertainty markers
  - Planned delivery years parsed from comments where SIPRI gives them

Output: data/interim/deals.parquet
"""

import logging
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config
from pipeline.utils import sipri_parsers
from pipeline.utils.design_origin import assign_design_origin, successor
from pipeline.utils.capabilities import capability

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DEALS_PARQUET = config.INTERIM_DIR / "deals.parquet"

# A deal with undelivered units counts as open only if it has seen activity
# (order or delivery) within this many years of the data's last year.
# Older undelivered deals are usually cancelled or unrecorded.
OPEN_WINDOW_YEARS = 5

_COMPONENT_RE = re.compile(
    r"engine|turbofan|turbojet|turboprop|gas turbine|radar|sonar|turret|fire.control|"
    r"electro-optical|eo system|eo/radar|sensor|reactor",
    re.IGNORECASE,
)
_LICENSED_RE = re.compile(r"licen[cs]|assembl", re.IGNORECASE)
_AID_RE = re.compile(r"\baid\b|gift", re.IGNORECASE)
_CANCEL_RE = re.compile(r"cancel", re.IGNORECASE)
_PLANNED_RE = re.compile(
    r"deliver(?:y|ies)\s+(?:planned|expected|scheduled)\s+(?:for\s+|by\s+|from\s+|in\s+)?"
    r"(\d{4})(?:\s*-\s*(\d{4}))?",
    re.IGNORECASE,
)


def _planned(comment) -> tuple[float, float]:
    if not isinstance(comment, str):
        return (np.nan, np.nan)
    m = _PLANNED_RE.search(comment)
    if not m:
        return (np.nan, np.nan)
    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else start
    return (start, end)


def build_deals() -> pd.DataFrame:
    raw = sipri_parsers.parse_transfers_csv()
    raw = raw[raw["buyer"].notna() & raw["designation"].notna()].reset_index(drop=True)
    df = raw.copy()
    df.insert(0, "deal_id", np.arange(len(df)))

    # Successor states and recipient type
    df["buyer_successor_iso3"] = df["buyer_iso3"].map(successor)
    df["buyer_is_state"] = df["buyer_iso3"].notna() & ~df["buyer"].str.endswith("*")

    # Delivery timing
    years = df["delyears_list"].apply(lambda ys: sorted(ys) if isinstance(ys, list) else [])
    df["first_delivery"] = years.map(lambda ys: ys[0] if ys else np.nan)
    df["last_delivery"] = years.map(lambda ys: ys[-1] if ys else np.nan)
    df["n_delivery_years"] = years.map(len)
    df["delivery_years"] = years.map(lambda ys: ";".join(str(int(y)) for y in ys))
    df["order_to_delivery_lag"] = df["first_delivery"] - df["order_year"]
    df = df.drop(columns=["delyears_list"])

    planned = df["comments"].map(_planned)
    df["planned_delivery_start"] = planned.map(lambda p: p[0])
    df["planned_delivery_end"] = planned.map(lambda p: p[1])

    # Units and TIV outstanding
    delivered = df["num_delivered"].fillna(0)
    df["units_outstanding"] = (df["num_ordered"] - delivered).clip(lower=0)
    df["tiv_outstanding"] = df["units_outstanding"] * df["tiv_unit"]

    # Flags
    comments = df["comments"].fillna("")
    df["is_second_hand"] = df["status"].str.startswith("Second hand", na=False)
    df["is_licensed"] = comments.str.contains(_LICENSED_RE)
    df["is_aid"] = comments.str.contains(_AID_RE)
    df["mentions_cancellation"] = comments.str.contains(_CANCEL_RE)
    df["is_component"] = df["weapon_desc"].fillna("").str.contains(_COMPONENT_RE)
    df["capability"] = df["weapon_desc"].map(capability)

    # Deal state
    data_year = int(np.nanmax(df["last_delivery"]))
    last_activity = df[["order_year", "last_delivery"]].max(axis=1)
    state = np.select(
        [
            df["num_ordered"].isna(),
            df["units_outstanding"] <= 0,
            df["mentions_cancellation"],
            last_activity >= data_year - OPEN_WINDOW_YEARS,
        ],
        ["unknown", "complete", "partly_cancelled", "open"],
        default="stalled",
    )
    df["deal_state"] = state
    # Only open deals carry a backlog; stalled/cancelled remainders are unknowable
    df["tiv_outstanding"] = np.where(
        state == "open", df["tiv_outstanding"], np.where(state == "complete", 0.0, np.nan)
    )

    df = assign_design_origin(df)
    df["data_year"] = data_year
    return df


def report(df: pd.DataFrame) -> None:
    """Log sanity checks so the attribution can be eyeballed on each run."""
    logger.info("Deals: %d | data year: %d", len(df), df["data_year"].iloc[0])
    logger.info("Deal states: %s", df["deal_state"].value_counts().to_dict())
    logger.info("Origin method: %s", df["origin_method"].value_counts().to_dict())
    for col in ["order_year_uncertain", "num_ordered_uncertain", "num_delivered_uncertain"]:
        if col in df:
            logger.info("  %s: %.0f%%", col, df[col].mean() * 100)

    diff = df[df["design_origin_iso3"] != df["seller_successor_iso3"]]
    logger.info("Deals where design origin != seller: %d (%.1f%%)", len(diff), len(diff) / len(df) * 100)
    pairs = diff.groupby(["seller", "design_origin_iso3"]).size().nlargest(12)
    for (seller, origin), n in pairs.items():
        logger.info("  %-28s -> %s  (%d deals)", seller, origin, n)

    open_ = df[df["deal_state"] == "open"]
    logger.info(
        "Open deals: %d, TIV outstanding %.0f, %d with planned delivery dates",
        len(open_), open_["tiv_outstanding"].sum(), open_["planned_delivery_start"].notna().sum(),
    )


def main():
    logger.info("=== Step 2: Deal table + design origin ===")
    df = build_deals()
    report(df)
    config.INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DEALS_PARQUET, index=False)
    logger.info("Wrote %s (%d rows, %d columns)", DEALS_PARQUET.name, len(df), df.shape[1])


if __name__ == "__main__":
    main()
