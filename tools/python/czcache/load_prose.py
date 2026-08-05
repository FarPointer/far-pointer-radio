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
    s = line.strip()
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


def extract(raw: str):
    """Returns (candidate, rejected, score).

    `rejected` is everything after the cut, so a wrong cut shows up in review rather than
    disappearing silently.
    """
    body = _plain_text(raw)
    lines = [ln.strip() for ln in body.split("\n")]

    i = 0
    while i < len(lines) and (not lines[i] or HEADER_LINE_RE.match(lines[i])):
        i += 1

    kept = []
    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1
            if kept and i < len(lines) and lines[i] and _is_scratch(lines[i]):
                break
            continue
        if _is_scratch(line):
            break
        kept.append(line)
        i += 1

    candidate = "\n\n".join(kept).strip()
    rejected = "\n".join(ln for ln in lines[i:] if ln).strip()

    if len(candidate) < MIN_CHARS:
        return None, rejected, 0.0

    score = 0.0
    if POSITIVE_RE.search(candidate):
        score += 0.5
    if re.search(r"kser|kxir|streaming|8:?30|10:?30", candidate, re.I):
        score += 0.25
    if candidate.count(".") >= 2:
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
