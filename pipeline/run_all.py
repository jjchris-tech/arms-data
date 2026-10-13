"""
Run the full pipeline: acquire -> deals -> dependency profiles.

    python pipeline/run_all.py            # use the existing SIPRI download
    python pipeline/run_all.py --refresh  # re-download from SIPRI first
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from pipeline import checks, step1_acquire, step2_deals, step3_dependency


def main():
    step1_acquire.main(refresh="--refresh" in sys.argv)
    step2_deals.main()
    step3_dependency.main()
    checks.main()


if __name__ == "__main__":
    main()
