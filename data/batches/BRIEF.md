# Jaildle research brief

Jaildle is a daily guessing game: the player sees a photo, name and one-line headline of a famous or
news-famous person who is IN PRISON RIGHT NOW, and guesses how long until their release date.
Today is 2026-11-12. Network access is unrestricted. You are one of several researchers, each with a
different category; stay inside yours.

These are real people. A wrong "is in prison" claim, a wrong crime, or a wrong face is harmful.
Accuracy beats volume: skip anyone you cannot verify.

## Who qualifies
- Convicted AND physically in prison/jail today, with a release date at least 3 months away.
- A determinable future date: an official projected release date, an earliest parole-eligibility date
  (fine for life-with-minimum-term sentences), or a full-term date you can compute from sentence + custody start.
- Notable enough that a news reader, fan or true-crime follower would recognise the name or the case.
  Obscure is fine if the case made national news or the person has a Wikipedia article.
- EXCLUDE: life without parole / whole-life / death sentences; release dates after 2080; people only charged
  or awaiting sentence; anyone released, paroled, pardoned, commuted, on bail pending appeal, in a halfway
  house / home confinement (BOP facility type "RRM"), or dead; lifers who are already past their parole
  eligibility date; political prisoners / prisoners of conscience; anyone convicted as a child whose
  identity is protected.
- Do NOT include anyone already in the game: see data/batches/EXISTING.txt.

## How to verify
- US federal: run `python3 /home/user/sentencle/tools/bop_check.py "First Last"` (several names per call is fine).
  It prints facility and projected release date from the Bureau of Prisons locator. Match on age/middle name.
  A federal person with no match, "actual" release date, or an RRM facility does not qualify. Use the BOP date
  and facility exactly, and put the register number in `notes` as "Bureau of Prisons register no. NNNNN-NNN."
- US state: use the state corrections department's offender search where it works, else recent news
  reports citing it. UK/other: recent reliable news + sentence arithmetic (say so in `notes`).
- Confirm current status with a 2026 source wherever the date does not come from a live official record.
- Case facts (counts, dates, sentence): from DOJ/prosecutor releases, Wikipedia or major news.

## Photo
One photo per person showing THAT person (not a victim, co-defendant, lawyer, relative or logo).
- Best: the lead photo from the person's own Wikipedia article if it is a free image, or a booking photo /
  police or government handout. Otherwise a solo news photo.
- Find it on the article/agency page itself (og:image, <img>/<figure> + caption). Do not scrape search-engine
  image results. Wikipedia API calls: at most one every 3 seconds, with a descriptive User-Agent.
- Confirm identity from the caption / alt text / filename, then LOOK at the downloaded image (Read tool):
  one person, face visible, plausible age and sex. Crop posters/composites/group shots to the right person.
  No courtroom sketches. No childhood photos of adults. If unsure, skip the person.
- Save as JPEG fitting within 330x440 px (PIL: convert("RGB"); thumbnail((330,440)); quality 80) to
  /home/user/sentencle/data/img/custom/<PREFIX>-<slug>.jpg (PREFIX is given in your task).

## Output
Write ONE file: /home/user/sentencle/data/batches/<PREFIX>.json — a JSON array, one object per person, with
exactly these fields. Save progress to the file as you go (every ~10 people) so nothing is lost.

{
 "name": "name as the public knows them",
 "knownFor": "max ~8 words: who they are, e.g. 'Former Illinois House Speaker'",
 "headline": "what they did, max ~12 words, plain and factual, sentence case, no full stop. MUST NOT mention the sentence length, years, or release date. No jokes, no puns. Only what they were convicted of.",
 "convictedOf": "the actual counts, one line (note guilty plea if so)",
 "jurisdiction": "'US federal (S.D.N.Y.)' | 'Texas state' | 'England & Wales' | ...",
 "crimeDates": "'2014–2018' or 'March 2022'",
 "custodyStart": "YYYY-MM-DD or YYYY-MM: when the continuous custody that counts toward this sentence began",
 "sentencingDate": "YYYY-MM-DD or YYYY-MM",
 "sentenceLength": "'87 months', '30 years to life', 'Life, minimum 22 years'",
 "facility": "current prison, or ''",
 "releaseDate": "YYYY-MM-DD or YYYY-MM",
 "releaseType": "'official projected release' | 'earliest parole eligibility' | 'computed full term' | 'computed estimate'",
 "releaseRule": "one plain sentence on how time is served there, e.g. 'Federal: no parole. Up to 15% comes off for good conduct, and programme credits can cut more'",
 "birthYear": 1975,
 "sources": ["1-3 URLs; for federal inmates the first is https://www.bop.gov/inmateloc/"],
 "notes": "shown to players after the round: one or two plain sentences on anything they should know about the date (how it was computed, conflicting reports, pending appeal). '' if nothing.",
 "photoFile": "<PREFIX>-<slug>.jpg",
 "photoCredit": "URL of the page the photo came from",
 "photoLicence": "who issued/took it, e.g. 'Wikimedia Commons, CC BY-SA' / 'Harris County booking photo' / 'AP news photo'",
 "confidence": "high (official record seen today) | medium (news-sourced or computed)",
 "wikipedia": "English Wikipedia article title for the person or case, or ''"
}

Do not modify any other file in /home/user/sentencle. Use your own scratch directory
/tmp/claude-0/-home-user/72262d80-a290-5e9c-ac17-1512298bbe57/scratchpad/<PREFIX>/ for scripts and downloads.

Final message (short): how many entries you wrote, how many are high vs medium confidence, and a list of
any entries you are unsure about (identity of photo, status, or date) with the reason.
