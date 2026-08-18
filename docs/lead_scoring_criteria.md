# Lead Scoring Criteria — Based on Form Submission

This scores a lead the moment the form is submitted, using only the four qualifying fields the form collects: **budget, timeline, financing, preferred area**. No conversation has happened yet — this is the triage score that decides how fast and how hard the agent should chase this lead in the first WhatsApp message.

Because these fields are almost certainly structured (dropdowns/select options), this scoring step should mostly be a **deterministic lookup table in code, not an LLM judgment call.** Save the LLM for the qualification conversation later — this step just needs to map form answers to points.

## Scoring Categories

### 1. Financing Readiness — 30 points
Most predictive field for deal likelihood, so it carries the most weight.
| Form answer | Points |
|---|---|
| Cash buyer | 30 |
| Pre-approved mortgage | 25 |
| Needs financing, not yet applied | 12 |
| Not sure / no answer | 0 |

### 2. Timeline — 25 points
| Form answer | Points |
|---|---|
| Immediately / within 30 days | 25 |
| 1–3 months | 18 |
| 3–6 months | 8 |
| Just researching / no timeline | 0 |

### 3. Budget — 25 points
Absolute threshold on the submitted budget amount - not compared against a per-area or per-listing price, so it needs no per-area pricing data to maintain.
| Budget | Points |
|---|---|
| Over $250k | 25 |
| $150k – $250k | 16 |
| $50k – $150k | 8 |
| Under $50k | 0 |

### 4. Preferred Area Match — 20 points
The submitted area (free text, e.g. "Istanbul, Basaksehir") is matched against the **Reference Data** sheet tab (`Area | Tier`), which classifies each district as Low/Medium/Expensive based on its real-world price tier - not per-listing coverage. Matching is case/diacritic-insensitive (handles Turkish characters) and matches by the district name appearing anywhere in the submitted text.
| Area tier | Points |
|---|---|
| Expensive | 20 |
| Medium | 14 |
| Low | 7 |
| Not found in Reference Data | 0 |

**Total: 100 points**

## Score Bands

| Score | Label | Action |
|---|---|---|
| 80–100 | **Hot** | Call or WhatsApp within minutes, offer viewing slots in the first message |
| 50–79 | **Warm** | Standard WhatsApp qualification sequence |
| 0–49 | **Cold** | Low-touch nurture sequence, no immediate viewing push |

## Pre-Score Data Gate

Before scoring, validate the submission itself — bad data shouldn't get a score, it should get flagged:
- Phone number fails format/country validation → flag `invalid_contact`, route to manual review
- Email is a disposable/throwaway domain → flag `invalid_contact`
- A required field (budget, timeline, financing, or area) was left blank → flag `incomplete_submission`, score only on what's present and note the gap

Leads with either flag skip scoring and go to a human to check before any automated outreach happens.

## Output Format

```json
{
  "financing": {"answer": "Pre-approved mortgage", "score": 25},
  "timeline": {"answer": "Within 30 days", "score": 25},
  "budget_fit": {"answer": "180,000", "score": 16},
  "area_match": {"answer": "Istanbul, Basaksehir (Medium)", "score": 14},
  "total_score": 95,
  "label": "hot",
  "flags": []
}
```

## Two Implementation Notes

- **Financing and Timeline are dropdown/select values**, so those two are a plain lookup table — `tools/score_lead.py` maps each answer string to its point value directly. No LLM call for this step at all.
- **Budget and Preferred area are free text**, so each gets a regex-based normalization pass before scoring (`tools/score_lead.py`): Budget parses shorthand like "100k $" or "1.2m" into a number; Area is matched against the Reference Data district list case/diacritic-insensitively. Both are deterministic regex, not an LLM call - kept separate and logged (the `answer` field in the output shows exactly what was parsed/matched) so a bad parse is visible, not silent.