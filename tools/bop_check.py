#!/usr/bin/env python3
"""Look up US federal inmates on the Bureau of Prisons locator.

Usage: python3 tools/bop_check.py "First Last" ["First Last" ...]
Prints every match with facility and projected/actual release date.
"""
import json, subprocess, sys, urllib.parse

for full in sys.argv[1:]:
    first, last = full.split(" ", 1)
    url = ("https://www.bop.gov/PublicInfo/execute/inmateloc?todo=query&output=json"
           f"&nameFirst={urllib.parse.quote(first)}&nameLast={urllib.parse.quote(last)}")
    raw = subprocess.run(["curl", "-sS", "-m", "30", "-A", "Mozilla/5.0", url], capture_output=True).stdout
    try:
        rows = json.loads(raw).get("InmateLocator", [])
    except Exception:
        print(f"{full}: lookup failed"); continue
    if not rows:
        print(f"{full}: no match")
    for r in rows:
        print(f"{full}: {r['nameFirst']} {r['nameMiddle']} {r['nameLast']} age {r['age']} #{r['inmateNum']} "
              f"| {r['faclName']} {r['faclType']} | projected {r['projRelDate'] or '-'} | actual {r['actRelDate'] or '-'} | code {r['releaseCode']}")
