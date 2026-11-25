#!/usr/bin/env python3
"""
JobHunt tracker tool. The ONLY code that reads or writes tracker.xlsx.

Why this exists: every skill calls this instead of editing the spreadsheet itself, so
(1) column names live in one place, (2) status transitions are enforced in code,
(3) writes are atomic, backed up and refuse to run while the file is open in Excel,
(4) the kill switch (PAUSE_ALL) and run budgets are read the same way everywhere,
(5) Claude spends tokens on decisions, not on spreadsheet plumbing.

Usage:  python tools/tracker.py --root . <command> [options]
All commands print ONE JSON object. Exit codes:
  0 ok | 1 error | 2 transition/field not allowed | 3 tracker locked (open in Excel)
  4 not found | 10 PAUSE_ALL is on (stop everything)
"""
import argparse, collections, datetime as dt, json, os, re, shutil, sys

try:
    from openpyxl import Workbook, load_workbook
    from openpyxl.formatting.rule import FormulaRule
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
except ImportError:
    print(json.dumps({"ok": False, "error": "openpyxl missing. Run: pip install openpyxl"}))
    sys.exit(1)

APP, CON, LOG, DASH, SETT = "Applications", "Contacts", "Run Log", "Dashboard", "Settings"

COLS = [
    "Job ID", "Date found", "Portal", "Company", "Title", "Location / mode",
    "Experience / salary", "JD link", "Apply link", "Apply type", "Fit score",
    "Score reason", "Matched skills", "Missing skills", "Resume file", "Resume used",
    "Status", "Applied date and time", "Proof", "Confirmation",
    "Interview stage / date", "Follow-up date", "Manual action reason", "Notes",
    "Referral possible", "Contact", "Dedup key", "JD file", "Attempts", "Last updated",
]
CON_COLS = [
    "Contact ID", "Job ID", "Company", "Name", "Role", "Relation type", "Profile link",
    "Public email", "Email source", "Why relevant", "Outreach draft", "Outreach status",
    "Date contacted", "Notes",
]
STATUSES = ["FOUND", "SHORTLISTED", "RESUME_READY", "SUBMITTED", "CONFIRMED", "SKIPPED",
            "MANUAL_REQUIRED", "FAILED", "NO_CONFIRMATION", "REJECTED", "INTERVIEW",
            "OFFER", "CLOSED"]
APPLIED_STATES = ["SUBMITTED", "CONFIRMED", "NO_CONFIRMATION", "INTERVIEW"]
RESPONSE_STATES = ["REJECTED", "INTERVIEW", "OFFER"]

COLOURS = {  # status -> fill hex (applied as conditional formatting, so it is automatic)
    "MANUAL_REQUIRED": "F8CBAD", "NO_CONFIRMATION": "F4B6B6", "FAILED": "F4B6B6",
    "SUBMITTED": "C6E0B4", "CONFIRMED": "C6E0B4", "INTERVIEW": "BDD7EE", "OFFER": "BDD7EE",
    "SKIPPED": "D9D9D9", "REJECTED": "D9D9D9", "CLOSED": "D9D9D9",
}

ANY = "*"
def _t(frm, to):
    return {(f, t) for f in frm for t in to}

TRANSITIONS = {
    "jh-discovery": {(None, "FOUND")},
    "jh-scoring-vetting": _t(["FOUND"], ["SHORTLISTED", "SKIPPED"]),
    "jh-resume-tailor": _t(["SHORTLISTED"], ["RESUME_READY"]),
    "jh-apply-assistant": (_t(["RESUME_READY"], ["SUBMITTED", "MANUAL_REQUIRED", "FAILED"])
                           # company-site applications start from MANUAL_REQUIRED rows (apply_company_sites: true)
                           | _t(["MANUAL_REQUIRED"], ["SUBMITTED", "FAILED"])),
    "jh-email-verifier": (
        _t(["SUBMITTED"], ["CONFIRMED", "NO_CONFIRMATION"])
        | _t(["NO_CONFIRMATION"], ["CONFIRMED"])
        | _t(APPLIED_STATES, ["REJECTED", "INTERVIEW"])
        | _t(["INTERVIEW"], ["OFFER"])
    ),
    "jh-tracker": _t(["FOUND", "SHORTLISTED", "RESUME_READY"], ["CLOSED"]),
    "jh-referral-finder": set(),   # never changes status
    "jh-weekly-review": set(),
    "user": {(ANY, ANY)},          # the human can do anything (e.g. MANUAL_REQUIRED -> SUBMITTED)
}
FIELD_RULES = {  # which columns each actor may write (Notes via `note` is always allowed)
    "jh-discovery": {"Date found", "Portal", "Company", "Title", "Location / mode",
                     "Experience / salary", "JD link", "Apply link", "Apply type",
                     "JD file", "Dedup key", "Notes"},
    "jh-scoring-vetting": {"Fit score", "Score reason", "Matched skills", "Missing skills",
                           "Notes", "Manual action reason"},
    "jh-resume-tailor": {"Resume file", "Resume used", "Notes"},
    "jh-apply-assistant": {"Applied date and time", "Proof", "Manual action reason",
                           "Apply type", "Apply link", "Notes"},
    "jh-email-verifier": {"Confirmation", "Interview stage / date", "Notes"},
    "jh-referral-finder": {"Referral possible", "Contact", "Notes"},
    "jh-weekly-review": set(),
    "jh-tracker": set(COLS),
    "user": set(COLS),
}
ALIASES = {
    "company": "Company", "title": "Title", "portal": "Portal", "location": "Location / mode",
    "experience_salary": "Experience / salary", "jd_link": "JD link",
    "apply_link": "Apply link", "apply_type": "Apply type", "jd_file": "JD file",
    "notes": "Notes", "date_found": "Date found",
}
MAX_NOTES = 2000


# ----------------------------------------------------------------------------- helpers
class Fail(Exception):
    def __init__(self, msg, code=1):
        super().__init__(msg)
        self.code = code


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False, default=str))
    sys.exit(code)


def now():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def today():
    return dt.date.today().isoformat()


def norm(s):
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", str(s or "").lower())).strip()


def norm_company(s):
    s = norm(s)
    s = re.sub(r"\b(pvt|private|ltd|limited|llp|inc|llc|technologies|technology|india)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_loc(s):
    first = re.split(r"[,/(|;-]", str(s or ""))[0]
    return norm(first)


def dedup_key(company, title, location):
    return f"{norm_company(company)}|{norm(title)}|{norm_loc(location)}"


def norm_url(u):
    u = str(u or "").strip().lower()
    u = re.sub(r"[?#].*$", "", u)
    return u.rstrip("/")


class Paths:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.tracker = os.path.join(self.root, "tracker.xlsx")
        self.prefs = os.path.join(self.root, "data", "preferences.md")
        self.backups = os.path.join(self.root, "logs", "backups")


# ----------------------------------------------------------------------------- workbook
def style_header(ws, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F3864")
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(c)].width = 18
    ws.freeze_panes = "A2"


def create_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = APP
    ws.append(COLS)
    style_header(ws, len(COLS))
    for name, w in [("Company", 24), ("Title", 32), ("Score reason", 50), ("Notes", 50),
                    ("JD link", 36), ("Apply link", 36), ("Manual action reason", 36),
                    ("Matched skills", 28), ("Missing skills", 28)]:
        ws.column_dimensions[get_column_letter(COLS.index(name) + 1)].width = w
    scol = get_column_letter(COLS.index("Status") + 1)
    last = get_column_letter(len(COLS))
    for status, hexcol in COLOURS.items():
        ws.conditional_formatting.add(
            f"A2:{last}2000",
            FormulaRule(formula=[f'${scol}2="{status}"'], fill=PatternFill("solid", bgColor=hexcol, fgColor=hexcol)))
    dv = DataValidation(type="list", formula1='"' + ",".join(STATUSES) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{scol}2:{scol}2000")

    cs = wb.create_sheet(CON)
    cs.append(CON_COLS)
    style_header(cs, len(CON_COLS))
    for name, w in [("Outreach draft", 60), ("Why relevant", 36), ("Profile link", 36)]:
        cs.column_dimensions[get_column_letter(CON_COLS.index(name) + 1)].width = w

    ls = wb.create_sheet(LOG)
    ls.append(["Timestamp", "Mode", "Counts", "Errors"])
    style_header(ls, 4)
    ls.column_dimensions["C"].width = 60
    ls.column_dimensions["D"].width = 60

    ds = wb.create_sheet(DASH)
    ds.append(["Status", "Count"])
    style_header(ds, 2)
    for i, s in enumerate(STATUSES, start=2):
        ds.cell(row=i, column=1, value=s)
        ds.cell(row=i, column=2, value=f'=COUNTIF({APP}!${scol}:${scol},A{i})')
    r = len(STATUSES) + 3
    ds.cell(row=r, column=1, value="Portal").font = Font(bold=True)
    ds.cell(row=r, column=2, value="Total rows").font = Font(bold=True)
    ds.cell(row=r, column=3, value="Applied (submitted or later)").font = Font(bold=True)
    pcol = get_column_letter(COLS.index("Portal") + 1)
    for j, p in enumerate(["Naukri", "Foundit", "Instahyre", "Hirist", "Cutshort", "Wellfound", "Company site", "LinkedIn"], start=r + 1):
        ds.cell(row=j, column=1, value=p)
        ds.cell(row=j, column=2, value=f'=COUNTIF({APP}!${pcol}:${pcol},A{j})')
        ds.cell(row=j, column=3, value="=" + "+".join(
            f'COUNTIFS({APP}!${pcol}:${pcol},A{j},{APP}!${scol}:${scol},"{s}")' for s in APPLIED_STATES + ["REJECTED", "OFFER"]))
    ds.column_dimensions["A"].width = 22
    ds.column_dimensions["C"].width = 28

    st = wb.create_sheet(SETT)
    st.append(["Status list (read-only reference)", "Meaning"])
    style_header(st, 2)
    meanings = {
        "FOUND": "Discovered, not yet scored", "SHORTLISTED": "Good match (borderline ones noted)",
        "RESUME_READY": "Resume chosen (base or tailored)", "SUBMITTED": "Agent submitted the application",
        "CONFIRMED": "Confirmation email or portal 'applied' status seen", "SKIPPED": "Poor fit or suspicious",
        "MANUAL_REQUIRED": "YOU must apply (reason in Manual action reason)", "FAILED": "Error during apply, check it",
        "NO_CONFIRMATION": "Submitted but nothing verified, check it", "REJECTED": "Rejection received",
        "INTERVIEW": "Interview invite received", "OFFER": "Offer received", "CLOSED": "Done or stale"}
    for s in STATUSES:
        st.append([s, meanings[s]])
    st.column_dimensions["A"].width = 30
    st.column_dimensions["B"].width = 60
    return wb


def load():
    p = PATHS
    if not os.path.exists(p.tracker):
        raise Fail("tracker.xlsx not found. Run: python tools/tracker.py --root . init", 4)
    return load_workbook(p.tracker)


def save(wb):
    p = PATHS
    lock = os.path.join(p.root, "~$tracker.xlsx")
    if os.path.exists(lock):
        raise Fail("tracker.xlsx appears to be open in Excel. Close it and retry. Nothing was written.", 3)
    os.makedirs(p.backups, exist_ok=True)
    stamp = os.path.join(p.backups, f"tracker_{today()}.xlsx")
    if os.path.exists(p.tracker) and not os.path.exists(stamp):
        shutil.copy2(p.tracker, stamp)
        for old in sorted(os.listdir(p.backups))[:-14]:
            try:
                os.remove(os.path.join(p.backups, old))
            except OSError:
                pass
    tmp = p.tracker + ".tmp"
    wb.save(tmp)
    try:
        os.replace(tmp, p.tracker)
    except PermissionError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise Fail("tracker.xlsx is locked (open in Excel?). Close it and retry. Nothing was written.", 3)


def rows(ws, cols):
    """Yield (row_index, dict) for data rows."""
    idx = {c: i for i, c in enumerate(cols)}
    for r in range(2, ws.max_row + 1):
        vals = [ws.cell(row=r, column=c + 1).value for c in range(len(cols))]
        if any(v not in (None, "") for v in vals):
            yield r, {c: vals[i] for c, i in idx.items()}


def write_cell(ws, r, cols, name, value):
    ws.cell(row=r, column=cols.index(name) + 1, value=value)


def find_row(ws, job_id):
    for r, d in rows(ws, COLS):
        if d["Job ID"] == job_id:
            return r, d
    raise Fail(f"Job ID {job_id} not found", 4)


def parse_kv(pairs):
    d = {}
    for p in pairs or []:
        if "=" not in p:
            raise Fail(f"--set expects key=value, got: {p}")
        k, v = p.split("=", 1)
        d[k.strip()] = v.strip()
    return d


def check_fields(actor, fields):
    allowed = FIELD_RULES.get(actor)
    if allowed is None:
        raise Fail(f"unknown actor {actor}", 2)
    bad = [k for k in fields if k not in COLS]
    if bad:
        raise Fail(f"unknown column(s): {bad}", 2)
    denied = [k for k in fields if k not in allowed]
    if denied:
        raise Fail(f"actor {actor} may not write column(s): {denied}", 2)


def append_note_text(old, text):
    text = str(text).strip()[:300]
    new = (str(old) + " | " if old else "") + f"[{today()}] {text}"
    return new[-MAX_NOTES:]


# ----------------------------------------------------------------------------- preferences
def read_prefs():
    prefs, paused = {}, False
    if not os.path.exists(PATHS.prefs):
        return prefs, paused, False
    with open(PATHS.prefs, encoding="utf-8") as f:
        for line in f:
            if re.match(r"^\s*PAUSE_ALL\s*:\s*true\b", line, re.I):
                paused = True
            m = re.match(r"^[-*\s]*([a-z][a-z0-9_]*)\s*:\s*([^#\n]+?)\s*(#.*)?$", line)
            if m:
                prefs[m.group(1)] = m.group(2).strip()
    return prefs, paused, True


# ----------------------------------------------------------------------------- commands
def cmd_init(a):
    for d in ["data", "resumes", "proof", "jd", "interviews", "logs", "tools"]:
        os.makedirs(os.path.join(PATHS.root, d), exist_ok=True)
    if os.path.exists(PATHS.tracker):
        out({"ok": True, "created": False, "note": "tracker.xlsx already exists; left untouched"})
    wb = create_workbook()
    save(wb)
    out({"ok": True, "created": True, "path": PATHS.tracker})


def cmd_preflight(a):
    prefs, paused, found = read_prefs()
    res = {"ok": True, "paused": paused, "prefs_found": found,
           "tracker_exists": os.path.exists(PATHS.tracker), "prefs": prefs}
    if a.mode and os.path.exists(PATHS.tracker):
        res["last_run"] = last_run(a.mode)
    if paused:
        res["ok"] = False
        res["error"] = "PAUSE_ALL is true in data/preferences.md. Stop immediately and tell the user."
        out(res, 10)
    out(res)


def last_run(mode):
    wb = load()
    ws = wb[LOG]
    last = None
    for _, d in rows(ws, ["Timestamp", "Mode", "Counts", "Errors"]):
        if d["Mode"] == mode:
            last = d["Timestamp"]
    return last


def cmd_add(a):
    data = json.load(open(a.json_file, encoding="utf-8")) if a.json_file else json.loads(a.json)
    rec = {ALIASES.get(k, k): v for k, v in data.items()}
    check_fields("jh-discovery", [k for k in rec])
    for need in ("Company", "Title", "JD link"):
        if not rec.get(need):
            raise Fail(f"missing required field: {need}")
    wb = load()
    ws = wb[APP]
    key = dedup_key(rec["Company"], rec["Title"], rec.get("Location / mode", ""))
    url = norm_url(rec["JD link"])
    max_id = 0
    for r, d in rows(ws, COLS):
        m = re.search(r"-(\d+)$", str(d["Job ID"] or ""))
        max_id = max(max_id, int(m.group(1)) if m else 0)
        if d["Dedup key"] == key or norm_url(d["JD link"]) == url:
            if norm_url(d["JD link"]) != url:
                extra = f"Also on {rec.get('Portal', '?')}: {rec['JD link']}"
                if extra not in str(d["Notes"] or ""):
                    write_cell(ws, r, COLS, "Notes", append_note_text(d["Notes"], extra))
                    save(wb)
            out({"ok": True, "duplicate": True, "job_id": d["Job ID"], "status": d["Status"]})
    job_id = f"JH-{dt.date.today():%Y%m%d}-{max_id + 1:03d}"
    rec.setdefault("Date found", today())
    rec["Dedup key"] = key
    rec["Job ID"], rec["Status"], rec["Attempts"], rec["Last updated"] = job_id, "FOUND", 0, now()
    ws.append([rec.get(c) for c in COLS])
    save(wb)
    out({"ok": True, "duplicate": False, "job_id": job_id})


def cmd_find(a):
    wb = load()
    ws = wb[APP]
    for r, d in rows(ws, COLS):
        if (a.url and norm_url(d["JD link"]) == norm_url(a.url)) or (a.key and d["Dedup key"] == a.key):
            out({"ok": True, "found": True, "job_id": d["Job ID"], "status": d["Status"]})
    out({"ok": True, "found": False})


DEFAULT_FIELDS = ["Job ID", "Company", "Title", "Status", "Fit score", "Apply type", "Attempts"]


def cmd_list(a):
    wb = load()
    ws = wb[APP]
    want = set(a.status.split(",")) if a.status else None
    fields = a.fields.split(",") if a.fields else DEFAULT_FIELDS
    bad = [f for f in fields if f not in COLS]
    if bad:
        raise Fail(f"unknown fields {bad}")
    res = []
    for _, d in rows(ws, COLS):
        if want and d["Status"] not in want:
            continue
        score = d["Fit score"] if isinstance(d["Fit score"], (int, float)) else -1
        if a.min_score is not None and score < a.min_score:
            continue
        if a.max_attempts is not None and int(d["Attempts"] or 0) > a.max_attempts:
            continue
        if a.referral_empty and d["Referral possible"] not in (None, ""):
            continue
        if a.days is not None:
            ref = str(d["Applied date and time"] or d["Date found"] or "")[:10]
            try:
                if (dt.date.today() - dt.date.fromisoformat(ref)).days > a.days:
                    continue
            except ValueError:
                pass
        res.append((score, {f: d[f] for f in fields}))
    if a.order == "score":
        res.sort(key=lambda x: -x[0])
    items = [x[1] for x in res][: a.limit]
    out({"ok": True, "total_matching": len(res), "returned": len(items), "rows": items})


def cmd_get(a):
    wb = load()
    _, d = find_row(wb[APP], a.id)
    out({"ok": True, "row": d})


def cmd_set_status(a):
    actor, to = a.actor, a.to
    if to not in STATUSES:
        raise Fail(f"unknown status {to}", 2)
    extra = parse_kv(a.set)
    check_fields(actor, extra)
    wb = load()
    ws = wb[APP]
    r, d = find_row(ws, a.id)
    frm = d["Status"]
    ok = TRANSITIONS.get(actor)
    if ok is None:
        raise Fail(f"unknown actor {actor}", 2)
    if not ((frm, to) in ok or (ANY, ANY) in ok):
        raise Fail(f"transition {frm} -> {to} not allowed for {actor}", 2)
    if actor == "jh-apply-assistant" and int(d["Attempts"] or 0) >= int(read_prefs()[0].get("max_attempts_per_job", 3)):
        raise Fail("max attempts reached for this job; leave it for the human", 2)
    write_cell(ws, r, COLS, "Status", to)
    for k, v in extra.items():
        if k in ("Fit score", "Attempts"):
            try:
                v = int(float(v))
            except ValueError:
                raise Fail(f"{k} must be a number")
        write_cell(ws, r, COLS, k, v)
    if actor == "jh-apply-assistant":
        write_cell(ws, r, COLS, "Attempts", int(d["Attempts"] or 0) + 1)
    if a.note:
        write_cell(ws, r, COLS, "Notes", append_note_text(extra.get("Notes", d["Notes"]) if "Notes" not in extra else d["Notes"], a.note))
    write_cell(ws, r, COLS, "Last updated", now())
    save(wb)
    out({"ok": True, "job_id": a.id, "from": frm, "to": to})


def cmd_set(a):
    extra = parse_kv(a.set)
    check_fields(a.actor, extra)
    wb = load()
    ws = wb[APP]
    r, d = find_row(ws, a.id)
    for k, v in extra.items():
        if k in ("Fit score", "Attempts"):
            v = int(float(v))
        write_cell(ws, r, COLS, k, v)
    write_cell(ws, r, COLS, "Last updated", now())
    save(wb)
    out({"ok": True, "job_id": a.id, "updated": list(extra)})


def cmd_note(a):
    wb = load()
    ws = wb[APP]
    r, d = find_row(ws, a.id)
    write_cell(ws, r, COLS, "Notes", append_note_text(d["Notes"], a.text))
    write_cell(ws, r, COLS, "Last updated", now())
    save(wb)
    out({"ok": True, "job_id": a.id})


def cmd_attempt(a):
    """Count one attempt without changing status (used by dry runs so a row is never re-tried forever)."""
    wb = load()
    ws = wb[APP]
    r, d = find_row(ws, a.id)
    n = int(d["Attempts"] or 0) + 1
    write_cell(ws, r, COLS, "Attempts", n)
    if a.text:
        write_cell(ws, r, COLS, "Notes", append_note_text(d["Notes"], a.text))
    write_cell(ws, r, COLS, "Last updated", now())
    save(wb)
    out({"ok": True, "job_id": a.id, "attempts": n})


def cmd_add_contact(a):
    data = json.load(open(a.json_file, encoding="utf-8")) if a.json_file else json.loads(a.json)
    for need in ("Job ID", "Name", "Relation type"):
        if not data.get(need):
            raise Fail(f"missing required field: {need}")
    if data.get("Public email") and not data.get("Email source"):
        raise Fail("Public email requires Email source (never store guessed emails)")
    bad = [k for k in data if k not in CON_COLS]
    if bad:
        raise Fail(f"unknown contact column(s): {bad}")
    wb = load()
    ws, cs = wb[APP], wb[CON]
    r, job = find_row(ws, data["Job ID"])
    existing, max_id = [], 0
    for _, c in rows(cs, CON_COLS):
        m = re.search(r"-(\d+)$", str(c["Contact ID"] or ""))
        max_id = max(max_id, int(m.group(1)) if m else 0)
        if c["Job ID"] == data["Job ID"]:
            existing.append(c)
    for c in existing:
        same_link = data.get("Profile link") and c["Profile link"] == data.get("Profile link")
        if same_link or norm(c["Name"]) == norm(data["Name"]):
            out({"ok": True, "duplicate": True, "contact_id": c["Contact ID"]})
    cap = int(read_prefs()[0].get("max_contacts_per_job", 3))
    if len(existing) >= cap:
        raise Fail(f"already {cap} contacts for this job (cap reached)", 2)
    cid = f"C-{max_id + 1:03d}"
    data["Contact ID"] = cid
    data["Company"] = data.get("Company") or job["Company"]
    data.setdefault("Outreach status", "Not contacted")
    cs.append([data.get(c) for c in CON_COLS])
    write_cell(ws, r, COLS, "Referral possible", "Yes")
    ids = [x for x in str(job["Contact"] or "").split(",") if x.strip()] + [cid]
    write_cell(ws, r, COLS, "Contact", ", ".join(ids))
    write_cell(ws, r, COLS, "Last updated", now())
    save(wb)
    out({"ok": True, "duplicate": False, "contact_id": cid})


def cmd_list_contacts(a):
    wb = load()
    res = [c for _, c in rows(wb[CON], CON_COLS) if not a.job or c["Job ID"] == a.job]
    out({"ok": True, "contacts": res})


def cmd_update_contact(a):
    extra = parse_kv(a.set)
    allowed = {"Outreach status", "Date contacted", "Notes", "Outreach draft"}
    if set(extra) - allowed:
        raise Fail(f"only {sorted(allowed)} can be updated", 2)
    wb = load()
    cs = wb[CON]
    for r, c in rows(cs, CON_COLS):
        if c["Contact ID"] == a.id:
            for k, v in extra.items():
                write_cell(cs, r, CON_COLS, k, v)
            save(wb)
            out({"ok": True, "contact_id": a.id})
    raise Fail("contact not found", 4)


def cmd_log_run(a):
    wb = load()
    wb[LOG].append([now(), a.mode, a.counts or "", (a.errors or "")[:500]])
    save(wb)
    out({"ok": True})


def cmd_last_run(a):
    out({"ok": True, "mode": a.mode, "last_run": last_run(a.mode)})


def cmd_pending_check(a):
    """Cheap early-exit test so scheduled verify runs cost nothing when there is nothing to verify."""
    wb = load()
    window = int(a.days)
    n = collections.Counter()
    for _, d in rows(wb[APP], COLS):
        if d["Status"] in APPLIED_STATES:
            ref = str(d["Applied date and time"] or d["Date found"] or "")[:10]
            try:
                age = (dt.date.today() - dt.date.fromisoformat(ref)).days
            except ValueError:
                age = 0
            if age <= window:
                n[d["Status"]] += 1
    out({"ok": True, "pending_total": sum(n.values()), "by_status": dict(n), "window_days": window})


def cmd_summary(a):
    wb = load()
    n = collections.Counter(d["Status"] for _, d in rows(wb[APP], COLS))
    out({"ok": True, "total": sum(n.values()), "by_status": {s: n.get(s, 0) for s in STATUSES if n.get(s)}})


def cmd_stats(a):
    wb = load()
    allrows = [d for _, d in rows(wb[APP], COLS)]
    cutoff = dt.date.today() - dt.timedelta(days=a.days)

    def d_of(d):
        try:
            return dt.date.fromisoformat(str(d["Date found"])[:10])
        except ValueError:
            return dt.date.min
    recent = [d for d in allrows if d_of(d) >= cutoff]
    applied_set = set(APPLIED_STATES + RESPONSE_STATES)
    by_portal = collections.defaultdict(lambda: collections.Counter())
    for d in recent:
        p = d["Portal"] or "?"
        by_portal[p]["found"] += 1
        if d["Status"] in applied_set:
            by_portal[p]["applied"] += 1
        if d["Status"] in ("CONFIRMED", "INTERVIEW", "OFFER"):
            by_portal[p]["confirmed_or_better"] += 1
        if d["Status"] in RESPONSE_STATES:
            by_portal[p]["responses"] += 1
        if d["Status"] in ("INTERVIEW", "OFFER"):
            by_portal[p]["interviews"] += 1
    missing = collections.Counter()
    for d in allrows:
        for s in str(d["Missing skills"] or "").split(","):
            if s.strip():
                missing[s.strip().lower()] += 1
    resp_scores = [d["Fit score"] for d in allrows if d["Status"] in RESPONSE_STATES and isinstance(d["Fit score"], (int, float))]
    applied = sum(1 for d in recent if d["Status"] in applied_set)
    conf = sum(1 for d in recent if d["Status"] in ("CONFIRMED", "INTERVIEW", "OFFER"))
    resp = sum(1 for d in recent if d["Status"] in RESPONSE_STATES)
    out({"ok": True, "window_days": a.days, "found": len(recent), "applied": applied,
         "confirmation_rate": round(conf / applied, 2) if applied else None,
         "response_rate": round(resp / applied, 2) if applied else None,
         "by_status": dict(collections.Counter(d["Status"] for d in recent)),
         "by_portal": {k: dict(v) for k, v in by_portal.items()},
         "avg_score_of_responded": round(sum(resp_scores) / len(resp_scores), 1) if resp_scores else None,
         "top_missing_skills": missing.most_common(10),
         "manual_required_open": sum(1 for d in allrows if d["Status"] == "MANUAL_REQUIRED")})


def cmd_maintain(a):
    """Close stale rows (never deletes)."""
    wb = load()
    ws = wb[APP]
    closed = 0
    for r, d in rows(ws, COLS):
        if d["Status"] in ("FOUND", "SHORTLISTED", "RESUME_READY"):
            try:
                age = (dt.date.today() - dt.date.fromisoformat(str(d["Date found"])[:10])).days
            except ValueError:
                continue
            if age > a.stale_days:
                write_cell(ws, r, COLS, "Status", "CLOSED")
                write_cell(ws, r, COLS, "Notes", append_note_text(d["Notes"], f"auto-closed: stale > {a.stale_days} days"))
                write_cell(ws, r, COLS, "Last updated", now())
                closed += 1
    if closed:
        save(wb)
    out({"ok": True, "closed": closed})


def cmd_refresh_format(a):
    """Rebuild the Status colour rules on an existing tracker (after COLOURS changes). Data untouched."""
    from openpyxl.formatting.formatting import ConditionalFormattingList
    wb = load()
    ws = wb[APP]
    ws.conditional_formatting = ConditionalFormattingList()
    scol = get_column_letter(COLS.index("Status") + 1)
    last = get_column_letter(len(COLS))
    for status, hexcol in COLOURS.items():
        ws.conditional_formatting.add(
            f"A2:{last}2000",
            FormulaRule(formula=[f'${scol}2="{status}"'], fill=PatternFill("solid", bgColor=hexcol, fgColor=hexcol)))
    save(wb)
    out({"ok": True, "rules": len(COLOURS)})


# ----------------------------------------------------------------------------- CLI
def build_parser():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", default=".", help="the JobHunt folder (default: current folder)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    s = sub.add_parser("preflight"); s.add_argument("--mode")
    s = sub.add_parser("add"); s.add_argument("--json"); s.add_argument("--json-file")
    s = sub.add_parser("find"); s.add_argument("--url"); s.add_argument("--key")
    s = sub.add_parser("list")
    s.add_argument("--status"); s.add_argument("--fields"); s.add_argument("--limit", type=int, default=25)
    s.add_argument("--order", choices=["score", "row"], default="row")
    s.add_argument("--min-score", type=float); s.add_argument("--max-attempts", type=int)
    s.add_argument("--referral-empty", action="store_true"); s.add_argument("--days", type=int)
    s = sub.add_parser("get"); s.add_argument("--id", required=True)
    s = sub.add_parser("set-status")
    s.add_argument("--id", required=True); s.add_argument("--to", required=True)
    s.add_argument("--actor", required=True); s.add_argument("--set", nargs="*"); s.add_argument("--note")
    s = sub.add_parser("set")
    s.add_argument("--id", required=True); s.add_argument("--actor", required=True); s.add_argument("--set", nargs="+", required=True)
    s = sub.add_parser("note"); s.add_argument("--id", required=True); s.add_argument("--text", required=True)
    s = sub.add_parser("attempt"); s.add_argument("--id", required=True); s.add_argument("--text")
    s = sub.add_parser("add-contact"); s.add_argument("--json"); s.add_argument("--json-file")
    s = sub.add_parser("list-contacts"); s.add_argument("--job")
    s = sub.add_parser("update-contact"); s.add_argument("--id", required=True); s.add_argument("--set", nargs="+", required=True)
    s = sub.add_parser("log-run"); s.add_argument("--mode", required=True); s.add_argument("--counts"); s.add_argument("--errors")
    s = sub.add_parser("last-run"); s.add_argument("--mode", required=True)
    s = sub.add_parser("pending-check"); s.add_argument("--days", default=45)
    sub.add_parser("summary")
    s = sub.add_parser("stats"); s.add_argument("--days", type=int, default=7)
    s = sub.add_parser("maintain"); s.add_argument("--stale-days", type=int, default=30)
    sub.add_parser("refresh-format")
    return p


COMMANDS = {
    "init": cmd_init, "preflight": cmd_preflight, "add": cmd_add, "find": cmd_find, "list": cmd_list,
    "get": cmd_get, "attempt": cmd_attempt, "set-status": cmd_set_status, "set": cmd_set, "note": cmd_note,
    "add-contact": cmd_add_contact, "list-contacts": cmd_list_contacts, "update-contact": cmd_update_contact,
    "log-run": cmd_log_run, "last-run": cmd_last_run, "pending-check": cmd_pending_check,
    "summary": cmd_summary, "stats": cmd_stats, "maintain": cmd_maintain, "refresh-format": cmd_refresh_format,
}

if __name__ == "__main__":
    args = build_parser().parse_args()
    PATHS = Paths(args.root)
    try:
        COMMANDS[args.cmd](args)
    except Fail as e:
        out({"ok": False, "error": str(e)}, e.code)
    except SystemExit:
        raise
    except Exception as e:  # never loop on unexpected errors: report once
        out({"ok": False, "error": f"{type(e).__name__}: {e}"}, 1)
