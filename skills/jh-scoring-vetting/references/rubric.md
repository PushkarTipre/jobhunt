# Scoring rubric (0-100)

Score each dimension, then add. Show the dimension numbers in your own working only if the user asks.

| Dimension | Max | How to score |
|---|---|---|
| Role fit | 30 | Judge against `role_focus` and the target titles in `data/preferences.md`. 26-30 the core of the job is `role_focus` under a `target_titles_primary` title. 18-25 adjacent: a `target_titles_acceptable` title, or a primary-type job where `role_focus` is only about half the work. 8-17 the title fits but the work is mostly something else (support, QA, BI, consulting, a different main tech stack). 0-7 not this kind of work. |
| Skills match | 30 | Take the JD's must-haves. Each must-have the ledger proves = full share, nice-to-haves = half share. Skills that are `claimed-only` count as 0. Any missing must-have caps this dimension at 20. |
| Experience level | 15 | 13-15 inside the JD range. 8-12 within 1-2 years outside. 0-7 further out. |
| Location, mode, notice | 10 | Location and mode match preferences (6), notice period of 30 days acceptable to the JD (4). Unknown notice = 2. |
| Company and compensation | 10 | Real product or known employer, pay at or above the floor (or unstated, 5). Pay clearly below floor = hard-filtered earlier. |
| Posting quality and legitimacy | 5 | Clear responsibilities, named company, normal apply path = 5. Vague = 2. Spam wording = 0 (and skip). |

Thresholds come from `data/preferences.md` (`shortlist_min`, `borderline_min`).

## Role-fit examples for a Flutter / mobile `role_focus` (rewrite these if yours changes)
- Flutter Developer or Mobile Engineer building Flutter apps (BLoC/Riverpod, REST, Firebase): 26-30.
- Full-stack with Flutter plus a Python/Django or Node backend; Python/Django backend roles; app roles that add AI features (LLM, vision, speech APIs): 18-25.
- Native-only Android (Kotlin) or iOS (Swift), or React Native, with no Flutter: 8-17.
- Pure ML research or model-training roles, web-only frontend, manual QA, support: 0-7.

## Calibration (during build step 4)
Run on 30 jobs, compare with the user's own verdicts, and adjust the above bands here, not in SKILL.md.
