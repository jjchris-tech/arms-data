"""
Paths for the arms dependency pipeline. All relative to the project root.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

RAW_DIR = PROJECT_ROOT / "data" / "raw"
INTERIM_DIR = PROJECT_ROOT / "data" / "interim"
APP_DATA_DIR = PROJECT_ROOT / "dashboard" / "public" / "data"

# SIPRI Arms Transfers trade register (downloaded by step 1)
TRANSFERS_CSV = RAW_DIR / "sipri-trade-register.csv"
