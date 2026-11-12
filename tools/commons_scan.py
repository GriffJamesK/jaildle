#!/usr/bin/env python3
"""Look for freely licensed photos on Wikimedia Commons for people whose current photo is not cleared.
Writes candidates to data/commons_candidates.json. Slow on purpose (Wikimedia rate limits)."""
import json, pathlib, subprocess, sys, time, urllib.parse
ROOT = pathlib.Path(__file__).resolve().parent.parent
UA = "jaildle-build/1.0 (static game build script)"
def get(u):
    for a in range(4):
        raw = subprocess.run(["curl", "-sS", "-m", "40", "-A", UA, u], capture_output=True).stdout
        try: return json.loads(raw)
        except Exception: time.sleep(20 * (a + 1))
    return {}
names = json.loads(pathlib.Path(sys.argv[1]).read_text())
out_f = ROOT / "data" / "commons_candidates.json"
out = json.loads(out_f.read_text()) if out_f.exists() else {}
for n in names:
    if n in out: continue
    q = '"%s"' % n.replace('"', '')
    d = get("https://commons.wikimedia.org/w/api.php?action=query&format=json&list=search&srnamespace=6&srlimit=6&srsearch=" + urllib.parse.quote(q))
    out[n] = [s["title"] for s in d.get("query", {}).get("search", []) if not s["title"].lower().endswith((".pdf", ".webm", ".ogv", ".ogg", ".svg", ".djvu", ".tif", ".tiff"))]
    out_f.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    time.sleep(5)
print("done", len(out), "with hits:", sum(1 for v in out.values() if v))
