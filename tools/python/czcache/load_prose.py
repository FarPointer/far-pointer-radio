"""Propose broadcast descriptions from the OneNote prose, conservatively.

Most OneNote notes open with the promo copy that was actually posted for the episode --
one to four paragraphs naming the artists, the station, and the air time. That is the
best `description` source the archive has.

The same files then continue into working notes: bare artist names, "Destroyer?",
"Open with Dreamstate Logic", bandcamp URLs, and the set list itself. Some notes are
*only* working notes and contain no promo copy at all. Publishing any of that would be
worse than publishing nothing, so extraction stops at the first line that looks like
scratch and the result is scored before it is offered.

Nothing here is authoritative. Everything this module produces is a *candidate*, marked
`description_status: "proposed"`, and the build writes both the candidate and the text it
rejected to a review report. Only a human entry in overrides/descriptions.yaml is
"approved". See merge.apply_descriptions.
"""
import datetime as dt
import re

from paths import ONENOTE_DIR

FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.S)
HTML_BLOCK_RE = re.compile(r"<table.*?</table>|<thead.*?</thead>|<colgroup.*?</colgroup>", re.S | re.I)
TAG_RE = re.compile(r"<[^>]+>")

# Lines that are structure or timestamps rather than content.
HEADER_LINE_RE = re.compile(
    r"\A(?:AM|PM|\d{1,2}[:.]\d{2}\s*(?:AM|PM)?|"
    r"(?:mon|tues|wednes|thurs|fri|satur|sun)day,?\s+.*\d{4}|"
    r"\d{1,2}[./]\d{1,2}[./]\d{2,4}|-{3,})\Z",
    re.I,
)

# The note's own title, e.g. "Convergence Zone.012 - May 30 2023" or "Episode 065".
# OneNote exports it as the first body line, so it is header, not copy -- but it is short
# and so was previously read as scratch, which stopped extraction before it began. That
# single miss accounted for most of the notes that yielded no description at all.
TITLE_LINE_RE = re.compile(
    r"\A(?:convergence\s*zone|episode)\b[\s.\-–—#]*\d*\s*[-–—]?\s*"
    r"(?:[A-Za-z]+\s+\d{1,2},?\s*\d{0,4}|\d{1,2}[./]\d{1,2}[./]\d{2,4})?\s*\Z",
    re.I,
)

# Checkbox and bullet markers OneNote leaves inline ("- [ ] This week ...").
BULLET_RE = re.compile(r"\A(?:-\s*\[[ xX]?\]|[-*•]|\d+[.)])\s+")

# The on-air sign-off. Real published text, but it is the same three lines every week and
# the air time already lives in structured fields, so it is trimmed from the tail of a
# description rather than repeated across 60 records.
BOILERPLATE_RE = re.compile(
    r"kser\.org|tunein|smart speaker|90\.7|89\.9|\bKSER\b|\bKXIR\b|"
    r"independent public radio|links? in bio|archive links|internet radio|"
    # "Convergence Zone airs / arrives / returns Tuesday at 10:30pm PDT" -- the verb
    # varies week to week, so match the shape (show, day, clock time) rather than a word.
    r"convergence zone\b[^\n]{0,60}\b\d{1,2}:?\d{0,2}\s*[ap]\.?m\.?|"
    r"\bairs\b[^\n]{0,40}\b\d{1,2}:?\d{0,2}\s*[ap]\.?m\.?",
    re.I,
)

# A line that reads as show-prep rather than promo copy.
URL_RE = re.compile(r"https?://|\bbandcamp\.com|\bwww\.", re.I)
MIC_RE = re.compile(r"\A\\?\[?\s*mic\s*break", re.I)
# "Artist - Song - Album": the set-list shorthand used throughout the notes.
TRACKLINE_RE = re.compile(r"\A[^-]{2,60}\s+-\s+[^-]{2,80}\s+-\s+.{2,}\Z")
LISTLINE_RE = re.compile(r"\A[A-Z][\w'’&. ]+(,\s*[A-Z][\w'’&. ]+){2,},?\Z")

# Signals shared by the genuine promo paragraphs.
POSITIVE_RE = re.compile(
    r"convergence zone|kser|kxir|\bthis week\b|\btonight\b|\btuesday\b|"
    r"streaming|\bpremiere\b|\bI['’]ll\b|\bI['’]ve\b",
    re.I,
)

MIN_WORDS = 8
MIN_CHARS = 120


def _plain_text(raw: str) -> str:
    body = FRONTMATTER_RE.sub("", raw)
    body = HTML_BLOCK_RE.sub("\n", body)
    body = TAG_RE.sub("", body)
    body = body.replace("\\[", "[").replace("\\]", "]").replace("\xa0", " ")
    return body


def _is_scratch(line: str) -> bool:
    """True if this line reads as working notes rather than publishable copy."""
    s = BULLET_RE.sub("", line.strip())
    if not s:
        return False
    if URL_RE.search(s) or MIC_RE.match(s):
        return True
    if s.endswith(":") or s.endswith("?"):
        return True
    if TRACKLINE_RE.match(s) or LISTLINE_RE.match(s):
        return True
    if len(s.split()) < MIN_WORDS:
        return True
    return False


def _trim_boilerplate(kept):
    """Drop the trailing run of station sign-off lines.

    Only from the tail, and only whole lines -- a blurb that *opens* by naming the station
    ("KSER's Fall Membership Drive converges with...") is editorial content and stays.
    """
    while kept and BOILERPLATE_RE.search(kept[-1]):
        kept.pop()
    return kept


def extract(raw: str):
    """Returns (candidate, rejected, score).

    `rejected` is everything after the cut, so a wrong cut shows up in review rather than
    disappearing silently.
    """
    body = _plain_text(raw)
    lines = [ln.strip() for ln in body.split("\n")]

    # Skip the note's header block: blank lines, the exported title, and the created
    # date/time stamp, in whatever order they appear. Bounded so a note that is nothing
    # but headers cannot consume the whole file looking for copy.
    i = 0
    while i < len(lines) and i < 8 and (
            not lines[i] or HEADER_LINE_RE.match(lines[i])
            or TITLE_LINE_RE.match(lines[i])):
        i += 1

    kept = []
    while i < len(lines):
        line = BULLET_RE.sub("", lines[i])
        if not line:
            i += 1
            if kept and i < len(lines) and lines[i] and _is_scratch(lines[i]):
                break
            continue
        if _is_scratch(line):
            break
        kept.append(line)
        i += 1

    # Fallback: some notes open with a one-line teaser or a stray prep line, which stops
    # the leading run before it starts. Rather than lose the blurb entirely, take the
    # longest consecutive run of publishable lines anywhere in the note. Only when the
    # leading run produced nothing -- when it did, it is the more trustworthy of the two.
    if len("\n\n".join(kept).strip()) < MIN_CHARS:
        best, run = [], []
        for line in [BULLET_RE.sub("", ln) for ln in lines]:
            if line and not _is_scratch(line):
                run.append(line)
                continue
            if len(run) > len(best):
                best = run
            run = []
        kept = run if len(run) > len(best) else best
        i = len(lines)

    full = "\n\n".join(kept).strip()
    candidate = "\n\n".join(_trim_boilerplate(list(kept))).strip()
    rejected = "\n".join(ln for ln in lines[i:] if ln).strip()

    if len(candidate) < MIN_CHARS:
        return None, rejected, 0.0

    # Scored on the untrimmed text. Naming the station and the air time is the strongest
    # evidence a paragraph is real promo copy rather than prep -- so scoring the trimmed
    # version would penalise every note for the boilerplate we just removed, which is
    # exactly backwards.
    score = 0.0
    if POSITIVE_RE.search(full):
        score += 0.5
    if re.search(r"kser|kxir|streaming|8:?30|10:?30", full, re.I):
        score += 0.25
    if full.count(".") >= 2:
        score += 0.25
    return candidate, rejected, round(score, 2)


FILE_DATE_PATTERNS = (
    re.compile(r"(\d{2})\.(\d{2})\.(\d{4})"),
    re.compile(r"(\d{2})\.(\d{2})\.(\d{2})(?!\d)"),
    re.compile(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})"),
)

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}


def _dates_from_name(name: str):
    """Every plausible date in a filename, best guess first.

    Filenames are not trustworthy on their own -- one note is named "08.15.2013" for a
    2023 broadcast -- so these are candidates to be checked against real broadcast dates,
    not answers.
    """
    out = []
    for pat in FILE_DATE_PATTERNS:
        for m in pat.finditer(name):
            try:
                if m.re is FILE_DATE_PATTERNS[2]:
                    mo = MONTHS.get(m.group(1).lower())
                    if not mo:
                        continue
                    out.append(dt.date(int(m.group(3)), mo, int(m.group(2))))
                else:
                    y = int(m.group(3))
                    y += 2000 if y < 100 else 0
                    out.append(dt.date(y, int(m.group(1)), int(m.group(2))))
            except ValueError:
                continue
    return out


def _created(raw: str):
    m = re.search(r"^created:\s*(\d{4}-\d{2}-\d{2})", raw, re.M)
    return dt.date.fromisoformat(m.group(1)) if m else None


def load(broadcast_dates):
    """Map each prose note to a broadcast date. Returns {date: {...}}.

    Resolution order: a filename date that *is* a broadcast date wins. Otherwise the note
    is attached to the first broadcast on or after its creation date, within a week --
    prep notes are written in the days before air.
    """
    valid = set(broadcast_dates)
    ordered = sorted(valid)
    out = {}

    for path in sorted(ONENOTE_DIR.rglob("*.md")):
        raw = path.read_text(encoding="utf-8")
        target = None
        for cand in _dates_from_name(path.name):
            if cand.isoformat() in valid:
                target = cand.isoformat()
                break
        if target is None:
            created = _created(raw)
            if created:
                nxt = [d for d in ordered if 0 <= (dt.date.fromisoformat(d) - created).days <= 7]
                target = nxt[0] if nxt else None
        if target is None:
            continue

        candidate, rejected, score = extract(raw)
        prior = out.get(target)
        # More than one note can land on a date; keep the strongest candidate.
        if prior and prior["score"] >= score:
            continue
        out[target] = {
            "file": str(path.relative_to(ONENOTE_DIR)),
            "candidate": candidate,
            "rejected": rejected[:2000],
            "score": score,
        }
    return out


if __name__ == "__main__":
    import load_spinitron

    bcs, _, _ = load_spinitron.load()
    proses = load({b["date"] for b in bcs.values()})
    good = {d: p for d, p in proses.items() if p["candidate"]}
    print(f"notes mapped to a broadcast: {len(proses)}")
    print(f"  with a usable candidate:   {len(good)}")
    for lo in (1.0, 0.75, 0.5):
        n = sum(1 for p in good.values() if p["score"] >= lo)
        print(f"  score >= {lo}: {n}")
    for d, p in sorted(good.items())[:3]:
        print(f"\n─── {d}  score={p['score']}  ({p['file']})")
        print(p["candidate"][:600])
