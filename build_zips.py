#!/usr/bin/env python3
"""Zip each folder in skills/ into dist/<name>.zip (skill folder at the ZIP root, SKILL.md inside it)."""
import os, re, sys, zipfile

root = os.path.dirname(os.path.abspath(__file__))
src, dist = os.path.join(root, "skills"), os.path.join(root, "dist")
os.makedirs(dist, exist_ok=True)
bad = 0
for name in sorted(os.listdir(src)):
    d = os.path.join(src, name)
    md = os.path.join(d, "SKILL.md")
    if not os.path.isfile(md):
        continue
    head = open(md, encoding="utf-8").read().split("---")[1]
    n = re.search(r"^name:\s*(\S+)", head, re.M)
    desc = re.search(r"^description:\s*(.+)$", head, re.M)
    if not n or n.group(1) != name or not desc or len(desc.group(1)) > 1024:
        print(f"ERROR {name}: frontmatter name must equal folder name and description must be <= 1024 chars")
        bad += 1
        continue
    out = os.path.join(dist, name + ".zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, files in os.walk(d):
            for f in files:
                full = os.path.join(base, f)
                z.write(full, os.path.relpath(full, src))
    print(f"built {out} ({len(desc.group(1))} char description)")
sys.exit(1 if bad else 0)
