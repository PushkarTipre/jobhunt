# Portals

You log in yourself in Chrome. No passwords are stored anywhere. Fill the `TO_BE_CONFIRMED` items during setup (jh-discovery will ask on first run).

| Portal | URL | Logged in? | Method | Daily apply cap | Apply type | Notes |
|---|---|---|---|---|---|---|
| Naukri | https://www.naukri.com | TO_BE_CONFIRMED | Logged-in Chrome search; use keyword + location + "last 3/7 days" filter | 3 | Mixed: on-portal "Apply" or "Apply on company website" (always MANUAL) | Questionnaire/chatbot popups are common: only proceed if every question is covered by the answers bank. Daily quota exists. |
| Foundit | https://www.foundit.in | TO_BE_CONFIRMED | Logged-in Chrome search | 3 | Mostly on-portal | |
| Instahyre | https://www.instahyre.com | TO_BE_CONFIRMED | Logged-in Chrome (opportunities feed) | 3 | On-portal "interested" flow | Employer-initiated model: "applying" may be an expression of interest. |
| Hirist | https://www.hirist.tech | TO_BE_CONFIRMED | Public search pages | 3 | Mixed | Tech-focused. |
| Cutshort | https://cutshort.io | TO_BE_CONFIRMED | Logged-in Chrome | 3 | On-portal | Often needs profile-based matching. |
| Wellfound | https://wellfound.com | TO_BE_CONFIRMED | Public search + logged-in Chrome | 3 | On-portal, often with a short note field (free text = MANUAL) | Startups. |
| Company career pages | various | n/a | Reached from Naukri "Apply on company site" or web search | `company_site_cap_per_day` (5) | Company site | Simple forms only (no login/account/CAPTCHA/OTP), see data/form_profile.md and preferences. Anything else stays manual. |
| LinkedIn | https://www.linkedin.com | manual | Manual use only. Never automated applying. Read-only people lookups by jh-referral-finder (if enabled) | 0 | n/a | LinkedIn prohibits automation. Keep lookups tiny. |

## Per-portal checks to fill in during Step 8 of the build order
Can a different resume be attached per application on this portal? (yes / no / only via profile)
- Naukri: TO_BE_CONFIRMED
- Foundit: TO_BE_CONFIRMED
- Instahyre: TO_BE_CONFIRMED
- Hirist: TO_BE_CONFIRMED
- Cutshort: TO_BE_CONFIRMED
- Wellfound: TO_BE_CONFIRMED
If "no", a tailored resume is used only for company-site and manual applications and the portal profile keeps the best general resume.
