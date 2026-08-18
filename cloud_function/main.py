"""
Cloud Function entry point for instant (webhook-triggered) lead processing.
Mirrors tools/*.py and agent/run.py exactly (same validation/scoring/email
rules) - condensed into one file for easy paste into the Cloud Console's
inline source editor. Triggered by an Apps Script onFormSubmit trigger
calling this function's URL the moment a lead submits, instead of a
scheduled poll.

Required environment variables (set in Cloud Console -> Runtime settings):
  TOKEN_JSON          - full contents of your local token.json
  GOOGLE_SHEET_ID      - your spreadsheet ID
  LEADS_SHEET_NAME     - e.g. "Form responses 1"
  REFERENCE_SHEET_NAME - e.g. "Reference Data"
  SENDER_NAME          - e.g. "Yariga Realty"
  ADMIN_EMAIL          - e.g. your email
  WEBHOOK_SECRET       - shared secret, must match the Apps Script trigger
"""

import base64
import json
import os
import re
from email.mime.text import MIMEText

import functions_framework
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.send",
]

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
AREA_TIER_SCORES = {"Expensive": 20, "Medium": 14, "Low": 7}
BUDGET_SCORE_BANDS = [(250_000, 25), (150_000, 16), (50_000, 8)]
SCORE_BANDS = {"hot_min": 80, "warm_min": 50}
_TURKISH_MAP = str.maketrans({
    "ç": "c", "Ç": "c", "ğ": "g", "Ğ": "g", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ü": "u", "Ü": "u",
})
REQUIRED_FIELDS = ["budget", "timeline", "financing", "area"]
DISPOSABLE_EMAIL_DOMAINS = [
    "mailinator.com", "guerrillamail.com", "tempmail.com", "10minutemail.com",
    "throwawaymail.com", "yopmail.com", "trashmail.com", "getnada.com",
]

EMAIL_TEMPLATES = {
    "hot": {
        "subject": "Let's get you in to see {{area}} properties",
        "body": (
            "Hi {{name}},\n\nThanks for reaching out about {{area}} - I'd like to get you viewing "
            "options right away. What's the best time to reach you today by phone?\n\nTalk soon"
        ),
    },
    "warm": {
        "subject": "Thanks for your interest, {{name}}",
        "body": (
            "Hi {{name}},\n\nThanks for your interest in {{area}}. One of our agents will follow up "
            "with you as soon as possible to talk through what you're looking for.\n\n"
            "In the meantime, feel free to browse our current listings."
        ),
    },
    "cold": {
        "subject": "Thanks for stopping by, {{name}}",
        "body": (
            "Hi {{name}},\n\nThanks for your interest in {{area}}. No pressure at all - feel free to "
            "browse listings whenever you're ready, and reach out any time you have questions."
        ),
    },
}


def get_credentials():
    creds = Credentials.from_authorized_user_info(json.loads(os.environ["TOKEN_JSON"]), SCOPES)
    if not creds.valid:
        creds.refresh(Request())
    return creds


def read_sheet(service, spreadsheet_id, sheet_name):
    result = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id, range=sheet_name).execute()
    values = result.get("values", [])
    return (values[0], values[1:]) if values else ([], [])


def read_reference_data(service, spreadsheet_id, sheet_name):
    """Reference Data sheet is Area | Tier (Low/Medium/Expensive)."""
    _, rows = read_sheet(service, spreadsheet_id, sheet_name)
    reference = {}
    for row in rows:
        if len(row) < 2 or not row[0].strip():
            continue
        reference[row[0].strip()] = row[1].strip()
    return reference


def col_letter(index_zero_based):
    index, letters = index_zero_based + 1, ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def write_row_updates(service, spreadsheet_id, sheet_name, row_index, headers, updates):
    if not updates:
        return
    data = [{"range": f"{sheet_name}!{col_letter(headers.index(h))}{row_index}", "values": [[v]]} for h, v in updates.items()]
    service.spreadsheets().values().batchUpdate(spreadsheetId=spreadsheet_id, body={"valueInputOption": "RAW", "data": data}).execute()


def send_email(service, to, subject, body, sender_name=None):
    message = MIMEText(body)
    message["to"], message["subject"] = to, subject
    if sender_name:
        message["from"] = sender_name
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()


def normalize_row(headers, row):
    normalized_index = {" ".join(h.split()).strip().casefold(): i for i, h in enumerate(headers)}
    lead = {}
    for field, header in FIELD_HEADERS.items():
        idx = normalized_index.get(" ".join(header.split()).strip().casefold())
        lead[field] = row[idx] if idx is not None and idx < len(row) else ""
    return lead


def is_valid_phone(raw):
    digits = re.sub(r"\D", "", raw or "")
    return 7 <= len(digits) <= 15


def is_disposable_email(raw):
    if not raw or "@" not in raw:
        return bool(raw)
    return raw.strip().lower().split("@")[-1] in DISPOSABLE_EMAIL_DOMAINS


def validate_submission(lead):
    flags = []
    if not is_valid_phone(lead.get("phone", "")):
        flags.append("invalid_contact")
    if is_disposable_email(lead.get("email", "")) and "invalid_contact" not in flags:
        flags.append("invalid_contact")
    missing = [f for f in REQUIRED_FIELDS if not str(lead.get(f, "")).strip()]
    if missing:
        flags.append("incomplete_submission:" + ",".join(missing))
    return (len(flags) == 0, flags)


def parse_number(raw):
    if not raw:
        return None
    m = re.search(r"([\d,]*\.?\d+)\s*(k|m)?", str(raw).strip(), re.IGNORECASE)
    if not m:
        return None
    try:
        value = float(m.group(1).replace(",", ""))
    except ValueError:
        return None
    suffix = (m.group(2) or "").lower()
    return value * 1_000 if suffix == "k" else value * 1_000_000 if suffix == "m" else value


def score_lookup(table, answer, is_gap):
    if is_gap or not answer:
        return {"answer": answer or "(blank)", "score": 0}
    return {"answer": answer, "score": table.get(answer, 0)}


def normalize_area_text(s):
    s = (s or "").translate(_TURKISH_MAP).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def match_area_tier(area_text, reference):
    normalized = normalize_area_text(area_text)
    if not normalized:
        return None
    for district, tier in reference.items():
        district_norm = normalize_area_text(district)
        if district_norm and district_norm in normalized:
            return tier
    return None


def score_lead(lead, gap_fields, reference):
    financing = score_lookup(FINANCING_SCORES, lead.get("financing"), "financing" in gap_fields)
    timeline = score_lookup(TIMELINE_SCORES, lead.get("timeline"), "timeline" in gap_fields)

    if "area" in gap_fields or not lead.get("area"):
        area_match = {"answer": lead.get("area") or "(blank)", "score": 0}
    else:
        tier = match_area_tier(lead.get("area"), reference)
        area_match = {"answer": f"{lead.get('area')} ({tier or 'unclassified'})", "score": AREA_TIER_SCORES.get(tier, 0)}

    if "budget" in gap_fields:
        budget_fit = {"answer": "(blank)", "score": 0}
    else:
        budget = parse_number(lead.get("budget"))
        if budget is None:
            budget_fit = {"answer": f"{lead.get('budget')} (unparseable)", "score": 0}
        else:
            score = 0
            for minimum, points in BUDGET_SCORE_BANDS:
                if budget >= minimum:
                    score = points
                    break
            budget_fit = {"answer": f"{budget:,.0f}", "score": score}

    total = financing["score"] + timeline["score"] + budget_fit["score"] + area_match["score"]
    label = "hot" if total >= SCORE_BANDS["hot_min"] else "warm" if total >= SCORE_BANDS["warm_min"] else "cold"
    return {"financing": financing, "timeline": timeline, "budget_fit": budget_fit, "area_match": area_match, "total_score": total, "label": label}


def fill_template(text, lead):
    return text.replace("{{name}}", lead.get("name") or "there").replace("{{area}}", lead.get("area") or "your area of interest")


def score_updates(score):
    h = SCORE_HEADERS
    return {
        h["financing_score"]: score["financing"]["score"], h["timeline_score"]: score["timeline"]["score"],
        h["budget_score"]: score["budget_fit"]["score"], h["area_score"]: score["area_match"]["score"],
        h["total_score"]: score["total_score"], h["label"]: score["label"],
    }


def extract_gap_fields(flags):
    for f in flags:
        if f.startswith("incomplete_submission:"):
            return f.split(":", 1)[1].split(",")
    return []


def process_once():
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds)
    gmail = build("gmail", "v1", credentials=creds)

    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    leads_sheet = os.environ["LEADS_SHEET_NAME"]
    reference_sheet = os.environ["REFERENCE_SHEET_NAME"]
    admin_email = os.environ["ADMIN_EMAIL"]
    sender_name = os.environ["SENDER_NAME"]
    h = SCORE_HEADERS

    headers, rows = read_sheet(sheets, sheet_id, leads_sheet)
    reference = read_reference_data(sheets, sheet_id, reference_sheet)
    status_idx = headers.index(h["status"])

    for i, row in enumerate(rows):
        row_index = i + 2
        status = row[status_idx] if status_idx < len(row) else ""
        if status:
            continue

        lead = normalize_row(headers, row)
        valid, flags = validate_submission(lead)

        if not valid:
            updates = {h["flags"]: "; ".join(flags), h["status"]: "needs_review"}
            if "invalid_contact" not in flags:
                score = score_lead(lead, extract_gap_fields(flags), reference)
                updates.update(score_updates(score))
            send_email(gmail, admin_email, f"Lead needs manual review: {lead.get('name') or lead.get('email')}",
                       f"Flags: {', '.join(flags)}\n\nPlease review this row in the Leads sheet.", sender_name)
            write_row_updates(sheets, sheet_id, leads_sheet, row_index, headers, updates)
            continue

        score = score_lead(lead, [], reference)
        template = EMAIL_TEMPLATES[score["label"]]
        send_email(gmail, lead["email"], fill_template(template["subject"], lead), fill_template(template["body"], lead), sender_name)

        updates = score_updates(score)
        updates[h["status"]] = "scored"
        updates[h["email_sent"]] = "yes"
        write_row_updates(sheets, sheet_id, leads_sheet, row_index, headers, updates)


@functions_framework.http
def handle_webhook(request):
    if request.headers.get("X-Webhook-Secret") != os.environ.get("WEBHOOK_SECRET"):
        return ("unauthorized", 401)
    process_once()
    return ("ok", 200)
