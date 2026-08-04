"""Parse playlists that were published as text rather than as an HTML table.

Roughly half the posts on convergencezone.fm never used a table. They list the set as
lines inside a paragraph, broken by <br>, in several styles that changed over time:

    Destroyer - Savage Night at the Opera - 00:00          (artist - song - elapsed)
    Patricia Wolf / Pacific Coast Highway / See-Through / 6:00 / 2022   (slash columns)
    Hibou - Valium - Hibou                                 (artist - song - album)
    FCS North - Police Laughter                            (artist - song)

The hard part is not the splitting, it is telling a set list apart from prose. Every post
opens with a few sentences that also contain dashes, and some posts are articles about
music with no set list at all. So a line style only counts when it repeats: the parser
takes the longest consecutive run of lines in one style and rejects anything shorter than
MIN_RUN, which prose never reaches.
"""
import re

MIN_RUN = 5
# A run may be interrupted by this many stray lines ('[Mic break]', 'HOUR TWO') before
# it is considered ended.
MAX_GAP = 2

TIME_RE = re.compile(r"^(?:\d{1,2}:)?\d{1,2}:\d{2}$")
DASH_RE = re.compile(r"\s+[–—-]\s+")
YEAR_RE = re.compile(r"^(19|20)\d{2}$")
SKIP_RE = re.compile(
    r"^(\[.*\]|\(.*\)|mic\s*break|break|track\s*list\s*[–—-]?|"
    r"hour\s*(one|two|three|\d)|first\s+hour|second\s+hour|set\s+\w+|"
    r"opens in new tab|\W*)$", re.I)
# Lines that are navigation or promo, not spins, even though they may contain dashes.
NOISE_RE = re.compile(
    r"(kser|kxir|playlist link|playlist &|archive and playlist|tunein|"
    r"convergence zone arrives|opens in new tab|first aired|streaming at|"
    r"spotify|tidal|mixcloud|bandcamp|donate|membership)", re.I)


# The header of the slash style is itself a well-formed row, so name it explicitly.
HEADER_RE = re.compile(r"^(artist|track|song|time|#)\b", re.I)


def _plausible(rec):
    """Reject prose that happens to contain a separator.

    Opening paragraphs are full of dashes ('...rituals and magic - the festive season
    can be a time for...') and split into perfectly valid-looking fields. What gives them
    away is length: performer names and song titles are short, sentences are not.
    """
    if not rec or not rec["artist"] or not rec["song"]:
        return False
    if HEADER_RE.match(rec["artist"]) and not rec["time"]:
        return False
    a, s = rec["artist"], rec["song"]
    if len(a) > 60 or len(a.split()) > 9:
        return False
    if len(s) > 110 or len(s.split()) > 16:
        return False
    # A sentence fragment usually ends in punctuation a title would not.
    return not a.endswith((",", ";", ":")) and "  " not in a


def _slash(line):
    parts = [p.strip() for p in line.split(" / ")]
    if len(parts) < 3:
        return None
    # 'Artist / Song / Release / Duration / Released'. The clock-looking field here is
    # track DURATION, not an offset from the top of the show, so it is deliberately
    # dropped: 'time' means elapsed position everywhere else, and mixing the two would
    # push the audit's suggested spin times minutes or hours off.
    return {"artist": parts[0], "song": parts[1], "album": parts[2],
            "label": "", "time": "", "notes": ""}


def _dashed(line):
    parts = [p.strip() for p in DASH_RE.split(line) if p.strip()]
    if len(parts) < 2:
        return None
    time = ""
    if TIME_RE.match(parts[-1]):
        time = parts.pop()
        if len(parts) < 2:
            return None
    artist, rest = parts[0], parts[1:]
    if not artist or not rest:
        return None
    # Only the artist boundary is reliable. A song title can itself contain a dash
    # ('Newgrange (2003 - Remaster)'), so everything after the first separator is the
    # song -- except a trailing field that looks like an album on the no-time styles.
    if time or len(rest) == 1:
        song, album = " - ".join(rest), ""
    else:
        song, album = " - ".join(rest[:-1]), rest[-1]
    return {"artist": artist, "song": song, "album": album,
            "label": "", "time": time, "notes": ""}


def _candidates(lines, fn):
    """Longest consecutive run of lines that parse with fn, allowing small gaps."""
    best, cur, gap = [], [], 0
    for ln in lines:
        if SKIP_RE.match(ln):
            continue
        rec = None if NOISE_RE.search(ln) else fn(ln)
        if rec and not _plausible(rec):
            rec = None
        if rec:
            cur.append(rec)
            gap = 0
        elif cur:
            gap += 1
            if gap > MAX_GAP:
                best, cur, gap = max(best, cur, key=len), [], 0
    return max(best, cur, key=len)


CLOCK_RE = re.compile(r"^\d{1,2}:\d{2}\s*(AM|PM)$", re.I)
FROM_RE = re.compile(r"^[“\"'](.+)[”\"']\s+from$", re.I)


def _blocks(lines):
    """The five-line-per-track style, one field per line.

        10:30 PM / Little H Collective / "Avalanche Pass" from / Avalanche Pass / 2023

    Anchored on the clock line and the quoted 'song from' line, both of which prose
    does not produce, so no length heuristics are needed here.
    """
    out, i = [], 0
    while i < len(lines) - 3:
        if CLOCK_RE.match(lines[i]) and (m := FROM_RE.match(lines[i + 2])):
            album = lines[i + 3]
            year = i + 4 < len(lines) and YEAR_RE.match(lines[i + 4])
            out.append({"artist": lines[i + 1], "song": m.group(1), "album": album,
                        "label": "", "time": lines[i], "notes": ""})
            i += 5 if year else 4
        else:
            i += 1
    return out


def parse_text_playlist(lines):
    """Best set list found in a post's text lines, or []."""
    best = _blocks(lines)
    for fn in (_slash, _dashed):
        run = _candidates(lines, fn)
        if len(run) > len(best):
            best = run
    if len(best) < MIN_RUN:
        return []
    return [{"position": i, **r} for i, r in enumerate(best, 1)]
