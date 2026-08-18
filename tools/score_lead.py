"""Deterministic scoring per docs/lead_scoring_criteria.md. See workflows/score_lead.md."""

import re

from tools.config import AREA_TIER_SCORES, BUDGET_SCORE_BANDS, FINANCING_SCORES, SCORE_BANDS, TIMELINE_SCORES

_TURKISH_MAP = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})


def score_lead(lead: dict, gap_fields: list, reference: dict):
    financing = _score_lookup(FINANCING_SCORES, lead.get("financing"), "financing" in gap_fields)
    timeline = _score_lookup(TIMELINE_SCORES, lead.get("timeline"), "timeline" in gap_fields)
    area_match = _score_area(lead.get("area"), reference, "area" in gap_fields)
    budget_fit = _score_budget(lead.get("budget"), "budget" in gap_fields)

    total = financing["score"] + timeline["score"] + budget_fit["score"] + area_match["score"]
    if total >= SCORE_BANDS["hot_min"]:
        label = "hot"
    elif total >= SCORE_BANDS["warm_min"]:
        label = "warm"
    else:
        label = "cold"

    return {
        "financing": financing,
        "timeline": timeline,
        "budget_fit": budget_fit,
        "area_match": area_match,
        "total_score": total,
        "label": label,
    }


def _score_lookup(table, answer, is_gap):
    if is_gap or not answer:
        return {"answer": answer or "(blank)", "score": 0}
    return {"answer": answer, "score": table.get(answer, 0)}


def _score_area(area, reference, is_gap):
    if is_gap or not area:
        return {"answer": area or "(blank)", "score": 0}
    tier = _match_area_tier(area, reference)
    return {"answer": f"{area} ({tier or 'unclassified'})", "score": AREA_TIER_SCORES.get(tier, 0)}


def _match_area_tier(area_text, reference):
    """Matches free-text area answers (e.g. "Istanbul, Basaksehir") against
    Reference Data district names. The Preferred area field is free text,
    not a locked dropdown, so submissions vary in capitalization and Turkish
    character usage ("Uskudar" vs "Üsküdar") - normalize both sides and
    match by containment rather than requiring an exact string match."""
    normalized = _normalize_area_text(area_text)
    if not normalized:
        return None
    for district, tier in reference.items():
        district_norm = _normalize_area_text(district)
        if district_norm and district_norm in normalized:
            return tier
    return None


def _normalize_area_text(s):
    s = (s or "").translate(_TURKISH_MAP).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _score_budget(raw_budget, is_gap):
    if is_gap:
        return {"answer": "(blank)", "score": 0}
    budget = _parse_number(raw_budget)
    if budget is None:
        return {"answer": f"{raw_budget} (unparseable)", "score": 0}
    score = 0
    for minimum, points in BUDGET_SCORE_BANDS:
        if budget >= minimum:
            score = points
            break
    return {"answer": f"{budget:,.0f}", "score": score}


def _parse_number(raw):
    """Handles plain numbers, thousands separators, currency symbols, and
    shorthand suffixes (100k -> 100000, 1.2m -> 1200000) - the kind of
    free-text a lead actually types into a "numeric" budget field."""
    if not raw:
        return None
    match = re.search(r"([\d,]*\.?\d+)\s*(k|m)?", str(raw).strip(), re.IGNORECASE)
    if not match:
        return None
    try:
        value = float(match.group(1).replace(",", ""))
    except ValueError:
        return None
    suffix = (match.group(2) or "").lower()
    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000
    return value
