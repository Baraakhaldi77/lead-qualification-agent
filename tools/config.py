"""
Every tunable constant for the pipeline: sheet header names, scoring
tables (mirrors docs/lead_scoring_criteria.md), validation rules, email
copy. Change behavior here, not by hardcoding values in other tools.
"""

# --- Sheet header names ---
# Must match the Google Form's actual question titles (Form questions
# become these column headers verbatim - matched case/whitespace-insensitive,
# see tools/normalize_lead.py, but the words themselves must still match).
# These reflect the live form as built - if you rename a question, update
# the matching entry here too.

FIELD_HEADERS = {
    "timestamp": "Timestamp",
    "name": "Full Name",
    "phone": "Phone",
    "email": "Email",
    "budget": "Budget",
    "timeline": "Timeline",
    "financing": "Financing",
    "area": "Preferred area/s",
}

SCORE_HEADERS = {
    "financing_score": "Financing Score",
    "timeline_score": "Timeline Score",
    "budget_score": "Budget Score",
    "area_score": "Area Score",
    "total_score": "Total Score",
    "label": "Label",
    "flags": "Flags",
    "status": "Status",
    "email_sent": "Email Sent",
    "email_sent_at": "Email Sent At",
}

# --- Scoring tables (docs/lead_scoring_criteria.md is the source of
# truth — if they disagree, fix this file, don't reinterpret the rubric) ---

FINANCING_SCORES = {
    "Cash buyer": 30,
    "Pre-approved mortgage": 25,
    "Needs financing, not yet applied": 12,
    "Not sure / no answer": 0,
}

TIMELINE_SCORES = {
    "Immediately / within 30 days": 25,
    "1–3 months": 18,
    "3–6 months": 8,
    "Just researching / no timeline": 0,
}

AREA_TIER_SCORES = {
    "Active Listing": 20,
    "General Coverage": 10,
    # anything not found in Reference Data -> 0
}

BUDGET_FIT_BANDS = {
    "close_pct": 0.10,       # within ~10% -> 25 pts
    "negotiable_pct": 0.25,  # within ~25% -> 12 pts, else 0
}

SCORE_BANDS = {
    "hot_min": 80,
    "warm_min": 50,
    # below warm_min -> cold
}

REQUIRED_FIELDS = ["budget", "timeline", "financing", "area"]

# --- Validation ---

# Small demo blocklist - extend with your own known disposable domains.
DISPOSABLE_EMAIL_DOMAINS = [
    "mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com",
    "throwawaymail.com", "yopmail.com", "trashmail.com", "getnada.com",
]

PHONE_MIN_DIGITS = 7
PHONE_MAX_DIGITS = 15

# --- Email ---

DEFAULT_SENDER_NAME = "Riverside Realty"   # override via .env SENDER_NAME
DEFAULT_ADMIN_EMAIL = "admin@example.com"  # override via .env ADMIN_EMAIL

EMAIL_TEMPLATES = {
    "hot": {
        "subject": "Let's get you in to see {{area}} properties",
        "body": (
            "Hi {{name}},\n\n"
            "Thanks for reaching out about {{area}} - I'd like to get you viewing options right away. "
            "What's the best time to reach you today by phone?\n\n"
            "Talk soon"
        ),
    },
    "warm": {
        "subject": "Thanks for your interest, {{name}}",
        "body": (
            "Hi {{name}},\n\n"
            "Thanks for your interest in {{area}}. One of our agents will follow up with you within "
            "the next 1-2 business days to talk through what you're looking for.\n\n"
            "In the meantime, feel free to browse our current listings."
        ),
    },
    "cold": {
        "subject": "Thanks for stopping by, {{name}}",
        "body": (
            "Hi {{name}},\n\n"
            "Thanks for your interest in {{area}}. No pressure at all - feel free to browse listings "
            "whenever you're ready, and reach out any time you have questions."
        ),
    },
}
