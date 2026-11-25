# JobHunt: a job-hunt assistant built from Claude skills

A set of 11 Claude skills plus a few small Python tools that run a careful, budgeted job hunt: discover postings, score and vet them, tailor your resume truthfully, apply only where the form is simple and safe, verify confirmations through read-only Gmail, find referral contacts, and prep you for interviews.

It never applies from a scheduled task, never sends messages for you, never stores passwords, and keeps everything in local files (`tracker.xlsx` plus markdown in `data/`).

## What's in this repo

| Path | Purpose |
|---|---|
| `skills/` | Source of the 11 skills (`jh-orchestrator`, `jh-discovery`, `jh-scoring-vetting`, `jh-resume-tailor`, `jh-apply-assistant`, `jh-email-verifier`, `jh-referral-finder`, `jh-interview-brief`, `jh-weekly-review`, `jh-profile-builder`, `jh-tracker`) |
| `tools/` | `tracker.py` (the only code that touches the spreadsheet), `make_resume_tex.py` (LaTeX to PDF resume), `truth_check.py` (flags resume claims not in your profile) |
| `data.example/` | Blank templates for your personal files: preferences, answers bank, form profile, portals |
| `build_zips.py` | Packs each skill folder into `dist/<name>.zip` for upload |
| `SETUP_GUIDE.md` | Detailed step-by-step Claude Desktop setup |
| `RISK_REVIEW.md` | Design notes on loops, usage burn and safety guards |

Your personal files (`data/`, `tracker.xlsx`, `resumes/`, `jd/`, `logs/`, `proof/`) are git-ignored and never leave your machine.

## Requirements

- Claude Desktop (Pro or higher) with **Code execution and file creation** enabled, and Cowork or the Code tab
- Claude in Chrome extension (for discovery and applying)
- Gmail connector, read-only (for confirmation checks)
- Python 3.9+ and: `pip install openpyxl pdfplumber pypdf`
- [Tectonic](https://github.com/tectonic-typesetting/tectonic/releases) (LaTeX engine) placed at `tools/bin/tectonic/tectonic.exe` (Windows) or on your PATH (macOS: `brew install tectonic`)
- A LaTeX version of your resume (see step 3)

## Setup

1. **Clone**
   ```powershell
   git clone https://github.com/<your-username>/<repo-name>.git JobHunt
   cd JobHunt
   ```
2. **Create your private data folder**
   ```powershell
   Copy-Item -Recurse data.example data
   New-Item -ItemType Directory -Force jd, resumes, logs, proof, interviews
   ```
   Edit `data/preferences.md`, `data/answers_bank.md`, `data/form_profile.md` and `data/portals.md` with your own details (every `<placeholder>` and `TO_BE_CONFIRMED`).
3. **Add your resume**: save the PDF as `data/resume_original.pdf` and a LaTeX version as `data/resume_original_latex.tex`. The tailor reuses your template's design and only rewrites the Summary, Skills, Experience and Projects sections (see the top of `tools/make_resume_tex.py` for the JSON shape).
4. **Build the skill ZIPs**
   ```powershell
   python build_zips.py
   ```
5. **Upload the skills**: Claude Desktop, Customize > Skills > upload each ZIP from `dist/`, and make sure all 11 are enabled.
6. **Open the `JobHunt` folder** as the working folder in Cowork or the Claude Code tab.
7. **Create the tracker**: say *"Set up my job-hunt tracker."*
8. **Build your profile**: say *"Build my master profile from my resume."* Answer its questions and review `data/master_profile.md` line by line.
9. **Log in to job portals yourself** in Chrome (Naukri, Foundit, Instahyre, etc.). No passwords are stored anywhere.

Full detail, including the recommended build order and scheduling, is in [SETUP_GUIDE.md](SETUP_GUIDE.md).

## Usage

| Say | What happens |
|---|---|
| "Run my job hunt" | Scan mode: discover, score, tailor resumes, find referrals |
| "Apply session" | Fills simple, safe forms with you present |
| "Check confirmations" | Reads Gmail (read-only) to confirm submissions and spot replies |
| "Prep me for <company>" | One-screen interview brief |
| "Weekly review" | Stats, learning gaps, suggestions |

## Safety defaults

- `apply_dry_run: true` in `data/preferences.md`: forms are filled but **never submitted** until you switch it off after inspecting dry runs.
- Kill switch: set the first line of `data/preferences.md` to `PAUSE_ALL: true`.
- Per-run budgets and daily apply caps are set in preferences to protect your Claude usage.
- Never auto-fills salary breakups, sensitive/EEO fields, government IDs, bank details, or free-text essays.

## Customizing

Edit a skill's `SKILL.md`, run `python build_zips.py`, and re-upload that ZIP. Set `role_focus`, the target titles and `keywords_include` in `data/preferences.md` to your field: discovery, scoring, tailoring, referrals and interview prep all read them. Then adjust the role-fit examples in `skills/jh-scoring-vetting/references/rubric.md` (they currently describe Flutter/mobile roles). The default portals target India.

## Privacy

Do not commit `data/`, `tracker.xlsx`, `resumes/`, `jd/` or `logs/`. They contain your contact details, CTC and application history. The included `.gitignore` already excludes them.

## Disclaimer

Automated applying may violate some portals' terms of service. You are responsible for how you use this. LinkedIn automation is intentionally not supported.
