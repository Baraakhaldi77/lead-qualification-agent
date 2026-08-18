# Workflow: Score Lead

## Objective

Apply the rubric in `docs/lead_scoring_criteria.md` to a valid lead. This is a deterministic lookup — never an LLM judgment call, per that doc and per CLAUDE.md's non-negotiables.

## Required Inputs

- A normalized lead object
- The gap-fields list from `validate_lead.md` (empty list for a fully valid lead)
- The Reference Data lookup: `{area: tier}` (Low/Medium/Expensive), read fresh from the Reference Data sheet tab each run

## Tools

- `tools/score_lead.py` (`score_lead`)

## Logic (mirrors docs/lead_scoring_criteria.md exactly)

- **Financing** (30 pts) and **Timeline** (25 pts): flat string lookup against the form's dropdown answers.
- **Budget** (25 pts): parse the submitted budget as a number (handles "100k $", "1.2m", commas) and band it against a fixed threshold — over $250k = 25, $150k–$250k = 16, $50k–$150k = 8, under $50k = 0. Not compared against any reference price.
- **Area Match** (20 pts): normalize the submitted free-text area (strip Turkish diacritics, lowercase) and match it against Reference Data's district list by containment — Expensive = 20, Medium = 14, Low = 7, not found = 0.
- **Total** → band into `hot` (80–100) / `warm` (50–79) / `cold` (0–49).

## Output

Score breakdown dict matching `docs/lead_scoring_criteria.md`'s Output Format (per-category answer + score, `total_score`, `label`).

## Edge Cases

- A gap field (from `incomplete_submission`) always scores 0 in its category, regardless of what's actually in that cell — don't half-trust a flagged field.
- An area not present in Reference Data correctly zeroes Area Match — never invent a tier to avoid this; add the district to Reference Data instead.
- If `docs/lead_scoring_criteria.md` and this workflow ever disagree, the doc wins — fix `tools/score_lead.py`, don't reinterpret the rubric here.
