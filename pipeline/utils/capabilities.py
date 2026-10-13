"""
Capability areas for dependency analysis.

Maps SIPRI's ~195 `weapon_desc` values to the areas a defence analyst would
ask about ("if supplier X stopped, what happens to our air defence?").
Differs from weapon_categories.py in that air defence is its own area rather
than being folded into missiles, and sensors/engines are separated out as
components that sit inside other platforms.

Rules are checked in order; the first match wins. `report_unmapped` lists any
description that only matched the catch-all so new SIPRI types get noticed.
"""

import re

# (capability, typical service life in years, rule)
# Service life drives the in-service estimate: equipment delivered more than
# this many years ago is assumed retired. Munitions are consumed or expire,
# so they get a short life; platforms last decades.
CAPABILITIES = [
    ("Sensors & components", 20, r"(?<!anti-)radar|sonar|engine\b|turbofan|turbojet|turboprop|gas turbine|electro-optical|"
                                 r"eo system|eo/radar|reconnaissance system|signals intelligence system|air-search system|"
                                 r"air refuel system|turret|chassis|reactor"),
    ("Helicopters",          30, r"helicopter"),
    # SIPRI spelled out its abbreviations in the March 2026 release (SAM ->
    # surface-to-air missile, ABM -> anti-ballistic missile); match both forms.
    ("Air defence",          25, r"\bsam\b|sam |/sam|abm|surface-to-air|anti-ballistic|anti-aircraft|air-defence|\bad system"),
    ("Naval",                35, r"(?<!anti-)submarine(?!-launched| sonar)|frigate|corvette|(?<!tank )destroyer|cruiser|"
                                 r"aircraft carrier|patrol (boat|ship)|missile boat|torp(e|d)o boat|torpdeo boat|gunboat|"
                                 r"landing (ship|craft)|amphibious|ampibious|"
                                 r"support ship|support craft|replenishment|^tanker$|mcm ship|minehunter|minesweeper|minelayer|"
                                 r"\btug\b|cargo (ship|craft)|transport (ship|craft)|survey ship|training ship|salvage ship|"
                                 r"signals intelligence ship|icebreaker|naval gun"),
    ("Missiles & munitions", 12, r"missile|torpedo|guided|loitering|one-way attack|naval mine|rocket launcher(?! )|"
                                 r"coastal defence system"),
    ("Combat aircraft",      30, r"fga|fighter|bomber|ground-attack|trainer/combat|\(armed\) trainer"),
    ("Support aircraft & drones", 30, r"aircraft|uav|drone|airship|satellite|ugv"),
    ("Armour",               35, r"tank|armoured|armored|infantry fighting vehicle|fire-support vehicle"),
    ("Artillery",            35, r"gun|mortar|multiple rocket launcher|howitzer"),
]

FALLBACK = ("Other", 20)

_COMPILED = [(name, life, re.compile(rule, re.IGNORECASE)) for name, life, rule in CAPABILITIES]

CAPABILITY_ORDER = [
    "Combat aircraft", "Air defence", "Missiles & munitions", "Naval", "Armour",
    "Helicopters", "Artillery", "Support aircraft & drones", "Sensors & components", "Other",
]
SERVICE_LIFE = {name: life for name, life, _ in CAPABILITIES} | {FALLBACK[0]: FALLBACK[1]}


def capability(weapon_desc) -> str:
    if not isinstance(weapon_desc, str):
        return FALLBACK[0]
    d = weapon_desc.strip()
    # Multiple rocket launchers are artillery, not munitions
    if re.search(r"multiple rocket launcher", d, re.IGNORECASE) and "naval" not in d.lower():
        return "Artillery"
    for name, _, rx in _COMPILED:
        if rx.search(d):
            return name
    return FALLBACK[0]


def report_unmapped(descs) -> list[str]:
    return sorted({d for d in descs if capability(d) == FALLBACK[0]})
