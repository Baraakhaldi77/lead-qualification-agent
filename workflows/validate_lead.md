# Workflow: Validate Lead

## Objective

Run the pre-score data gate from `docs/lead_scoring_criteria.md` before any scoring or outreach happens. Bad data gets flagged for a human, not scored or guessed at.

## Required Inputs

- A normalized lead object (output of `intake_lead.md`)

## Tools

- `tools/validate_lead.py` (`validate_submission`) — returns `(valid, flags)`.

## Rules

- Phone fails format/digit-count check → flag `invalid_contact`
- Email domain is on the disposable-domain blocklist (`tools/config.py`) → flag `invalid_contact`
- Any of budget / timeline / financing / area is blank → flag `incomplete_submission:<comma-separated missing fields>`

## Output

`valid: bool`, `flags: list[str]`

## Edge Cases

- Both `invalid_contact` and `incomplete_submission` can fire on the same lead. Treat `invalid_contact` as the more severe case: **skip scoring entirely**, since the contact info itself may be unreachable — there's no point computing a score for a lead you can't email.
- `incomplete_submission` alone still gets a **partial score** for visibility (missing fields score 0 in their category) but must **not** trigger an automated email — route to the admin for manual review either way (see `dispatch_email.md`).
- Never relax these checks to "send anyway" — this is the one gate standing between a bad submission and an automated email going out.
