# Risk review: bugs, vulnerabilities and usage-burn loops

Reviewed against the blueprint (v1.0). "Fix" says where the mitigation now lives.

## A. Loops and usage burn (highest priority)

| # | Risk in the blueprint design | How it would burn usage | Fix built in |
|---|---|---|---|
| A1 | Stages had no work ceilings ("search the portals", "score each job") | One run could open hundreds of pages and read hundreds of JDs | Hard budgets in `preferences.md` (queries 6, pages 2, new jobs 30, scored 25, tailored 6, apply 10, referral 5 jobs, emails 30, searches 3). Each skill reads and obeys them. |
| A2 | Nothing said "run once" | A stage that finds little may re-search "to be thorough"; the orchestrator may re-run stages | "One pass" rule in every skill and the orchestrator; no stage calls the orchestrator; leftovers wait for the next run. |
| A3 | FAILED / RESUME_READY rows could be retried every run | Same broken form retried forever, 20+ browser actions each time | `Attempts` counter, `max_attempts_per_job` (3), FAILED never retried in the same session, two consecutive failures end the session, 25-action cap per job. |
| A4 | Dry-run rows stay RESUME_READY, so every run re-checks them | Infinite re-checking | `tracker.py attempt` counts dry runs; after the cap they are left for you. |
| A5 | Verify mode scheduled twice a day would call Gmail even with nothing pending | Wasted runs every day | `pending-check` early exit (no Gmail call when nothing to verify) plus a 6-hour minimum gap. |
| A6 | Screenshots of every step | Images are the most expensive input | Skills read page text; one screenshot per application, only for proof. |
| A7 | Re-reading JDs and the whole spreadsheet each run | Large context each stage | JD saved once to `jd/*.txt`; rows read through `tracker.py list --fields ... --limit N`; the xlsx is never loaded into the conversation. |
| A8 | Resume tailoring retry loop (truth check fails, rewrite, fail...) | Repeated generation | At most one fix-and-retry; second failure falls back to the Base resume with a note. |
| A9 | Referral finder could browse LinkedIn at length | Many page reads, and account risk | 5 jobs, 3 contacts per job, 10 profile views per run, one pass. |
| A10 | Scheduled task failing silently and re-triggering | Repeated failing runs | Errors stop the stage and are written to the Run Log; no auto-retry; usage-limit message stops the run. Check the Run Log tab weekly. |
| A11 | Pro limits are shared across chat, Cowork, Chrome and Code | Scan + apply + chat in one day can exhaust the window | Apply sessions capped at 10, scan once a day, apply only when you start it, cheap early exits. Watch usage for the first week. |

## B. Correctness bugs

| # | Bug | Fix |
|---|---|---|
| B1 | Two skills overwrite each other's data | Every write goes through `tracker.py` with an actor; each actor may only move specific statuses and write specific columns. Verified in tests (an invalid move returned exit 2). |
| B2 | Spreadsheet open in Excel while Claude writes: corrupt or lost update | Writes are atomic (temp file then replace), refuse while Excel's `~$tracker.xlsx` lock exists, exit code 3 with a clear message, daily backups in `logs/backups`. |
| B3 | Duplicate jobs across portals | Dedup by company + title + city, and by URL (query strings ignored); extra portal URLs appended to notes. |
| B4 | Status column colouring done row by row can go stale | Colours are conditional formatting on Status, so they always match. Dashboard uses COUNTIF formulas. |
| B5 | Tailor "re-words" a bullet and slips in a new number or skill | `truth_check.py` blocks any number, skill, employer, title, date or contact not in the master profile, and warns on ungrounded bullets. Tested with a planted fake number, a claimed-only skill and an invented bullet. |
| B6 | Salary answers auto-filled wrongly | Only three approved answers are `yes`; everything else (CTC breakup, offers, negotiability) goes to MANUAL_REQUIRED. `TO_BE_CONFIRMED` values may never be submitted. |
| B7 | Naukri "Apply on company website" attempted anyway | Hard rule, always MANUAL_REQUIRED. |
| B8 | A tailored resume cannot be attached on some portals, so the wrong resume is submitted | The apply test requires the file to be the row's prepared resume; `portals.md` records per-portal attach ability (open item, verify in build step 8). |
| B9 | Verifier marks NO_CONFIRMATION wrongly for portal-only applications | Portal "Applied jobs" check before declaring NO_CONFIRMATION; later emails can still promote it to CONFIRMED. |
| B10 | `MANUAL_REQUIRED` rows you applied to by hand are never verified | You tell Claude "I applied to <ID>"; it records `SUBMITTED` as actor `user`, and the verifier then picks it up. |
| B12 | Tailored resumes looked bad (generic PDF renderer) | Resumes are now rendered from the user's own LaTeX template via Tectonic; design, header, education and achievements are copied verbatim. Page count is verified; a wrong count blocks instead of passing. |
| B11 | Free-text cells could exceed Excel limits | JD text lives in `jd/` files; notes are truncated at 2,000 characters. |

## C. Security and privacy

| # | Vulnerability | Fix |
|---|---|---|
| C1 | **Prompt injection** from JDs, web pages, emails, LinkedIn profiles | Stated in every skill; Gmail is read-only; skills never follow instructions from content, never click email links, and note the attempt. Residual risk: models can still be fooled, so apply stays human-started and dry-run first. |
| C2 | Agent enters credentials or creates accounts | Forbidden in the apply skill. You log in yourself; no passwords exist in any file. |
| C3 | Sensitive resume and contact data leaking | Everything is in your private folder; skills do not send data to third-party services, and external searches use company names and job titles only. Do not install third-party browser extensions that read the folder. |
| C4 | Third-party personal data (referral contacts) | Only name, role, public link, and a public email with its source. No guessed emails, no paid lookups. |
| C5 | Account bans (Naukri quotas, LinkedIn prohibits automation) | Low caps (3 per portal per day to start), human-like pauses, your own network and browser. **LinkedIn view-only lookups still carry some risk.** Set `linkedin_lookup: false` to remove it. |
| C6 | A scheduled run applying unattended | `allow_scheduled_apply: false`, and the apply skill refuses unattended starts. |
| C7 | The helper scripts in `tools/` being swapped for malicious ones | They live in your private folder only. Do not copy scripts from others into it. |
| C8 | Kill switch | `PAUSE_ALL: true` as the first line of `preferences.md` stops every skill at step 0 (tested: exit 10). |

## C2. Company-site applications (added 21 Nov 2026)

| # | Risk | Mitigation |
|---|---|---|
| C9 | Typing your details into a fake or unrelated employer site (many Naukri listings are copied from elsewhere) | Domain must match the company; listings marked `verify company` need your explicit yes per job; confirm-before-submit is on by default. |
| C10 | Account creation, OTP, CAPTCHA, assessment on the employer site | Hard stop, job stays manual. |
| C11 | Government IDs, bank or card details requested | Never entered, even if asked; job stays manual. |
| C12 | Consent tick-boxes and privacy policies accepted without you knowing | Listed in the pre-submit summary; marketing opt-ins never ticked. |
| C13 | Wrong or invented answers in free-text boxes | Only your own pre-written text from `form_profile.md` can be pasted; otherwise manual. |
| C14 | Personal data spread across many sites | Cap of 5 company-site applications per day; only fields marked `fill: yes`; DOB, address, pincode and reason for leaving stay unfilled until you approve them. |
| C16 | **Observed 21 Nov 2026:** clicking Naukri's "Apply on company site" in a dry run registered a real Naukri application with the profile resume | Skill now forbids that click in dry run and requires your yes in a real run; employer URLs are found via web search instead. |
| C15 | Prompt injection inside employer pages or forms | Page content is data; any odd instruction is ignored and noted. |

## D. Remaining risks you should know about

1. **Instruction-following is not a guarantee.** The rules are strong but not a sandbox. Keep dry-run on until you have inspected several runs.
2. **Scheduled tasks need the desktop app awake and open** for anything using your browser or local files. If the computer is off, runs are skipped (no usage burned).
3. **Gmail connector names and Chrome extension versions change.** Re-verify the setup list in `SETUP_GUIDE.md` before the first run.
4. **Portal layouts change.** When a portal's apply flow changes, the correct behaviour is to flag MANUAL_REQUIRED, not to guess.
5. **Terms of service.** Portals restrict automation. Keep volumes low. This is your decision and your account.
6. **Quality of scoring** depends on the rubric. Calibrate in build step 4 on 30 jobs.
