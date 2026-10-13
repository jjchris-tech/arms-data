"""
Parser for the SIPRI Arms Transfers trade register CSV and its formatting quirks.
"""

import re
import logging
import pandas as pd

from . import country_codes
from .. import config

logger = logging.getLogger(__name__)

# Number of preamble lines in the SIPRI trade register CSV
# Lines 1-10 are notes/metadata, line 11 is blank, line 12 is the header
TRANSFERS_SKIP_ROWS = 11


def parse_delyears(delyears_str) -> list[int]:
    """
    Parse SIPRI delivery years string into a list of integer years.

    Handles formats:
      - "2015-2018" -> [2015, 2016, 2017, 2018]
      - "2020" -> [2020]
      - "(2022)" -> [2022]  (parenthesized = uncertain)
      - "2015; 2017; 2019" -> [2015, 2017, 2019]
      - "2015-2017; 2020" -> [2015, 2016, 2017, 2020]
    """
    if not delyears_str or not isinstance(delyears_str, str):
        return []

    s = delyears_str.replace("(", "").replace(")", "").strip()
    if not s:
        return []

    years = set()
    parts = [p.strip() for p in s.split(";")]
    for part in parts:
        if not part:
            continue
        range_match = re.match(r"(\d{4})\s*[-\u2013]\s*(\d{4})", part)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            years.update(range(start, end + 1))
        else:
            found = re.findall(r"\d{4}", part)
            years.update(int(y) for y in found)

    return sorted(years)


def parse_transfers_csv(filepath=None) -> pd.DataFrame:
    """
    Parse the SIPRI trade register CSV file.

    The CSV from the SIPRI API has this structure:
      - Lines 1-10: preamble notes
      - Line 11: blank
      - Line 12: header row:
        Recipient, Supplier, Year of order, [?], Number ordered, [?],
        Weapon designation, Weapon description, Number delivered, [?],
        Year(s) of delivery, status, Comments,
        SIPRI TIV per unit, SIPRI TIV for total order,
        SIPRI TIV of delivered weapons

    Returns a cleaned DataFrame with standardized column names.
    """
    filepath = filepath or config.TRANSFERS_CSV

    # Read with the correct number of skiprows
    df = pd.read_csv(
        filepath,
        encoding="utf-8",
        skiprows=TRANSFERS_SKIP_ROWS,
        on_bad_lines="warn",
    )

    # Standardize column names
    col_map = {
        "Recipient": "buyer",
        "Supplier": "seller",
        "Year of order": "order_year",
        "Number ordered": "num_ordered",
        "Weapon designation": "designation",
        "Weapon description": "weapon_desc",
        "Number delivered": "num_delivered",
        "Deliveries in the Year Range": "num_delivered",   # renamed in the March 2026 release
        "Year(s) of delivery": "delyears",
        "status": "status",
        "Comments": "comments",
        "SIPRI TIV per unit": "tiv_unit",
        "SIPRI TIV for total order": "tiv_order",
        "SIPRI TIV of delivered weapons": "tiv_delivered",
    }

    # Map known columns, drop unnamed spacer columns
    new_cols = {}
    for orig_col in df.columns:
        stripped = orig_col.strip()
        if stripped in col_map:
            new_cols[orig_col] = col_map[stripped]
    df = df.rename(columns=new_cols)

    # The three unlabelled spacer columns hold SIPRI's '?' uncertainty markers
    # for the column before them (order year, number ordered, number delivered)
    flag_map = {"": "order_year_uncertain", ".1": "num_ordered_uncertain", ".2": "num_delivered_uncertain"}
    for orig_col in list(df.columns):
        flag = flag_map.get(str(orig_col).strip())
        if flag:
            df[flag] = df[orig_col].astype(str).str.strip().eq("?")

    # Drop unnamed/spacer columns
    drop_cols = [c for c in df.columns
                 if str(c).startswith("Unnamed") or c.strip() == "" or c.strip().startswith(".")]
    df = df.drop(columns=drop_cols, errors="ignore")

    # Strip whitespace from string columns
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        df[col] = df[col].str.strip()

    # Convert numeric columns
    for col in ["order_year", "num_ordered", "num_delivered", "tiv_unit", "tiv_order", "tiv_delivered"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Parse delivery years
    if "delyears" in df.columns:
        df["delyears_list"] = df["delyears"].apply(parse_delyears)

    # Map country names to ISO3
    if "buyer" in df.columns:
        df["buyer_iso3"] = df["buyer"].apply(country_codes.sipri_name_to_iso3)
    if "seller" in df.columns:
        df["seller_iso3"] = df["seller"].apply(country_codes.sipri_name_to_iso3)

    # Drop the original 'delyears' text column (keep parsed list)
    logger.info(
        "Parsed transfers: %d rows, %d unique buyers, %d unique sellers",
        len(df),
        df["buyer_iso3"].nunique() if "buyer_iso3" in df.columns else 0,
        df["seller_iso3"].nunique() if "seller_iso3" in df.columns else 0,
    )

    return df
