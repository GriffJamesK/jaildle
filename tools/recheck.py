#!/usr/bin/env python3
"""Re-check people already in the game against the US Bureau of Prisons record.

For each federal inmate (matched by the register number in their notes) it compares the live record with
data/people.json and reports anyone who has been released, moved to a halfway house, or whose projected
release date or prison has changed. People outside the federal system cannot be checked automatically;
they are listed with their sources so you can check them by hand.

Usage:
  python3 tools/recheck.py              # the cases for the next 7 days
  python3 tools/recheck.py --days 30    # the next 30 days
  python3 tools/recheck.py --all        # everyone
  add --write to save new dates and prisons into data/people.json (then run build.py)
"""
import datetime, json, pathlib, re, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
EPOCH = datetime.date(2026, 11, 12)          # case no. 1


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


def in_game(p):
    if p.get("photoFile"):
        return (ROOT / "data" / "img" / "custom" / p["photoFile"]).is_file()
    return not p.get("noPhoto")


def main():
    args = sys.argv[1:]
    write = "--write" in args
    days = int(args[args.index("--days") + 1]) if "--days" in args else 7
    path = ROOT / "data" / "people.json"
    people = json.loads(path.read_text())
    game = [p for p in people if in_game(p)]
    today = (datetime.date.today() - EPOCH).days
    if "--all" in args:
        picks = list(enumerate(game))
    else:
        picks = [((today + k) % len(game), game[(today + k) % len(game)]) for k in range(days + 1)]
    problems, changed, manual, ok = [], [], [], 0
    for idx, p in picks:
        when = EPOCH + datetime.timedelta(days=idx)
        label = f"case {idx + 1} ({when:%a %d %b %Y}) {p['name']}"
        reg = re.search(r"\b(\d{5}-\d{3})\b", p.get("notes", ""))
        if not p["jurisdiction"].lower().startswith("us federal") or not reg:
            manual.append(f"{label} [{p['jurisdiction']}; {p['releaseType']} {p['releaseDate']}] {' '.join(p.get('sources', [])[:2])}")
            continue
        row = bop(reg[1])
        if row == "error":
            problems.append(f"{label}: lookup failed, try again"); continue
        if not row:
            problems.append(f"{label}: register no. {reg[1]} not found"); continue
        place = f"{row.get('faclName', '')} {row.get('faclType', '')}".strip()
        if row.get("actRelDate"):
            problems.append(f"{label}: RELEASED on {row['actRelDate']}. Remove from the game"); continue
        if "RRM" in place:
            problems.append(f"{label}: moved to a halfway house / home confinement ({place}). Remove from the game"); continue
        try:
            mm, dd, yy = row["projRelDate"].split("/")
            official = f"{yy}-{mm}-{dd}"
        except ValueError:
            problems.append(f"{label}: projected release is '{row['projRelDate']}' ({place})"); continue
        if official != p["releaseDate"]:
            changed.append(f"{label}: release date {p['releaseDate']} -> {official}")
            if write:
                p["releaseDate"], p["releaseType"] = official, "official projected release"
        elif (datetime.date(int(yy), int(mm), int(dd)) - when).days < 60:
            problems.append(f"{label}: release ({official}) is under two months after their day; the game will skip them")
        else:
            ok += 1
        p["_lastChecked"] = datetime.date.today().isoformat() if write else p.get("_lastChecked")
        if p.get("_lastChecked") is None:
            p.pop("_lastChecked", None)
    print(f"Checked {len(picks)} cases: {ok} federal records unchanged, {len(changed)} changed, "
          f"{len(problems)} need attention, {len(manual)} cannot be checked automatically.")
    for title, rows in (("NEEDS ATTENTION", problems), ("DATE CHANGED" + (" (saved)" if write else " (run with --write to save)"), changed),
                        ("CHECK BY HAND (no public record to query)", manual)):
        if rows:
            print("\n" + title)
            for r in rows:
                print("  - " + r)
    if write:
        path.write_text(json.dumps(people, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
