# Scoring rubric (0-100)

Score each dimension, then add. Show the dimension numbers in your own working only if the user asks.

| Dimension | Max | How to score |
|---|---|---|
| Role fit | 30 | 26-30 core AI/ML/GenAI engineering exactly as the user's target titles. 18-25 adjacent (data science with ML, MLOps, AI solutions with real engineering). 8-17 AI in name but mostly analytics, BI, support or consulting. 0-7 not AI work. |
| Skills match | 30 | Take the JD's must-haves. Each must-have the ledger proves = full share, nice-to-haves = half share. Skills that are `claimed-only` count as 0. Any missing must-have caps this dimension at 20. |
| Experience level | 15 | 13-15 inside the JD range. 8-12 within 1-2 years outside. 0-7 further out. |
| Location, mode, notice | 10 | Location and mode match preferences (6), notice period of 30 days acceptable to the JD (4). Unknown notice = 2. |
| Company and compensation | 10 | Real product or known employer, pay at or above the floor (or unstated, 5). Pay clearly below floor = hard-filtered earlier. |
| Posting quality and legitimacy | 5 | Clear responsibilities, named company, normal apply path = 5. Vague = 2. Spam wording = 0 (and skip). |

Thresholds come from `data/preferences.md` (`shortlist_min`, `borderline_min`).

## Calibration (during build step 4)
Run on 30 jobs, compare with the user's own verdicts, and adjust the above bands here, not in SKILL.md.
