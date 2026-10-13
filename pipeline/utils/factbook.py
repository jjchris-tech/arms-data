"""
Parse the CIA World Factbook's "Military equipment inventories and acquisitions"
text into structured origin claims.

Each entry follows a loose house style:
  "the military's inventory consists of mostly Russian/Soviet-origin equipment
   along with smaller quantities from China and Israel; ... (2025)"

From that we extract:
  primary   — origins the text says dominate ("mostly", "largely", "the leading
              provider", or listed before an "along with smaller ..." contrast)
  mentioned — every origin named anywhere
  mode      — 'dominant' if the text names a main source, 'mixed' if it only
              lists suppliers, 'none' if it names no origins
  domestic  — the text says much of the inventory is domestically produced

Generic terms are kept as blocs: "Western" -> WESTERN, "European" -> EUROPEAN.
"""

import html
import re

WESTERN = "WESTERN"
EUROPEAN = "EUROPEAN"

# Longest/most specific patterns first so "South Korea" wins over "Korea".
_ORIGIN_PATTERNS = [
    (r"(former )?Soviet(-era|-origin| Union)?|USSR|Warsaw Pact", "RUS"),
    (r"Russian?|Russia's", "RUS"),
    (r"North Korean?", "PRK"),
    (r"South Korean?|Republic of Korea", "KOR"),
    (r"South African?", "ZAF"),
    (r"United States|U\.S\.|\bUS\b|American", "USA"),
    (r"United Kingdom|\bUK\b|British|Britain", "GBR"),
    (r"United Arab Emirates|\bUAE\b|Emirati", "ARE"),
    (r"Saudi( Arabian?)?", "SAU"),
    (r"Chinese|China(?!-)", "CHN"),
    (r"French|France", "FRA"),
    (r"German[y]?", "DEU"),
    (r"Israeli?", "ISR"),
    (r"Italian|Italy", "ITA"),
    (r"Spanish|Spain", "ESP"),
    (r"T[uü]rkiye|Turkish|Turkey", "TUR"),
    (r"Ukrainian?", "UKR"),
    (r"Belarus(ian)?", "BLR"),
    (r"Brazil(ian)?", "BRA"),
    (r"Indian?\b", "IND"),
    (r"Pakistani?", "PAK"),
    (r"Swed(en|ish)", "SWE"),
    (r"Swiss|Switzerland", "CHE"),
    (r"Dutch|Netherlands", "NLD"),
    (r"Belgi(um|an)", "BEL"),
    (r"Canad(a|ian)", "CAN"),
    (r"Australian?", "AUS"),
    (r"Czech(ia| Republic)?|Czechoslovak(ia|ian)?", "CZE"),
    (r"Pol(and|ish)", "POL"),
    (r"Bulgarian?", "BGR"),
    (r"Romanian?", "ROU"),
    (r"Serbian?|Yugoslav(ia|ian)?", "SRB"),
    (r"Iranian?", "IRN"),
    (r"Egypt(ian)?", "EGY"),
    (r"Japan(ese)?", "JPN"),
    (r"Taiwan(ese)?", "TWN"),
    (r"Singapore(an)?", "SGP"),
    (r"Jordan(ian)?", "JOR"),
    (r"Fin(land|nish)", "FIN"),
    (r"Norw(ay|egian)", "NOR"),
    (r"Den(mark|ish)", "DNK"),
    (r"Austrian?(?!a)", "AUT"),
    (r"Portug(al|uese)", "PRT"),
    (r"Gree(ce|k)", "GRC"),
    (r"Hungar(y|ian)", "HUN"),
    (r"Slovak(ia)?", "SVK"),
    (r"Sloven(ia|ian)", "SVN"),
    (r"Croatian?", "HRV"),
    (r"Argentin(a|e|ian)", "ARG"),
    (r"Chile(an)?", "CHL"),
    (r"Indonesian?", "IDN"),
    (r"Malaysian?", "MYS"),
    (r"Thai(land)?", "THA"),
    (r"Georgian?", "GEO"),
    (r"Kazakh(stan)?", "KAZ"),
    (r"Azerbaijan(i)?", "AZE"),
    (r"Cuban?", "CUB"),
    (r"Libyan?", "LBY"),
    (r"Algerian?", "DZA"),
    (r"Morocc(o|an)", "MAR"),
    (r"Nigerian?", "NGA"),
    (r"Qatar(i)?", "QAT"),
    (r"Kuwait(i)?", "KWT"),
    (r"Oman(i)?", "OMN"),
    (r"Mexic(o|an)", "MEX"),
    (r"Colombian?", "COL"),
    (r"Estonian?", "EST"),
    (r"Lithuanian?", "LTU"),
    (r"Latvian?", "LVA"),
    (r"Western|NATO", WESTERN),
    (r"European|Europe", EUROPEAN),
]
_ORIGIN_RX = [(re.compile(r"\b(?:" + p + r")\b"), iso) for p, iso in _ORIGIN_PATTERNS]

_DOMINANCE = re.compile(
    r"\b(mostly|largely|primarily|predominantly|principally|mainly|chiefly|majority|bulk|most of|overwhelmingly)\b",
    re.IGNORECASE,
)
# Phrases after which origins are secondary
_CONTRAST = re.compile(
    r"\b(along with|alongside|with (a )?smaller|smaller|as well as|in addition|plus|and some|some (more )?modern|"
    r"and other|other suppliers|other countries)\b",
    re.IGNORECASE,
)
_LEADING = re.compile(
    r"(?P<pre>[^;]*?)\b(is|are|has been|have been|remains?|continues? to be) (the |its )?"
    r"(leading|main|largest|primary|principal|top|biggest|key) (foreign )?(provider|supplier|source)",
    re.IGNORECASE,
)
_PROVIDED_BY = re.compile(r"\b(largely|mostly|primarily|mainly) (provided|supplied|donated) by\b(?P<post>[^;]*)", re.IGNORECASE)
_DOMESTIC = re.compile(r"domestic(ally)?[- ]produc|indigenous|locally produced|own defen[cs]e industry", re.IGNORECASE)
_YEAR = re.compile(r"\((\d{4})\)\s*$")


def _origins(text: str, exclude: str | None) -> list[str]:
    found = []
    for rx, iso in _ORIGIN_RX:
        for m in rx.finditer(text):
            found.append((m.start(), iso))
    seen, out = set(), []
    for _, iso in sorted(found):
        if iso != exclude and iso not in seen:
            seen.add(iso)
            out.append(iso)
    return out


_LIST = re.compile(r"\b(range of|variety of|several|a number of|number of|various|including|include[sd]?|such as)\b", re.IGNORECASE)


def _first_origin_pos(text: str) -> int | None:
    positions = [m.start() for rx, _ in _ORIGIN_RX for m in rx.finditer(text)]
    return min(positions) if positions else None


def _origins_after_list_check(seg: str, exclude: str | None) -> list[str]:
    """Origins in `seg`, or [] if they are introduced as a list of many suppliers."""
    pos = _first_origin_pos(seg)
    if pos is None:
        return []
    marker = _LIST.search(seg)
    if marker and marker.start() < pos:
        return []
    return _origins(seg, exclude)


def parse(text: str, self_iso3: str | None = None) -> dict:
    """Structured origin claims from one Factbook entry. `self_iso3` is ignored as an origin."""
    t = html.unescape(text or "").strip()
    year_match = _YEAR.search(t)
    clauses = [c.strip() for c in t.split(";") if c.strip()]
    first = clauses[0] if clauses else ""

    mentioned = _origins(t, self_iso3)
    primary, evidence = [], []

    # 1. "X is the leading provider" / "largely provided by X" anywhere in the text
    for clause in clauses:
        m = _LEADING.search(clause)
        if m:
            got = _origins(m.group("pre"), self_iso3)
            if got:
                primary += got[:1] if len(got) > 1 else got
                evidence.append(clause)
        m = _PROVIDED_BY.search(clause)
        if m:
            got = _origins(m.group("post"), self_iso3)
            if got:
                primary += got
                evidence.append(clause)

    # 2. Any clause with a dominance word ("mostly", "the majority of ... are from X"),
    #    unless the origins come as a list ("mostly older arms from a range of countries, including ...")
    for clause in clauses:
        dom = _DOMINANCE.search(clause)
        if not dom:
            continue
        seg = clause[dom.start():]
        contrast = _CONTRAST.search(seg)
        seg = seg[: contrast.start()] if contrast else seg
        got = _origins_after_list_check(seg, self_iso3)
        if got:
            primary += got
            evidence.append(clause)

    # 3. First clause: origins listed before an "along with a smaller ..." contrast
    contrast = _CONTRAST.search(first)
    head = first[: contrast.start()] if contrast else first
    if contrast and re.search(r"smaller|some", contrast.group(0), re.IGNORECASE):
        got = _origins_after_list_check(head, self_iso3)
        if got:
            primary += got
            evidence.append(first)

    primary = list(dict.fromkeys(primary))
    domestic = bool(_DOMESTIC.search(head)) or bool(re.search(r"mostly domestic|largely domestic|primarily domestic", t, re.I))
    return {
        "mode": "dominant" if primary else ("mixed" if mentioned else "none"),
        "primary": primary,
        "mentioned": mentioned,
        "domestic": domestic,
        "year": int(year_match.group(1)) if year_match else None,
        "evidence": evidence[0] if evidence else None,
    }
