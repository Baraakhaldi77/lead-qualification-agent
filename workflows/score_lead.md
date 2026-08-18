# Workflow: Score Lead

## Objective

Apply the rubric in `docs/lead_scoring_criteria.md` to a valid lead. This is a deterministic lookup — never an LLM judgment call, per that doc and per CLAUDE.md's non-negotiables.

## Required Inputs

- A normalized lead object
- The gap-fields list from `validate_lead.md` (empty list for a fully valid lead)
- The Reference Data lookup: `{area: {typical_price, tier}}`, read fresh from the Reference Data sheet tab each run

## Tools

- `tools/score_lead.py` (`score_lead`)

## Logic (mirrors docs/lead_scoring_criteria.md exactly)

- **Financing** (30 pts) and **Timeline** (25 pts): flat string lookup against the form's dropdown answers.
- **Area Match** (20 pts): look up the submitted area in Reference Data — `Active Listing` tier = 20, `General Coverage` = 10, not found = 0.
- **Budget Fit** (25 pts): parse the submitted budget as a number, compare against the matched area's `typical_price` — within ~10% = 25, within ~25% = 12, otherwise 0. No reference price found for the area → 0, note it in the answer text rather than guessing.
- **Total** → band into `hot` (80–100) / `warm` (50–79) / `cold` (0–49).

## Output

Score breakdown dict matching `docs/lead_scoring_criteria.md`'s Output Format (per-category answer + score, `total_score`, `label`).

## Edge Cases

- A gap field (from `incomplete_submission`) always scores 0 in its category, regardless of what's actually in that cell — don't half-trust a flagged field.
- An area not present in Reference Data correctly zeroes both Area Match and Budget Fit — never invent a typical price to avoid this.
- If `docs/lead_scoring_criteria.md` and this workflow ever disagree, the doc wins — fix `tools/score_lead.py`, don't reinterpret the rubric here.
