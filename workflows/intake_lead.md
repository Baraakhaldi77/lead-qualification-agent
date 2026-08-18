# Workflow: Intake Lead

## Objective

Turn a raw Google Sheet row (from the linked Google Form) into a standardized lead object the rest of the pipeline can work with.

## Required Inputs

- The Leads sheet's header row (column names, read fresh each run — don't assume fixed positions)
- The raw row of values for the lead being processed

## Tools

- `tools/normalize_lead.py` (`normalize_row`) — maps header names to the standard field set: `name`, `phone`, `email`, `budget`, `timeline`, `financing`, `area`. Missing/short rows (an optional question left blank, trailing cells absent) are treated as empty string, not an error.

## Output

A lead dict with all seven fields present (empty string if not answered).

## Edge Cases

- A row shorter than the header row (skipped optional question) → missing fields become `""`, not a crash.
- A header name in the sheet that doesn't match `tools/config.py`'s `FIELD_HEADERS` → that field reads as `""`; this usually means the Form question wording drifted from the header the pipeline expects — fix the mismatch, don't guess which column is which.
- This step never validates or scores — that's `validate_lead.md` and `score_lead.md`. Intake only reshapes data.
