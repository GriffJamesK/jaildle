# Jaildle

A daily guessing game: how long until a famous inmate's release date?

- `docs/` is the built game: `index.html` plus one photo per person in `docs/i/`. Host the folder anywhere.
- `docs/desk/` is **Jaildle Desk**, a free-play fork built from `src/desk.html`: call inmates to a records window one after another, read their papers on a desk you can rearrange, and file an estimate. It uses the same people and photos, plus a pixel portrait of each in `docs/p/` made by `build.py`.
- `data/people.json` is the list. Edit it, then run `python3 build.py` to rebuild.
- `build.py` pulls each person's lead photo from their Wikipedia article (`wikipediaTitle`) and embeds it.
  People with no freely licensed photo are left out of the game. To include one, put a JPEG in
  `data/img/custom/` and set `"photoFile": "name.jpg"` (and optionally `"photoCredit": "<url>"`) on their entry.
- Other days: the arrows beside the case number replay past cases. Players cannot go past today. To preview future days yourself, run `python3 build.py --dev` and open `docs/index.html` locally; never publish that build.
- `tools/portraits.py` makes the Desk game's window portraits in `data/portraits/`: it cuts each person out of their photo, sizes the head by the detected face, and reduces it to flat colours. Run it after adding people (needs `pip install rembg onnxruntime opencv-python-headless`), then run `build.py`. Don't run the two at the same time.
- `tools/recheck.py` re-checks the cases for the next 7 days (or `--days N`, or `--all`) against the Bureau of Prisons record and lists anyone released, moved or re-dated. Non-federal cases are listed for a manual check.
- `tools/bop_check.py "First Last"` looks up a US federal inmate's official projected release date.

The daily case follows the order of `data/people.json`: case no. 1 (12 November 2026) is the first entry, and so on, skipping anyone within two months of release. Add new people at the end so existing days keep their cases. `tools/merge_batches.py` checks researched batches in `data/batches/` and appends the ones that pass.

Release dates move. Re-check the list every few months, and remove anyone who is released, pardoned or wins an appeal.
