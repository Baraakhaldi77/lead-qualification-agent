"""Deterministic scoring per docs/lead_scoring_criteria.md. See workflows/score_lead.md."""

import re

from tools.config import AREA_TIER_SCORES, BUDGET_FIT_BANDS, FINANCING_SCORES, SCORE_BANDS, TIMELINE_SCORES


def score_lead(lead: dict, gap_fields: list, reference: dict):
    financing = _score_lookup(FINANCING_SCORES, lead.get("financing"), "financing" in gap_fields)
    timeline = _score_lookup(TIMELINE_SCORES, lead.get("timeline"), "timeline" in gap_fields)

    ref = reference.get((lead.get("area") or "").strip())
    area_match = _score_area(lead.get("area"), ref, "area" in gap_fields)
    budget_fit = _score_budget(lead.get("budget"), ref, "budget" in gap_fields)

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


def _score_area(area, ref, is_gap):
    if is_gap or not area:
        return {"answer": area or "(blank)", "score": 0}
    tier = ref["tier"] if ref else None
    return {"answer": area, "score": AREA_TIER_SCORES.get(tier, 0)}


def _score_budget(raw_budget, ref, is_gap):
    if is_gap:
        return {"answer": "(blank)", "score": 0}
    budget = _parse_number(raw_budget)
    if budget is None or not ref:
        return {"answer": f"{raw_budget} (no reference price for area)", "score": 0}
    typical = ref["typical_price"]
    pct_diff = abs(budget - typical) / typical if typical else 1
    if pct_diff <= BUDGET_FIT_BANDS["close_pct"]:
        score = 25
    elif pct_diff <= BUDGET_FIT_BANDS["negotiable_pct"]:
        score = 12
    else:
        score = 0
    return {"answer": f"{budget} vs {typical} typical", "score": score}


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
