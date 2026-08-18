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

### 3. Budget Fit — 25 points
Compare the submitted budget to the price of the listing they inquired about, or to typical inventory in their preferred area if no specific listing.
| Form answer | Points |
|---|---|
| Within ~10% of relevant listing/inventory price | 25 |
| Within ~25%, plausible with negotiation | 12 |
| Far below or unrealistic for the market | 0 |

### 4. Preferred Area Match — 20 points
| Form answer | Points |
|---|---|
| Matches an active listing exactly | 20 |
| Matches the company's general coverage area | 10 |
| Outside the company's coverage area entirely | 0 |

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
  "budget_fit": {"answer": "1.4M vs 1.35M listing", "score": 25},
  "area_match": {"answer": "Exact match to inquired listing", "score": 20},
  "total_score": 95,
  "label": "hot",
  "flags": []
}
```

## Two Implementation Notes

- **If the form fields are dropdown/select values** (most likely), this whole thing is a plain lookup table — `tools/score_lead.py` maps each answer string to its point value and sums them. No LLM call needed for this step at all.
- **If any field is free text** (e.g. budget typed as "around 1.3-1.5m" or area typed as "somewhere near downtown"), that field needs a light normalization pass first — an LLM or regex step that maps the free text to the closest structured bucket above — before the lookup table runs. Keep that normalization step separate and logged, so you can see when it guesses wrong.