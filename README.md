# Real Estate Lead Qualification Agent — Phase 1

Google Form submission → Google Sheet (native) → a scheduled Python poller runs the WAT pipeline
(`workflows/` SOPs, `tools/` deterministic Python) → scores the lead against `docs/lead_scoring_criteria.md`
→ writes the result back to the row → sends a tiered Gmail email (hot / warm / cold), or routes
flagged submissions to a human instead.

No webhook, no hosting: the "Agent" (`agent/run.py`) is a script you run on a schedule (cron / Windows
Task Scheduler) that re-reads the Sheet each pass and processes whatever hasn't been handled yet — state
lives in the Sheet, not in the process.

## Setup

### 1. Create the Google Form

Create the questions **in this exact order and wording** (the pipeline maps columns by header name, and the header name is the question title):

1. **Full name** — short answer
2. **Phone** — short answer (add Form-level validation: regex, e.g. `^[\d\s()+-]{7,20}$`)
3. **Email** — short answer, enable the Form's built-in email validation
4. **Budget** — short answer, **numeric only** (not a dropdown — Budget Fit needs a real number)
5. **Timeline** — dropdown: `Immediately / within 30 days`, `1–3 months`, `3–6 months`, `Just researching / no timeline`
6. **Financing** — dropdown: `Cash buyer`, `Pre-approved mortgage`, `Needs financing, not yet applied`, `Not sure / no answer`
7. **Preferred area** — dropdown, values should match whatever you'll put in the Reference Data sheet's `Area` column, plus an `Other / not listed` option

Link the form to a new Google Sheet (Responses tab → green Sheets icon → Create spreadsheet). Note the sheet's response tab name (usually `Form Responses 1`) and the spreadsheet ID (the long string in its URL) — both go in `.env`.

Add a second tab named **Reference Data** with headers `Area | Typical Price | Tier`, and populate it with real rows, e.g.:

| Area | Typical Price | Tier |
|---|---|---|
| Downtown | 1350000 | Active Listing |
| Riverside | 850000 | General Coverage |

`Tier = Active Listing` scores 20 Area-Match points (areas where you currently have listings), `General Coverage` scores 10 (areas you serve but have no active listing in). Anything submitted that doesn't match a row here scores 0 on both Area Match and Budget Fit — keep this table current.

### 2. Google Cloud project (for Sheets + Gmail API access)

1. Create/select a project at console.cloud.google.com, enable the **Google Sheets API** and **Gmail API**.
2. Configure the OAuth consent screen (Internal if Workspace, External + your account as a test user otherwise).
3. Create an **OAuth client ID**, type **Desktop app**. Download the JSON and save it as `credentials.json` at the project root (gitignored — never commit it).

### 3. Install and configure

```
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`: `GOOGLE_SHEET_ID`, `LEADS_SHEET_NAME`, `REFERENCE_SHEET_NAME`, `SENDER_NAME`, `ADMIN_EMAIL`, `POLL_INTERVAL_SECONDS`.

### 4. First run (authorizes + adds score columns)

From the project root:

```
python -m agent.run --once
```

This opens a browser window to authorize Sheets + Gmail access (writes `token.json`, gitignored, auto-refreshed after this), then adds the score/status header columns to the Leads tab if they're not already there, and processes any existing rows.

### 5. Schedule it

Run `python -m agent.run` (no `--once`) to poll continuously at `POLL_INTERVAL_SECONDS`, or call `python -m agent.run --once` on a schedule instead (Windows Task Scheduler, cron, etc.) if you'd rather not keep a long-running process.

## Testing

Submit test entries through the live form covering:
- A **hot** case (cash buyer, immediate timeline, budget within 10% of an Active Listing area's typical price)
- A **warm** case (score 50–79)
- A **cold** case (score 0–49)
- An **invalid_contact** case (garbage phone number, or an email at a disposable domain from `tools/config.py`'s blocklist)
- An **incomplete_submission** case (leave a non-required-by-Forms field blank, or edit a submitted row's cell blank before the next poll)

Run `python -m agent.run --once` after submitting, then check: the Leads sheet row for correct scores/label/flags/status, the lead's inbox for the right tier email (or, for flagged rows, that the lead got **no** email and `ADMIN_EMAIL` got a review alert instead).

To confirm the idempotency guard, run `python -m agent.run --once` a second time against the same rows — `Status` is already set, so they're skipped and no duplicate email goes out.

## Known Phase-1 limits

- Detection latency = your poll interval, not instant (this was the explicit tradeoff for not hosting a webhook).
- Gmail send quota: ~100/day on a plain Gmail account, ~1,500/day on Google Workspace.
- Budget Fit and Area Match are only as good as the Reference Data table.
- No conversation, no CRM, no calendar booking yet — the trigger and scoring rubric are locked in per `CLAUDE.md`, everything else about the qualification conversation is still to be planned.
