# Workflow: Dispatch Email

## Objective

Send exactly one tier-appropriate email per lead, and route flagged leads to a human instead of the lead.

## Required Inputs

- The normalized lead object
- The lead's `label` (`hot` / `warm` / `cold`) from `score_lead.md` — only reached if the lead passed `validate_lead.md`
- The row's current `Status` / `Email Sent` state (read fresh, not cached) — this is the idempotency guard

## Tools

- `tools/dispatch_email.py` (`compose_tier_email`, `compose_admin_alert`)
- `tools/gmail_client.py` (`send_email`)
- `tools/sheets_client.py` (`write_row_updates`) — to persist `Status` / `Email Sent` / `Email Sent At` immediately after a successful send

## Rules

- **hot** / **warm** / **cold** all get an email — different template per tier (`tools/config.py`'s `EMAIL_TEMPLATES`). Cold is deliberately low-touch/no-urgency, not skipped.
- **Flagged leads (`needs_review` status) never get the lead-facing email.** Instead send `compose_admin_alert(...)` to `ADMIN_EMAIL` so a human checks the row.
- Write the Sheet update **after** a successful send, not before — if the send fails, the row's `Status` stays blank so the next poller pass retries it, instead of silently marking a lead as handled when they were never actually emailed.
- Before sending, check `Email Sent` isn't already `yes` for that row — a poller pass that re-reads a row it already fully processed must not double-email.

## Edge Cases

- If the Sheets write fails right after a successful send (rare), the row could get retried and double-emailed on the next pass — known Phase-1 limitation, watch the poller's logs if this happens.
- Never invent property details in the email body that aren't already in `tools/config.py`'s templates or the lead's own submitted data — say a human will follow up with specifics.
