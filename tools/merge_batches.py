#!/usr/bin/env python3
"""Check the research batches in data/batches/*.json and append the entries that pass to data/people.json.

Checks: required fields, not already in the game, photo file present, release date 3+ months away and
before 2081, headline does not give away the sentence, and (for US federal inmates) the release date
matches the Bureau of Prisons record looked up by register number today.

Usage: python3 tools/merge_batches.py [--write]     (without --write it only reports)
"""
import datetime, json, pathlib, random, re, subprocess, sys, time, unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
REQ = ["name", "knownFor", "headline", "convictedOf", "jurisdiction", "crimeDates", "custodyStart",
       "sentenceLength", "releaseDate", "releaseType", "releaseRule", "sources", "photoFile"]
TYPES = {"official projected release", "earliest parole eligibility", "computed full term", "computed estimate"}
TODAY = datetime.date.today()
EXCLUDE = json.loads((ROOT / 'data' / 'batches' / 'EXCLUDE.json').read_text()) if (ROOT / 'data' / 'batches' / 'EXCLUDE.json').exists() else {}


def norm(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    s = re.sub(r'"[^"]*"|\([^)]*\)', " ", s)          # drop nicknames and brackets
    return re.sub(r"[^a-z]+", " ", s).strip()


def bop(regno):
    url = ("https://www.bop.gov/PublicInfo/execute/inmateloc?todo=query&output=json"
           f"&inmateNumType=IRN&inmateNum={regno}")
    for attempt in range(3):
        raw = subprocess.run(["curl", "-sS", "-m", "30", "-A", "Mozilla/5.0", url], capture_output=True).stdout
        try:
            rows = json.loads(raw).get("InmateLocator", [])
            return rows[0] if rows else None
        except Exception:
            time.sleep(3 * (attempt + 1))
    return "error"


def main():
    write = "--write" in sys.argv
    people = json.loads((ROOT / "data" / "people.json").read_text())
    have = {norm(p["name"]) for p in people}
    accepted, rejected = [], []
    for f in sorted((ROOT / "data" / "batches").glob("[a-z][a-z].json")):
        try:
            batch = json.loads(f.read_text())
        except Exception as e:
            print(f"!! {f.name}: unreadable ({e})"); continue
        for p in batch:
            why = check(p, have)
            if why:
                rejected.append((f.stem, p.get("name", "?"), why))
            else:
                have.add(norm(p["name"])); p["batch"] = f.stem; accepted.append(p)
    print(f"accepted {len(accepted)}, rejected {len(rejected)}")
    for b, n, w in rejected:
        print(f"  - [{b}] {n}: {w}")
    if write and accepted:
        random.Random(7).shuffle(accepted)             # mix the categories; appended after existing days
        (ROOT / "data" / "people.json").write_text(json.dumps(people + accepted, indent=1, ensure_ascii=False))
        print(f"people.json now has {len(people) + len(accepted)} entries")


def check(p, have):
    miss = [k for k in REQ if not p.get(k)]
    if miss:
        return "missing " + ", ".join(miss)
    if p["name"] in EXCLUDE:
        return "screened out: " + EXCLUDE[p["name"]]
    if norm(p["name"]) in have:
        return "duplicate"
    if p["releaseType"] not in TYPES:
        return f"bad releaseType {p['releaseType']!r}"
    if not (ROOT / "data" / "img" / "custom" / p["photoFile"]).is_file():
        return "photo file not found"
    m = re.fullmatch(r"(\d{4})-(\d{2})(?:-(\d{2}))?", p["releaseDate"])
    if not m:
        return f"bad releaseDate {p['releaseDate']!r}"
    rel = datetime.date(int(m[1]), int(m[2]), int(m[3] or 15))
    if (rel - TODAY).days < 90:
        return "release is under 3 months away or already past"
    if rel.year > 2080:
        return "release after 2080"
    if re.search(r"\b\d+\s*(years?|months?|yrs?)\b|\b(gets|given|handed|sentenced to|jailed for)\b|\blife (sentence|term|in prison|imprisonment)\b", p["headline"], re.I):
        return f"headline gives away the sentence: {p['headline']!r}"
    if p["jurisdiction"].lower().startswith("us federal"):
        r = re.search(r"\b(\d{5}-\d{3})\b", p.get("notes", ""))
        if not r:
            return "federal entry without a BOP register number in notes"
        row = bop(r[1])
        if row == "error":
            return "BOP lookup failed"
        if not row or row.get("actRelDate") or "RRM" in (row.get("faclType") or "") + (row.get("faclName") or ""):
            return f"BOP: not in a prison ({(row or {}).get('faclName')}, released {(row or {}).get('actRelDate')})"
        try:
            mm, dd, yy = row["projRelDate"].split("/")
        except ValueError:
            return f"BOP projected date is {row['projRelDate']!r}"
        official = f"{yy}-{mm}-{dd}"
        if official != p["releaseDate"]:
            p["releaseDate"] = official               # the live record wins
        last = norm(row["nameLast"]).split()[-1]
        if last not in norm(p["name"]) + " " + norm(p.get("notes", "")) + " " + norm(p.get("convictedOf", "")):
            p.setdefault("_warn", []).append(f"BOP surname {row['nameLast']} not in entry name")
        p["releaseType"] = "official projected release"
    return None


if __name__ == "__main__":
    main()
