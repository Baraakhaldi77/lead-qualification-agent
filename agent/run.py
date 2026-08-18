"""
The Agent layer for Phase 1: a thin, deterministic orchestrator that runs
workflows/intake_lead.md -> validate_lead.md -> score_lead.md ->
dispatch_email.md, in that fixed order, for every unprocessed row in the
Leads sheet. No LLM call - every input this phase handles is structured,
per CLAUDE.md's "prefer deterministic code wherever the input is
structured" rule. Run as a scheduled poller (see README.md for cron /
Task Scheduler setup), not a webhook - no hosting required.

Run manually with `python -m agent.run --once` for a single pass (testing).
"""

import argparse
import datetime
import json
import os
import time
import traceback
from pathlib import Path

from dotenv import load_dotenv

from tools import config, dispatch_email, gmail_client, normalize_lead, score_lead as score_lead_tool
from tools import sheets_client, validate_lead
from tools.google_auth import get_credentials

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

SPREADSHEET_ID = os.environ["GOOGLE_SHEET_ID"]
LEADS_SHEET = os.environ.get("LEADS_SHEET_NAME", "Form Responses 1")
REFERENCE_SHEET = os.environ.get("REFERENCE_SHEET_NAME", "Reference Data")
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "120"))
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", config.DEFAULT_ADMIN_EMAIL)
SENDER_NAME = os.environ.get("SENDER_NAME", config.DEFAULT_SENDER_NAME)

TMP_DIR = PROJECT_ROOT / ".tmp"

H = config.SCORE_HEADERS


def process_once():
    creds = get_credentials()
    sheets = sheets_client.build_sheets_service(creds)
    gmail = gmail_client.build_gmail_service(creds)

    # Only the score/status columns are ours to create - FIELD_HEADERS come
    # natively from the Form and must never be auto-recreated here (doing so
    # previously produced duplicate blank columns when wording didn't match
    # exactly).
    headers = sheets_client.ensure_headers(sheets, SPREADSHEET_ID, LEADS_SHEET, list(H.values()))
    _, rows = sheets_client.read_sheet(sheets, SPREADSHEET_ID, LEADS_SHEET)
    reference = sheets_client.read_reference_data(sheets, SPREADSHEET_ID, REFERENCE_SHEET)

    status_idx = headers.index(H["status"])

    for i, row in enumerate(rows):
        row_index = i + 2  # 1-indexed sheet row, +1 for header row
        status = row[status_idx] if status_idx < len(row) else ""
        if status:
            continue  # already processed - state lives in the sheet, not in this process

        try:
            _process_row(sheets, gmail, headers, row, row_index, reference)
        except Exception:
            # One bad row must not stop the batch. Row's Status stays blank,
            # so it's retried next pass.
            print(f"[agent.run] row {row_index} failed:\n{traceback.format_exc()}")


def _process_row(sheets, gmail, headers, row, row_index, reference):
    lead = normalize_lead.normalize_row(headers, row)
    _snapshot(row_index, lead)

    valid, flags = validate_lead.validate_submission(lead)

    if not valid:
        _handle_flagged(sheets, gmail, headers, lead, flags, row_index, reference)
        return

    score = score_lead_tool.score_lead(lead, [], reference)
    subject, body = dispatch_email.compose_tier_email(lead, score["label"])
    gmail_client.send_email(gmail, lead["email"], subject, body, SENDER_NAME)

    updates = _score_updates(score)
    updates[H["status"]] = "scored"
    updates[H["email_sent"]] = "yes"
    updates[H["email_sent_at"]] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    sheets_client.write_row_updates(sheets, SPREADSHEET_ID, LEADS_SHEET, row_index, headers, updates)


def _handle_flagged(sheets, gmail, headers, lead, flags, row_index, reference):
    invalid_contact = "invalid_contact" in flags
    updates = {H["flags"]: "; ".join(flags), H["status"]: "needs_review"}

    if not invalid_contact:
        gap_fields = _extract_gap_fields(flags)
        score = score_lead_tool.score_lead(lead, gap_fields, reference)
        updates.update(_score_updates(score))

    subject, body = dispatch_email.compose_admin_alert(lead, flags)
    gmail_client.send_email(gmail, ADMIN_EMAIL, subject, body, SENDER_NAME)

    sheets_client.write_row_updates(sheets, SPREADSHEET_ID, LEADS_SHEET, row_index, headers, updates)


def _score_updates(score):
    return {
        H["financing_score"]: score["financing"]["score"],
        H["timeline_score"]: score["timeline"]["score"],
        H["budget_score"]: score["budget_fit"]["score"],
        H["area_score"]: score["area_match"]["score"],
        H["total_score"]: score["total_score"],
        H["label"]: score["label"],
    }


def _extract_gap_fields(flags):
    for f in flags:
        if f.startswith("incomplete_submission:"):
            return f.split(":", 1)[1].split(",")
    return []


def _snapshot(row_index, lead):
    """Disposable debug snapshot - never the source of truth, per CLAUDE.md."""
    try:
        TMP_DIR.mkdir(exist_ok=True)
        (TMP_DIR / f"lead_row_{row_index}.json").write_text(json.dumps(lead, indent=2))
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run a single pass and exit (for testing)")
    args = parser.parse_args()

    if args.once:
        process_once()
        return

    while True:
        process_once()
        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
