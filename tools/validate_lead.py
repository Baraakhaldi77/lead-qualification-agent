"""Pre-score data gate. See workflows/validate_lead.md and docs/lead_scoring_criteria.md."""

import re

from tools.config import DISPOSABLE_EMAIL_DOMAINS, PHONE_MAX_DIGITS, PHONE_MIN_DIGITS, REQUIRED_FIELDS


def validate_submission(lead: dict):
    flags = []

    if not _is_valid_phone(lead.get("phone", "")):
        flags.append("invalid_contact")
    if _is_disposable_email(lead.get("email", "")) and "invalid_contact" not in flags:
        flags.append("invalid_contact")

    missing = [f for f in REQUIRED_FIELDS if not str(lead.get(f, "")).strip()]
    if missing:
        flags.append("incomplete_submission:" + ",".join(missing))

    return (len(flags) == 0, flags)


def _is_valid_phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    return PHONE_MIN_DIGITS <= len(digits) <= PHONE_MAX_DIGITS


def _is_disposable_email(raw):
    if not raw or "@" not in raw:
        return bool(raw)  # non-empty but malformed shape -> treat as bad
    domain = raw.strip().lower().split("@")[-1]
    return domain in DISPOSABLE_EMAIL_DOMAINS
