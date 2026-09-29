"""Deterministic reranking + scoring (no LLM).

Combines three sub-scores into a final relevance score out of 100:
  - similarity score (from pgvector cosine similarity)
  - keyword overlap score (query words vs title + scope)
  - specification match score (query numbers/units vs specifications)
"""
import re
import math

# Tokens that carry little meaning and would inflate keyword scores.
STOPWORDS = {
    "a", "an", "the", "for", "and", "or", "with", "of", "to", "in", "on",
    "off", "is", "are", "be", "it", "this", "that", "these", "those", "for",
    "use", "used", "using", "etc", "etc.", "per", "gsm", "including", "similar",
}

SPEC_PATTERNS = [
    # IP rating: IP65 -> value "65", unit "IP"
    (re.compile(r"\bIP\s*(\d{2})\b", re.I), "IP", lambda m: m.group(1)),
    # Wattage: 100W / 100 watt / 100watts
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:W|watt|watts)\b", re.I), "W", lambda m: float(m.group(1))),
    # Voltage: 230V
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:V|volt|volts)\b", re.I), "V", lambda m: float(m.group(1))),
    # Frequency: 50Hz
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:Hz|hertz)\b", re.I), "Hz", lambda m: float(m.group(1))),
    # Pressure: MPa
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:MPa|mpa)\b"), "MPa", lambda m: float(m.group(1))),
    # Temperature: °C / degree C
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:°C|deg(?:ree)?s?\s*C|celsius)\b", re.I), "°C", lambda m: float(m.group(1))),
    # Length mm
    (re.compile(r"(\d+(?:\.\d+)?)\s*mm\b"), "mm", lambda m: float(m.group(1))),
    # Length cm
    (re.compile(r"(\d+(?:\.\d+)?)\s*cm\b"), "cm", lambda m: float(m.group(1))),
    # Mass kg
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:kg|kilograms?)\b", re.I), "kg", lambda m: float(m.group(1))),
    # Mass g (careful)
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:gram|grams|g)\b(?!s)", re.I), "g", lambda m: float(m.group(1))),
    # GSM
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:gsm|g/m2|g/m²)\b", re.I), "gsm", lambda m: float(m.group(1))),
    # Lumen
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:lm|lumens?)\b", re.I), "lm", lambda m: float(m.group(1))),
    # Percentage
    (re.compile(r"(\d+(?:\.\d+)?)\s*%"), "%", lambda m: float(m.group(1))),
    # Litre
    (re.compile(r"(\d+(?:\.\d+)?)\s*(?:L|litres?|liters?)\b", re.I), "L", lambda m: float(m.group(1))),
]


def extract_specs(text):
    """Extract {unit, value, raw} from a query/document."""
    specs = []
    for pat, unit, fn in SPEC_PATTERNS:
        for m in pat.finditer(text):
            params = dict(pat.groupindex) if pat.groupindex else {}
            try:
                value = fn(m)
            except Exception:
                continue
            if unit == "IP":
                value = str(value).zfill(2)
            specs.append({"unit": unit, "value": str(value), "raw": m.group(0)})
    return specs


def tokenize(text):
    return [
        t for t in re.sub(r"[^a-zA-Z0-9\u0900-\u097F\s]", " ", text.lower()).split()
        if len(t) > 1 and t not in STOPWORDS
    ]


def keyword_overlap_score(query_tokens, standard):
    """Score 0-100 based on overlap of query words against title + scope."""
    title_toks = tokenize(standard["title"])
    scope_toks = tokenize(standard.get("scope") or "")
    combined = set(title_toks + scope_toks)
    if not combined:
        return 0.0
    query_set = set(query_tokens)
    hits = query_set & combined
    # Weight title matches more heavily
    title_hits = query_set & set(title_toks)
    base = (len(hits) / len(query_set)) * 80 if query_set else 0
    title_bonus = (len(title_hits) / len(query_set)) * 20 if query_set else 0
    return round(min(100.0, base + title_bonus), 1)


def specification_match_score(query_specs, standard):
    """Score 0-100 and return list of matched specification values.

    Returns (score, matched). Each matched entry is:
      {"value": <query raw value>, "field": <key>, "stored": <stored value>}
    """
    spec_obj = standard.get("specifications") or {}
    spec_items = []
    for k, v in spec_obj.items():
        spec_items.append((k, str(v)))

    value_to_field = {
        "W": ["watt", "power"],
        "V": ["voltage", "volt"],
        "Hz": ["frequency", "freq", "hz"],
        "MPa": ["strength", "mpa"],
        "mm": ["thickness", "diameter", "size", "mm", "dimension"],
        "°C": ["temp", "degc", "temperature"],
        "kg": ["weight", "mass"],
        "L": ["capacity", "litre", "volume"],
        "%": ["percent", "%"],
        "gsm": ["gsm", "grammage"],
        "IP": ["ip", "protection", "ingress"],
        "lm": ["lumen", "lm"],
        "cm": ["cm"],
        "g": ["g", "gram"],
    }

    matched = []
    # Maximum possible points = 30 per query spec (full match result)
    max_possible = len(query_specs) * 30
    score = 0.0

    for qs in query_specs:
        matched_any = False
        for key, val in spec_items:
            key_l = key.lower()
            val_l = val.lower()
            qval = qs["value"].lower()
            qraw = qs["raw"]
            fields = value_to_field.get(qs["unit"], [qs["unit"]])
            field_match = any(f in key_l for f in fields)
            if qval in val_l and field_match:
                score += 30.0
                matched.append({"value": qraw, "field": key, "stored": f"{key}: {val}"})
                matched_any = True
                break
            elif qval in val_l:
                score += 15.0
                matched.append({"value": qraw, "field": key, "stored": f"{key}: {val}"})
                matched_any = True
                break

    if max_possible == 0:
        return 0.0, []

    final = round(min(100.0, (score / max_possible) * 100.0), 1)
    return final, matched


def category_overlap_score(query_tokens, standard):
    """Score 0-100 based on overlap between query tokens and standard category/sub-category."""
    cat_text = (standard.get("category") or "") + " " + (standard.get("sub_category") or "")
    cat_toks = set(tokenize(cat_text))
    if not cat_toks or not query_tokens:
        return 0.0
    query_set = set(query_tokens)
    hits = query_set & cat_toks
    if hits:
        return round(min(100.0, (len(hits) / max(1, len(query_set))) * 100.0), 1)
    return 0.0


def qco_boost_score(standard):
    """Return 100.0 if standard has mandatory QCO, else 0.0."""
    return 100.0 if standard.get("is_qco_mandatory") else 0.0


def enhanced_combine_scores(similarity, keyword, spec, category=0.0, qco_boost=0.0):
    """
    Enhanced 5-part scoring as specified for MANAK-AI v2.0:
      - 40% embedding similarity
      - 25% specification overlap
      - 20% keyword overlap
      - 10% category overlap
      - 5% QCO boost
    """
    sim_100 = round(similarity * 100.0, 1)
    final = round(
        sim_100 * 0.40 + spec * 0.25 + keyword * 0.20 + category * 0.10 + qco_boost * 0.05, 1
    )
    return final, sim_100


def department_match_score(department, standard):
    """Score 100.0 if standard matches requested department, else 0.0."""
    if not department:
        return 0.0
    dep_req = department.lower().strip()
    s_dep = (standard.get("department") or "").lower()
    s_sec = (standard.get("sector") or "").lower()
    if dep_req in s_dep or s_dep in dep_req or dep_req in s_sec or s_sec in dep_req:
        return 100.0
    return 0.0


def related_standards_boost_score(standard, reference_standards=None):
    """Score 100.0 if standard is connected to any reference standard, else 0.0."""
    if not reference_standards:
        return 0.0
    ref_set = set(reference_standards)
    s_num = standard.get("is_number")
    s_refs = set(standard.get("normative_references") or []) | set(standard.get("related_standards") or [])
    if s_num in ref_set or bool(s_refs & ref_set):
        return 100.0
    return 0.0


def multisignal_rerank_score(
    similarity,
    keyword,
    spec,
    category=0.0,
    department=0.0,
    qco_boost=0.0,
    related_boost=0.0,
):
    """Multi-signal ranking combining:
      - 40% Semantic embedding similarity (primary signal)
      - 20% Specification match
      - 15% Keyword overlap
      - 10% Category match
      - 5% Department match
      - 5% QCO relevance
      - 5% Related standards boost
    Returns (final_score, similarity_100)
    """
    sim_100 = round(similarity * 100.0, 1)
    final = round(
        sim_100 * 0.40
        + spec * 0.20
        + keyword * 0.15
        + category * 0.10
        + department * 0.05
        + qco_boost * 0.05
        + related_boost * 0.05,
        1,
    )
    return min(100.0, final), sim_100


def combine_scores(similarity, keyword, spec):
    """
    similarity in [0,1] from cosine. Convert to a 0-100 weight and combine.
    Weights: similarity 40%, keyword 40%, specification 20%.
    Preserved for full backward compatibility with existing tests.
    """
    sim_100 = round(similarity * 100.0, 1)
    final = round(
        sim_100 * 0.40 + keyword * 0.40 + spec * 0.20, 1
    )
    return final, sim_100


