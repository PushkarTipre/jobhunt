#!/usr/bin/env python3
r"""
Render a tailored resume from JSON into the user's own LaTeX template and compile it to PDF.
The design (preamble, fonts, contact header, education, achievements) is copied VERBATIM from
data/resume_original_latex.tex; only the Summary, Skills, Experience and Projects bodies are generated.

Usage:
  python tools/make_resume_tex.py --in resumes/X.json --out resumes/X.pdf [--max-pages 2]
  python tools/make_resume_tex.py --base --out resumes/Base.pdf      # compile the untouched template

JSON (strings may use **bold** markers; plain text otherwise, LaTeX characters are escaped for you):
{ "headline": "optional, must come from the master profile",
  "summary": "text",
  "skills": [{"category": "LLM & VLM", "items": ["PyTorch", "..."]}],
  "experience": [
    {"company": "Acme Corp", "company_dates": "Jan 2024 – Present", "location": "City, Country",
     "roles": [{"title": "...", "dates": "..."}], "bullets": ["..."]},
    {"company": "Example Ltd", "company_dates": "Jun 2023 – Dec 2023",
     "title": "Intern", "location": "City, Country (Remote)", "bullets": ["..."]},
    {"company": "Studio Co", "company_dates": "Jul 2025 – Present", "title": "Software Engineer",
     "sub_projects": [{"name": "Client App", "bullets": ["..."]}]}],
  "projects": [{"name": "Project Name", "bullets": ["..."]}] }
Project and client-project (sub_projects) stack and link come from the template; client projects are written there as
\resumeSubProject{name}{stack}{link}, and a link may be empty. Section headings are copied from the template's own
\section lines (under the %-----------SUMMARY----------- style markers). Needs Tectonic (tools/bin/tectonic/tectonic.exe or on PATH).
Exit: 0 ok | 1 compile error or too many pages | 5 compiler missing
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(ROOT, "data", "resume_original_latex.tex")


def out(obj, code=0):
    print(json.dumps(obj, ensure_ascii=False))
    sys.exit(code)


def find_tectonic():
    local = os.path.join(HERE, "bin", "tectonic", "tectonic.exe")
    if os.path.exists(local):
        return local
    local2 = os.path.join(HERE, "bin", "tectonic", "tectonic")
    if os.path.exists(local2):
        return local2
    return shutil.which("tectonic")


SPECIAL = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
           "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}


def esc(s):
    s = str(s).replace("\u2013", "--").replace("\u2014", "---").replace("\u2018", "'").replace("\u2019", "'")
    s = s.replace("\u201c", "``").replace("\u201d", "''").replace("\u2011", "-")
    return "".join(SPECIAL.get(ch, ch) for ch in s)


def tex(s):
    """escape + convert **bold** markers"""
    parts = str(s).split("**")
    res = []
    for i, p in enumerate(parts):
        e = esc(p)
        res.append(r"\textbf{" + e + "}" if i % 2 == 1 and e else e)
    return "".join(res)


def split_template(t):
    pre, rest = t.split("\\begin{document}", 1)
    # XeTeX (Tectonic) does not know these pdfTeX-only lines; they only affect pdfTeX text mapping.
    # \sectionfont comes from a package that is not loaded, so it is a no-op in Overleaf too.
    for bad in ("\\input{glyphtounicode}", "\\pdfgentounicode=1", "\\sectionfont{\\color{cyan}}"):
        pre = pre.replace(bad, "")
    head, rest2 = rest.split("%-----------SUMMARY-----------", 1)
    tail = "%-----------EDUCATION-----------" + rest2.split("%-----------EDUCATION-----------", 1)[1]
    projects = {}
    for m in re.finditer(r"\\textbf\{([^}]+)\}\s*\$\|\$\s*\\emph\{([^}]+)\}(?:\s*\\href\{([^}]+)\})?", t):
        projects[m.group(1).strip()] = (m.group(2).strip(), (m.group(3) or "").strip())
    subs = {}
    for m in re.finditer(r"\\resumeSubProject\s*\{([^}]*)\}\s*\{([^}]*)\}\s*\{([^}]*)\}", t):
        subs[m.group(1).strip()] = (m.group(2).strip(), m.group(3).strip())
    return pre, head, tail, projects, subs


DEFAULT_HEADERS = {
    "SUMMARY": "\\section{\\textcolor{cyan}{PROFESSIONAL SUMMARY}}",
    "TECHNICAL SKILLS": "\\section{\\textcolor{cyan}{TECHNICAL SKILLS}}",
    "EXPERIENCE": "\\section{\\textcolor{cyan}{PROFESSIONAL EXPERIENCE}}",
    "PROJECTS": "\\section{\\textcolor{cyan}{ACADEMIC PROJECTS}}",
}


def section_headers(t):
    """Reuse the template's own \\section line for each generated section, so its heading text and style stay."""
    hs = dict(DEFAULT_HEADERS)
    for key in hs:
        m = re.search(r"%-+" + re.escape(key) + r"-+(.*?)(?=%-{5,}|\\end\{document\})", t, re.S)
        h = m and re.search(r"^\s*(\\section\*?\{.*\})\s*$", m.group(1), re.M)
        if h:
            hs[key] = h.group(1)
    return hs


def project_gap(t):
    """Vertical gap the template puts between two projects (the generator used to hard-code -15pt)."""
    m = re.search(r"%-+PROJECTS-+(.*?)(?=%-{5,}|\\end\{document\})", t, re.S)
    g = m and re.search(r"\\resumeItemListEnd\s*(\\vspace\{[^}]*\})?\s*\\resumeProjectHeading", m.group(1))
    if g:
        return g.group(1) or ""
    return "\\vspace{-15pt}"


def canon(s):
    """Spelling-neutral name: LaTeX \\& and ---/-- read the same as &, em dash and en dash."""
    s = str(s).replace("\\&", "&").replace("---", "\u2014").replace("--", "\u2013")
    return re.sub(r"\s+", " ", s).strip().lower()


def lookup(meta, name, kind):
    """Find a template entry by its JSON name; returns the template's own spelling so it is output verbatim."""
    want = canon(name)
    for k, v in meta.items():
        if canon(k) == want:
            return k, v
    raise ValueError(f"{kind} '{name}' not found in the template; names must match exactly")


def items(bullets):
    return "  \\resumeItemListStart\n" + "".join(f"    \\resumeItem{{{tex(b)}}}\n" for b in bullets) + "  \\resumeItemListEnd\n"


def build(data, t):
    pre, head, tail, proj_meta, sub_meta = split_template(t)
    hdr = section_headers(t)
    gap = project_gap(t)
    if data.get("headline"):
        head = re.sub(r"(\{\\small \\textbf\{)(.*?)(\}\} \\\\ \\vspace\{2pt\})",
                      lambda m: m.group(1) + tex(data["headline"]).replace("|", "$|$") + m.group(3), head, count=1)
    b = [pre, "\\begin{document}", head]
    b.append("%-----------SUMMARY-----------\n" + hdr["SUMMARY"] + "\n\\vspace{1pt}\n"
             + tex(data["summary"]) + "\\vspace{-5pt}\n\n")
    b.append("%-----------TECHNICAL SKILLS-----------\n\\vspace{-5pt}\n" + hdr["TECHNICAL SKILLS"] + "\n\\small\n")
    lines = [f"\\noindent\\textbf{{{esc(g['category'])}}}: " + ", ".join(esc(i) for i in g["items"]) for g in data["skills"]]
    b.append(" \\\\\n".join(lines) + "\n\\normalize\n\n".replace("\\normalize", "\\normalsize"))
    b.append("%-----------EXPERIENCE-----------\n\\vspace{-5pt}\n" + hdr["EXPERIENCE"] + "\n\\vspace{1pt}\n\\resumeSubHeadingListStart\n\n")
    for e in data["experience"]:
        if e.get("roles"):
            b.append(f"  \\resumeSubheading\n    {{{tex(e['company'])}}}{{{esc(e['company_dates'])}}}\n    {{{esc(e.get('location', ''))}}}{{}}\n")
            for r in e["roles"]:
                b.append(f"  \\resumeSubSubheading\n    {{{tex(r['title'])}}}{{{esc(r['dates'])}}}\n")
        else:
            b.append(f"  \\resumeSubheading\n    {{{tex(e['company'])}}}{{{esc(e.get('company_dates') or e.get('dates'))}}}\n    {{{esc(e['title'])}}}{{{esc(e.get('location', ''))}}}\n")
        if not e.get("bullets") and not e.get("sub_projects"):
            raise ValueError(f"experience '{e.get('company')}' needs bullets or sub_projects")
        if e.get("bullets"):
            b.append(items(e["bullets"]))
        for sp in e.get("sub_projects", []):
            name, (stack, link) = lookup(sub_meta, sp["name"], "client project")
            b.append(f"  \\resumeSubProject{{{name}}}{{{stack}}}{{{link}}}\n")
            if sp.get("bullets"):
                b.append(items(sp["bullets"]))
        b.append("  \\vspace{0pt}\n\n")
    b.append("\\resumeSubHeadingListEnd\n\n")
    if data.get("projects"):
        b.append("%-----------PROJECTS-----------\n" + hdr["PROJECTS"] + "\n\\vspace{0pt}\n\\resumeSubHeadingListStart\n\n")
        for n, p in enumerate(data["projects"]):
            name, (stack, link) = lookup(proj_meta, p["name"], "project")
            href = f"\n    \\href{{{link}}}{{\\textcolor{{blue}}{{\\underline{{Link}}}}}}" if link else ""
            b.append(f"  \\resumeProjectHeading\n    {{\\textbf{{{name}}} $|$ \\emph{{{stack}}}{href}}}{{}}\n")
            b.append(items(p["bullets"]))
            if gap and n < len(data["projects"]) - 1:
                b.append("    " + gap + "\n")
        b.append("\\resumeSubHeadingListEnd\n\\vspace{-10pt}\n\n")
    b.append(tail)
    return "".join(b)


def compile_tex(src_tex, out_pdf):
    exe = find_tectonic()
    if not exe:
        out({"ok": False, "error": "Tectonic not found (tools/bin/tectonic/tectonic.exe). See SETUP_GUIDE."}, 5)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "resume.tex")
        open(p, "w", encoding="utf-8").write(src_tex)
        r = subprocess.run([exe, "-X", "compile", p, "--outdir", d], capture_output=True, text=True, timeout=240)
        pdf = os.path.join(d, "resume.pdf")
        if r.returncode != 0 or not os.path.exists(pdf):
            errs = [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("!") or "error" in l.lower()][:6]
            out({"ok": False, "error": "LaTeX compile failed", "details": errs}, 1)
        shutil.copyfile(pdf, out_pdf)
        pages = count_pages(pdf)
    if not pages:
        out({"ok": False, "error": "could not count PDF pages; refusing to guess"}, 1)
    return pages


def count_pages(path):
    """Page count that also works for PDFs with compressed object streams (Tectonic output)."""
    for mod in ("pypdf", "PyPDF2"):
        try:
            m = __import__(mod)
            return len(m.PdfReader(path).pages)
        except Exception:
            pass
    try:
        import pdfplumber
        with pdfplumber.open(path) as p:
            return len(p.pages)
    except Exception:
        pass
    import zlib
    raw = open(path, "rb").read()
    n = len(re.findall(rb"/Type\s*/Page[^s]", raw))
    if n:
        return n
    counts = []
    for m in re.finditer(rb"stream\r?\n(.*?)endstream", raw, re.S):
        try:
            blob = zlib.decompress(m.group(1))
        except Exception:
            continue
        counts += [int(x) for x in re.findall(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", blob)]
        counts += [int(x) for x in re.findall(rb"/Count\s+(\d+)[^>]*?/Type\s*/Pages", blob)]
    return max(counts) if counts else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp")
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", action="store_true")
    ap.add_argument("--max-pages", type=int, default=2)
    a = ap.parse_args()
    t = open(TEMPLATE, encoding="utf-8").read()
    if a.base:
        pre, _ = t.split("\\begin{document}", 1)
        src = t
        for bad in ("\\input{glyphtounicode}", "\\pdfgentounicode=1", "\\sectionfont{\\color{cyan}}"):
            src = src.replace(bad, "")
    else:
        if not a.inp:
            out({"ok": False, "error": "--in is required unless --base"}, 1)
        data = json.load(open(a.inp, encoding="utf-8"))
        try:
            src = build(data, t)
        except (KeyError, ValueError) as e:
            out({"ok": False, "error": f"bad resume JSON: {e}"}, 1)
        open(os.path.splitext(a.out)[0] + ".tex", "w", encoding="utf-8").write(src)
    pages = compile_tex(src, a.out)
    res = {"ok": pages <= a.max_pages, "pages": pages, "out": a.out}
    if pages > a.max_pages:
        res["error"] = f"{pages} pages; cut low-relevance items and re-run once"
    out(res, 0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
