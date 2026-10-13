"""
Map SIPRI country names to ISO 3166-1 alpha-3 codes.

Uses country_converter for fuzzy matching with manual overrides
for SIPRI-specific names that don't resolve automatically.
"""

import logging
from functools import lru_cache

import country_converter as coco

logger = logging.getLogger(__name__)
# country_converter logs every miss itself; we log each unresolved name once below
logging.getLogger("country_converter").setLevel(logging.ERROR)

# Manual overrides for names that country_converter can't resolve
SIPRI_TO_ISO3_OVERRIDES = {
    # Korean peninsula
    "Korea South": "KOR",
    "Korea, South": "KOR",
    "South Korea": "KOR",
    "Korea North": "PRK",
    "Korea, North": "PRK",
    "North Korea": "PRK",
    # Middle East / Africa
    "UAE": "ARE",
    "Congo DR": "COD",
    "Congo Republic": "COG",
    "Congo, Rep.": "COG",
    "Congo, Dem. Rep.": "COD",
    "Cote d'Ivoire": "CIV",
    "Ivory Coast": "CIV",
    "Cabo Verde": "CPV",
    "Cape Verde": "CPV",
    "Eswatini": "SWZ",
    "Swaziland": "SWZ",
    "Burma": "MMR",
    "Myanmar": "MMR",
    "Timor Leste": "TLS",
    "Timor-Leste": "TLS",
    "East Timor": "TLS",
    # Europe
    "Czechia": "CZE",
    "Czech Republic": "CZE",
    "North Macedonia": "MKD",
    "Macedonia (FYROM)": "MKD",
    "Bosnia-Herzegovina": "BIH",
    "Bosnia and Herzegovina": "BIH",
    # Former states
    "Soviet Union": "SUN",
    "USSR": "SUN",
    "Czechoslovakia": "CSK",
    "Yugoslavia": "YUG",
    "Serbia and Montenegro": "SCG",
    "East Germany (GDR)": "DDR",
    "South Vietnam": "VNM",  # Map to modern Vietnam
    # Misc
    "Palestine": "PSE",
    "Taiwan": "TWN",
    "Chinese Taipei": "TWN",
    "Hong Kong": "HKG",
    "Macau": "MAC",
    "Kosovo": "XKX",
    "Brunei": "BRN",
    # Common SIPRI abbreviations
    "USA": "USA",
    "UK": "GBR",
    "United Kingdom": "GBR",
    "Russia": "RUS",
    "China": "CHN",
    "China, P.R.": "CHN",
    "Iran": "IRN",
    "Syria": "SYR",
    "Venezuela": "VEN",
    "Bolivia": "BOL",
    "Tanzania": "TZA",
    "Vietnam": "VNM",
    "Viet Nam": "VNM",
    "Laos": "LAO",
}

# Region/group names that appear in SIPRI data but are not countries
NON_COUNTRY_NAMES = {
    "Africa", "North Africa", "Sub-Saharan Africa",
    "Americas", "Central America and the Caribbean", "South America", "North America",
    "Asia & Oceania", "Central Asia", "East Asia", "Oceania",
    "South Asia", "South East Asia",
    "Europe", "Central Europe", "Eastern Europe", "Western Europe",
    "Middle East",
    "World", "World total",
}

_converter = coco.CountryConverter()


@lru_cache(maxsize=None)
def sipri_name_to_iso3(name: str) -> str | None:
    """
    Convert a SIPRI country name to ISO3 code.

    Returns None if the name cannot be resolved (logs a warning).
    """
    if not name or not isinstance(name, str):
        return None

    name_stripped = name.strip()

    if name_stripped in NON_COUNTRY_NAMES:
        return None

    # Check overrides first
    if name_stripped in SIPRI_TO_ISO3_OVERRIDES:
        return SIPRI_TO_ISO3_OVERRIDES[name_stripped]

    # Try country_converter
    result = _converter.convert(names=name_stripped, to="ISO3", not_found=None)
    if result is not None:
        # country_converter may return a list for ambiguous matches
        if isinstance(result, list):
            result = result[0] if result else None
        # It may also return the input string if not found
        if isinstance(result, str) and len(result) == 3 and result.isalpha():
            return result

    logger.warning("Could not resolve country name to ISO3: '%s'", name_stripped)
    return None

