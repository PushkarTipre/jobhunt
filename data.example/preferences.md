PAUSE_ALL: false

# Preferences (edit freely; skills read the `key: value` lines)

KILL SWITCH: change the first line to `PAUSE_ALL: true` and every skill stops at its first step.

## Targets (jh-profile-builder will refine these from your resume; you approve)
target_titles_primary: AI Engineer, Machine Learning Engineer
target_titles_acceptable: Data Scientist, NLP Engineer, MLOps Engineer
role_focus: AI/ML/GenAI engineering (LLM apps, RAG, model training and deployment)   # the kind of work every skill scores and searches for
keywords_include: Python, LLM, PyTorch
keywords_avoid: telecaller, data entry, sales, registration fee, unpaid, commission only, MLM
locations: <your city>, Remote
work_mode: remote anywhere; hybrid or onsite only in <your city>
experience_years_min: 0
experience_years_max: 3
experience_tolerance_years: 1
min_salary_lpa: 0
company_types: product companies, startups
companies_exclude: none
notice_period_days: 30
notice_negotiable: yes
relocation_min_lpa: 15
freshness_days: 7

## Score thresholds
shortlist_min: 75
borderline_min: 60
referral_min_score: 80

## RUN BUDGETS (protect your Claude usage; raise only after clean weeks)
scan_max_tool_calls: 120
discovery_max_queries: 6
discovery_max_pages_per_query: 2
discovery_max_new_jobs_per_run: 30
scoring_max_jobs_per_run: 25
tailor_max_per_run: 6
apply_max_per_session: 10
apply_cap_per_portal_per_day: 3
apply_max_browser_actions_per_job: 25
apply_stop_after_consecutive_failures: 2
max_attempts_per_job: 3
apply_dry_run: true                 # true = fill forms but NEVER submit. Switch to false only after inspecting dry runs.
referral_max_jobs_per_run: 5
max_contacts_per_job: 3
referral_max_profile_views_per_run: 10
linkedin_lookup: true
verify_max_emails_read: 30
verify_min_hours_between_runs: 6
interview_max_web_searches: 3
stale_days: 30

## Company-site applications
apply_company_sites: true
company_site_confirm_before_submit: true
company_site_cap_per_day: 5
company_site_require_domain_match: true

## Unattended runs
allow_scheduled_apply: false
