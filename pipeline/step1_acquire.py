"""
Step 1: Download the SIPRI Arms Transfers trade register.

Skips the download if the file already exists; pass --refresh to fetch the
latest version (SIPRI updates the database once a year, usually in March).
"""

import base64
import logging
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# SIPRI backend API (used by the armstransfers.sipri.org web app)
SIPRI_API_BASE = "https://atbackend.sipri.org/api/p"


def download_transfers(refresh: bool = False) -> Path:
    """Download the full trade register as CSV. The API returns it base64-encoded."""
    if config.TRANSFERS_CSV.exists() and not refresh:
        logger.info("Using existing %s (pass --refresh to re-download)", config.TRANSFERS_CSV.name)
        return config.TRANSFERS_CSV

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading SIPRI trade register...")
    resp = requests.post(
        f"{SIPRI_API_BASE}/trades/trade-register-csv/",
        headers={"Content-Type": "application/json;charset=UTF-8"},
        json={"filters": [], "logic": "AND"},
        timeout=180,
    )
    resp.raise_for_status()
    csv_text = base64.b64decode(resp.json()["bytes"]).decode("latin-1")
    config.TRANSFERS_CSV.write_text(csv_text, encoding="utf-8")
    logger.info("Saved %s (%.1f MB)", config.TRANSFERS_CSV.name, len(csv_text) / 1e6)
    return config.TRANSFERS_CSV


def main(refresh: bool = False):
    logger.info("=== Step 1: Acquire ===")
    download_transfers(refresh)


if __name__ == "__main__":
    main(refresh="--refresh" in sys.argv)
