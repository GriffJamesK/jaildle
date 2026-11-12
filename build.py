#!/usr/bin/env python3
"""Build the game into docs/ from data/people.json + src/template.html.

docs/index.html holds the game and the case data; docs/i/ holds one photo per person,
loaded only when that person's case is shown.
docs/desk/ is Jaildle Desk, the free-play fork (src/desk.html), with pixel portraits in docs/p/.

Play order is the order of data/people.json: case no. 1 is the first entry, and so on.
Add new people at the END so existing days keep their cases, and give each a new unique "id"
(the next unused number); it names their photo file.

Photos, in order of preference:
- "photoFile": a JPEG in data/img/custom/ (with "photoCredit" = source page URL)
- otherwise the lead photo of the Wikipedia article named in "wikipediaTitle" (cached in data/img/)
People with no photo are left out of the game and listed at the end of the build.

Usage: python3 build.py          (the build to publish)
       python3 build.py --dev    (local preview: arrows can step into future days; do not publish)
"""
import io, json, pathlib, re, shutil, subprocess, sys, time, unicodedata, urllib.parse
from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).parent
IMG = ROOT / "data" / "img"
DIST = ROOT / "docs"          # GitHub Pages serves this folder
UA = "jaildle-build/1.0 (static game build script)"
DROP = ("confidence", "wikipediaTitle", "wikipedia", "imageTitle", "arrestDate", "convictionDate",
        "noPhoto", "photoFile", "photoCredit", "photoLicence", "batch", "_warn", "id", "_lastChecked")


def curl(url):
    return subprocess.run(["curl", "-sSL", "-m", "40", "-A", UA, url], capture_output=True, check=False).stdout


def wiki_photo(person):
    """Return (path, credit_url) for the Wikipedia lead photo, fetching it once; or (None, None)."""
    title = person.get("imageTitle") or person.get("wikipediaTitle")
    if not title:
        return None, None
    slug = "".join(c if c.isalnum() else "_" for c in person["name"])
    meta_f, img_f = IMG / f"{slug}.json", IMG / f"{slug}.jpg"
    if not meta_f.exists():
        api = ("https://en.wikipedia.org/w/api.php?action=query&redirects=1&format=json"
               "&prop=pageimages&piprop=thumbnail|name&pithumbsize=330&titles=" + urllib.parse.quote(title))
        time.sleep(4)
        try:
            page = next(iter(json.loads(curl(api))["query"]["pages"].values()))
        except Exception:
            return None, None  # lookup failed; retried on the next build
        thumb = page.get("thumbnail", {}).get("source")
        if thumb:
            thumb = thumb.split("?")[0].replace("//thumb.wikimedia.org/", "//upload.wikimedia.org/")
        meta_f.write_text(json.dumps({"thumb": thumb, "file": page.get("pageimage")}))
    meta = json.loads(meta_f.read_text())
    if not meta.get("thumb"):
        return None, None
    if not img_f.exists():
        for attempt in range(4):  # Wikimedia rate-limits bursts; back off and retry
            time.sleep(2 + 6 * attempt)
            try:
                im = Image.open(io.BytesIO(curl(meta["thumb"]))).convert("RGB")
            except Exception:
                continue
            im.thumbnail((330, 440))
            im.save(img_f, "JPEG", quality=78)
            break
    if not img_f.exists():
        return None, None
    return img_f, "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(meta["file"])


PIXEL_TONES = [(26, 24, 30), (62, 54, 58), (118, 96, 86), (176, 146, 122), (226, 204, 176)]   # dark to light


def pixel_portrait(src, dst):
    """A 44x52 five-tone posterised portrait, shown enlarged with hard pixels."""
    im = Image.open(src).convert("L")
    w, h = im.size
    if h >= w:                      # portrait photo: keep the top, where the head is
        box_h = min(h, int(w * 52 / 44))
        im = im.crop((0, 0, w, box_h))
    else:                           # landscape photo: centre crop
        box_w = int(h * 44 / 52)
        left = (w - box_w) // 2
        im = im.crop((left, 0, left + box_w, h))
    im = ImageOps.autocontrast(im.resize((44, 52), Image.BOX), cutoff=2)
    vals = list(im.tobytes())
    px = sorted(vals)
    cuts = [px[int(len(px) * f)] for f in (0.16, 0.38, 0.62, 0.84)]   # tone bands sized to this photo
    out = Image.new("RGBA", im.size)
    data = []
    for i, v in enumerate(vals):
        x, y = i % 44, i // 44
        # keep a head-and-shoulders shape and drop the photo's background, so a figure stands at the window
        head = ((x - 21.5) / 15.5) ** 2 + ((y - 19) / 19.5) ** 2 <= 1
        shoulders = y >= 32 and abs(x - 21.5) <= 13 + (y - 32) * 0.55
        data.append(PIXEL_TONES[sum(v > c for c in cuts)] + (255,) if head or shoulders else (0, 0, 0, 0))
    out.putdata(data)
    out.save(dst, optimize=True)


def ascii_slug(name):
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    people = json.loads((ROOT / "data" / "people.json").read_text())
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "i").mkdir(parents=True)
    out, missing, seen = [], [], set()
    for n, p in enumerate(people):
        custom = IMG / "custom" / (p.get("photoFile") or "-")
        if custom.is_file():
            src, credit = custom, p.get("photoCredit")
        elif p.get("noPhoto"):
            src, credit = None, None
        else:
            src, credit = wiki_photo(p)
        if not src:
            missing.append(p["name"])
            continue
        slug = ascii_slug(p["name"])
        assert slug and slug not in seen, f"duplicate or empty name: {p['name']}"
        seen.add(slug)
        im = Image.open(src).convert("RGB")
        im.thumbnail((330, 440))
        im.save(DIST / "i" / f"{p['id']:03d}.jpg", "JPEG", quality=78)  # numbered by the person's fixed "id"
        q = {k: v for k, v in p.items() if k not in DROP}
        q["img"], q["imgCredit"] = f"i/{p['id']:03d}.jpg", credit
        out.append(q)
    blob = json.dumps(out, ensure_ascii=False).replace("</", "<\\/")
    html = (ROOT / "src" / "template.html").read_text().replace("/*__DATA__*/", blob)
    if "--dev" in sys.argv:   # local preview only: lets the arrows step into future days. Never publish this build.
        html = html.replace("/*__DEV__*/false", "true")
    (DIST / "index.html").write_text(html)
    # Jaildle Desk: the free-play fork. Same people and photos, plus a pixel portrait of each for the window.
    (DIST / "desk").mkdir()
    (DIST / "p").mkdir()
    for q in out:
        num = q["img"][2:5]
        made = ROOT / "data" / "portraits" / f"{num}.png"      # from tools/portraits.py (person cut out, head sized by face)
        if made.exists():
            shutil.copy(made, DIST / "p" / f"{num}.png")
        else:
            pixel_portrait(DIST / q["img"], DIST / "p" / f"{num}.png")   # simple fallback until the tool has been run
    desk = (ROOT / "src" / "desk.html").read_text().replace("/*__DATA__*/", blob)
    (DIST / "desk" / "index.html").write_text(desk)
    (DIST / ".nojekyll").write_text("")   # tells GitHub Pages to serve the files as they are
    size = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file()) / 1e6
    print(f"{len(out)} people in the game; docs/ is {size:.1f} MB (index.html {len(html)/1e6:.2f} MB).")
    print(f"Left out for lack of a photo ({len(missing)}): {', '.join(missing)}")


if __name__ == "__main__":
    main()
