"""Intake: raw Sheet row -> standardized lead object. See workflows/intake_lead.md."""

from tools.config import FIELD_HEADERS


def normalize_row(headers, row):
    # Match header names case/whitespace-insensitively so a trailing space or
    # a capitalization difference in the Form's actual question title doesn't
    # silently drop a field to blank - the words themselves must still match
    # tools/config.py's FIELD_HEADERS.
    normalized_index = {_norm(h): i for i, h in enumerate(headers)}

    lead = {}
    for field, header in FIELD_HEADERS.items():
        idx = normalized_index.get(_norm(header))
        lead[field] = row[idx] if idx is not None and idx < len(row) else ""
    return lead


def _norm(header):
    return " ".join(header.split()).strip().casefold()
