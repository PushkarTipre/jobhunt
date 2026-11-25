#!/usr/bin/env python3
"""
Truth check for a tailored resume. Deterministic, so a mistake in the model's judgment cannot slip through.

Usage: python tools/truth_check.py --master data/master_profile.md --resume resumes/draft.json
Exit 0 = pass (warnings allowed). Exit 1 = hard violations: fix the resume JSON, then re-run ONCE.

HARD checks (any failure blocks the resume):
  - every number in the resume exists in the master profile
  - every skill listed exists in the Skills ledger with proof (not 'claimed-only')
  - every employer, job title and date range exists in the master profile
  - contact name / email / phone exist in the master profile
  - every degree/school exists in the master profile
SOFT checks (warnings to read, not blockers):
  - a bullet that shares few content words with ANY master bullet (possible invention)
"""
import argparse, json, re, sys

STOP = set("a an the and or of to in for with on by from at as is are was were be been using used use built build "
           "led lead developed develop designed design created create implemented implement worked work managed "
           "across into over under this that these those it its their our my i we".split())


def norm(s):
    return re.sub(r"\s+", " ", str(s or "").lower().replace("–", "-").replace("—", "-")).strip()


def nospace(s):
    return re.sub(r"[\s]", "", norm(s))


def numbers(text):
    return {n.replace(",", "") for n in re.findall(r"\d+(?:[.,]\d+)*", str(text))}


def words(text):
    return {w for w in re.findall(r"[a-z][a-z0-9+#.\-]{2,}", norm(text)) if w not in STOP}


def ledger(master_text):
    """Return (proven_names, claimed_only_names) parsed from the '## Skills ledger' table."""
    m = re.search(r"^##\s*Skills ledger\s*$(.*?)(?=^##\s|\Z)", master_text, re.S | re.M | re.I)
    proven, claimed = set(), set()
    if not m:
        return proven, claimed
    for line in m.group(1).splitlines():
        if not line.strip().startswith("|") or re.match(r"^\s*\|[\s\-:|]+\|\s*$", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or norm(cells[0]) in ("skill", ""):
            continue
        names = [norm(x) for x in re.split(r"[/,]", cells[0]) if x.strip()]
        proof, rest = cells[2], " ".join(cells[3:])
        if "claimed-only" in norm(proof + " " + rest) or not proof.strip() or proof.strip() in ("-", "none"):
            claimed.update(names)
        else:
            proven.update(names)
    return proven, claimed


def master_bullets(master_text):
    return [l.strip(" -*\t") for l in master_text.splitlines() if re.match(r"^\s*[-*]\s+\S", l)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", required=True)
    ap.add_argument("--resume", required=True)
    a = ap.parse_args()
    master = open(a.master, encoding="utf-8").read()
    r = json.load(open(a.resume, encoding="utf-8"))
    mt, mns = norm(master), nospace(master)
    hard, warn = [], []

    # numbers
    resume_text = json.dumps({k: v for k, v in r.items()}, ensure_ascii=False).replace("**", "")
    for n in sorted(numbers(resume_text) - numbers(master)):
        hard.append(f"number '{n}' not found in master profile")

    # skills
    proven, claimed = ledger(master)
    if not proven:
        hard.append("no proven skills parsed from '## Skills ledger' in master profile (check its table format)")
    for grp in r.get("skills", []):
        for item in grp.get("items", []):
            k = norm(item)
            parts = [norm(x) for x in re.split(r"[/,]", str(item)) if x.strip()]
            if k not in proven and parts and all(x in proven for x in parts):
                continue  # combined item such as "Docker/Podman", every part proven
            if k in claimed and k not in proven:
                hard.append(f"skill '{item}' is claimed-only in the ledger; do not list it")
            elif k not in proven:
                hard.append(f"skill '{item}' is not a proven skill in the ledger")

    # contact
    c = r.get("contact", {})
    for field in ("name", "email", "phone"):
        if c.get(field) and nospace(c[field]) not in mns:
            hard.append(f"contact {field} '{c[field]}' differs from master profile")

    # experience facts
    for e in r.get("experience", []):
        if e.get("company") and norm(e["company"]) not in mt:
            hard.append(f"experience company '{e['company']}' not found in master profile")
        titles = ([e["title"]] if e.get("title") else []) + [x.get("title") for x in e.get("roles", [])]
        dates = [e.get("dates"), e.get("company_dates")] + [x.get("dates") for x in e.get("roles", [])]
        for t in filter(None, titles):
            if norm(t) not in mt:
                hard.append(f"experience title '{t}' not found in master profile")
        for d in filter(None, dates):
            if nospace(d) not in mns:
                hard.append(f"dates '{d}' for {e.get('company')} not found in master profile")

    # client projects inside an experience entry
    for e in r.get("experience", []):
        for sp in e.get("sub_projects", []):
            if sp.get("name") and norm(sp["name"]) not in mt:
                hard.append(f"client project '{sp['name']}' under {e.get('company')} not found in master profile")

    # project names and headline
    for p in r.get("projects", []):
        if p.get("name") and norm(p["name"]) not in mt:
            hard.append(f"project '{p['name']}' not found in master profile")
    if r.get("headline"):
        for part in re.split(r"[|/]", r["headline"].replace("**", "")):
            if part.strip() and norm(part) not in mt:
                hard.append(f"headline part '{part.strip()}' not found in master profile")

    # education
    for ed in r.get("education", []):
        for field in ("school", "degree"):
            if ed.get(field) and norm(ed[field]) not in mt:
                hard.append(f"education {field} '{ed[field]}' not found in master profile")

    # soft: bullet similarity
    mb = [words(b) for b in master_bullets(master)]
    bullets = [b for e in r.get("experience", []) for b in e.get("bullets", [])]
    bullets += [b for e in r.get("experience", []) for sp in e.get("sub_projects", []) for b in sp.get("bullets", [])]
    bullets += [b for p in r.get("projects", []) for b in p.get("bullets", [])]
    for b in bullets:
        w = words(b.replace("**", ""))
        if not w:
            continue
        best = max((len(w & m) / len(w) for m in mb), default=0)
        if best < 0.4:
            warn.append(f"bullet may not be grounded in profile (overlap {best:.0%}): {b[:90]}")

    res = {"ok": not hard, "hard_violations": hard, "warnings": warn}
    print(json.dumps(res, ensure_ascii=False))
    sys.exit(0 if not hard else 1)


if __name__ == "__main__":
    main()
