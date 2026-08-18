"""
Google Sheets API v4 wrapper. Every read pulls fresh state from the
Sheet - nothing here caches a row across calls, per CLAUDE.md's
"state lives in the sheet, not in memory" rule.
"""

from googleapiclient.discovery import build


def build_sheets_service(creds):
    return build("sheets", "v4", credentials=creds)


def read_sheet(service, spreadsheet_id, sheet_name):
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range=sheet_name
    ).execute()
    values = result.get("values", [])
    if not values:
        return [], []
    return values[0], values[1:]


def read_reference_data(service, spreadsheet_id, sheet_name):
    """Reference Data sheet is Area | Tier (Low/Medium/Expensive) - a plain
    district -> price-tier classification, not a per-listing price table."""
    _, rows = read_sheet(service, spreadsheet_id, sheet_name)
    reference = {}
    for row in rows:
        if len(row) < 2 or not row[0].strip():
            continue
        reference[row[0].strip()] = row[1].strip()
    return reference


def ensure_headers(service, spreadsheet_id, sheet_name, expected_headers):
    """Appends any missing headers to row 1. Never removes/reorders existing ones."""
    headers, _ = read_sheet(service, spreadsheet_id, sheet_name)
    missing = [h for h in expected_headers if h not in headers]
    if not missing:
        return headers
    new_headers = headers + missing
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        body={"values": [new_headers]},
    ).execute()
    return new_headers


def write_row_updates(service, spreadsheet_id, sheet_name, row_index, headers, updates: dict):
    """row_index is 1-indexed sheet row (2 = first data row). One batched call per row."""
    if not updates:
        return
    data = []
    for header, value in updates.items():
        col_letter = _col_letter(headers.index(header))
        data.append({
            "range": f"{sheet_name}!{col_letter}{row_index}",
            "values": [[value]],
        })
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "RAW", "data": data},
    ).execute()


def _col_letter(index_zero_based):
    index = index_zero_based + 1
    letters = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters
