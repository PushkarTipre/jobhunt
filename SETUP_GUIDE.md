# Setup guide: Claude Desktop (Windows)

Menu names change between versions. If a label differs, look for the closest one. Re-verify the platform notes in blueprint Section 3 first.

## What you have

```
JobHunt/
  SETUP_GUIDE.md, RISK_REVIEW.md
  data/        preferences.md, answers_bank.md, portals.md  (resume + master_profile come next)
  tools/       tracker.py, truth_check.py, make_resume_tex.py, bin/tectonic
  skills/      11 skill folders (source)
  dist/        11 ready-to-upload ZIPs  <- these go into Claude
  build_zips.py
```

## Step 1: Put the folder somewhere permanent
Move the whole `JobHunt` folder to e.g. `C:\Users\<you>\Documents\JobHunt`. (This session's scratch folder is deleted with the session.) Copy your resume to `JobHunt\data\resume_original.pdf`.

## Step 2: Python libraries (once)
The tracker needs `openpyxl`, the resume PDF needs `reportlab`, and reading your resume needs `pdfplumber` or `pypdf`.
```powershell
pip install openpyxl pdfplumber pypdf
```
If Claude runs code in its own sandbox it may install them itself; if it reports a missing library, ask it to run the same pip command.

### LaTeX resume engine (Tectonic)
Tailored resumes are produced from your own LaTeX template `data/resume_original_latex.tex`, so the design never changes. `tools/bin/tectonic/tectonic.exe` compiles it locally; nothing is uploaded anywhere. Download `tectonic-0.17.0-x86_64-pc-windows-msvc.zip` from the official GitHub releases of tectonic-typesetting/tectonic and put `tectonic.exe` in that folder. The first compile downloads LaTeX packages once. On macOS, run `brew install tectonic` instead (the tools find it on your PATH).

## Step 3: Claude settings
1. **Settings > Capabilities**: switch on **Code execution and file creation** (needed for skills).
2. Make sure **Claude in Chrome** is installed and signed in (Chrome Web Store, "Claude" extension) and that Claude Desktop shows it connected. Test it: ask Claude to open a tab.
3. **Settings > Connectors**: connect **Gmail** (read-only). Test it: ask "show the subject of my latest email".

## Step 4: Upload the skills
**Customize > Skills > upload**, one ZIP at a time from `JobHunt\dist\`:
`jh-tracker, jh-profile-builder, jh-discovery, jh-scoring-vetting, jh-resume-tailor, jh-apply-assistant, jh-email-verifier, jh-interview-brief, jh-referral-finder, jh-weekly-review, jh-orchestrator`.
Do the first six now if you prefer, the rest later (build order is in the blueprint). Make sure each shows as enabled.

## Step 5: Open the working folder in Cowork
In Cowork (or Claude Code tab) choose `JobHunt` as the working folder, so skills can read `data/` and run `tools/tracker.py`.

## Step 6: Create the tracker (blueprint build step 1)
Say: **"Set up my job-hunt tracker."** Expect `tracker.xlsx` with tabs Applications, Contacts, Run Log, Dashboard, Settings. Open it in Excel to look, then **close Excel** before any run (an open file blocks writes; Claude will tell you if so).

## Step 7: Build the profile (step 2)
Say: **"Build my master profile from my resume."** Answer its questions, then review `master_profile.md` line by line. Give it your GitHub and portfolio links at this point. Approve `master_profile.md`, `answers_bank.md`, `preferences.md`. Also answer: is the 30-day notice negotiable?

## Step 8: Log in to portals yourself
In Chrome log in to Naukri, Foundit, Instahyre, Hirist, Cutshort, Wellfound. Update the "Logged in?" column in `portals.md` (or tell Claude).

## Step 9: Walk the build order (blueprint Section 10) with the caps unchanged
1. Discovery on ONE portal ("Find jobs on Naukri"). Check rows and `jd/` files.
2. Scoring on about 30 jobs; compare to your judgment; tune `skills\jh-scoring-vetting\references\rubric.md` (then rebuild that ZIP and re-upload).
3. Resume tailor; read three outputs against your profile.
4. Email verifier with a few real confirmation emails.
5. Referral finder on five jobs.
6. Apply assistant in **dry run** (`apply_dry_run: true` stays). Inspect.
7. Then set `apply_dry_run: false` and apply on ONE portal with cap 3 per day. Check proof screenshots and confirmations.
8. Only then the orchestrator and schedules.

## Step 10: Schedule (only after a clean week of manual runs)
Cowork scheduled tasks (cloud tasks that need your browser or local files also need the desktop app open):
- Scan, once daily, e.g. 09:00: prompt `Run my job hunt in scan mode.`
- Verify, twice daily, e.g. 10:00 and 18:00: prompt `Run my job hunt in verify mode.`
- **Do not schedule apply.** Start apply sessions yourself.

## Day-to-day
- "Run my job hunt" (scan, then it asks before applying)
- "Apply session" (you present, Chrome open)
- "Check confirmations"
- "Prep me for <company>"
- "I applied to JH-20261120-004 by hand" (records SUBMITTED so it gets verified)
- "Weekly review"
- Open `tracker.xlsx` (Excel closed to Claude when you do): orange = you must apply, red = check it.

## Kill switch and backups
- Stop everything: make the first line of `data\preferences.md` read `PAUSE_ALL: true`.
- Weekly: copy `tracker.xlsx` and the `data` folder outside Claude. Daily automatic copies of the tracker are in `logs\backups`.

## Changing a skill
Edit its `SKILL.md` in `skills\`, run `python build_zips.py`, re-upload that ZIP in Customize > Skills.
