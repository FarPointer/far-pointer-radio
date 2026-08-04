"""Text normalisation and similarity shared by the scraper and the audit builder.

These live in one place because the scraper uses them to decide *which* Spinitron
playlist a published page belongs to, and the audit uses them to decide which spin a
track matches. If the two disagreed, a page could be bound to one playlist and then
audited as though it were another.
"""
import re
import unicodedata
from difflib import SequenceMatcher

FEAT_RE = re.compile(r"\s*[\(\[]?\b(feat|ft|featuring|with)\b\.?\s.*$", re.I)
PAREN_RE = re.compile(r"[\(\[][^)\]]*[)\]]")
NOISE_RE = re.compile(r"\b(remaster(ed)?|mono|stereo|edit|version|mix|remix|"
                      r"single|album|radio|live|bonus|track|deluxe)\b", re.I)


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def norm(s: str, drop_paren: bool = False) -> str:
    """Normalise a title or artist for comparison."""
    s = strip_accents((s or "").lower())
    s = s.replace("&", " and ").replace("’", "'").replace("“", '"').replace("”", '"')
    s = FEAT_RE.sub("", s)
    if drop_paren:
        s = PAREN_RE.sub(" ", s)
        s = NOISE_RE.sub(" ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"^(the|a|an)\s+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def artist_score(a: str, b: str) -> float:
    """Similarity between two artist strings, tolerant of collaboration credits.

    Spinitron often logs only the lead artist where the note spells out everyone
    ('Sin Fang' vs 'Sin fang kjartan holm fischersund'). Plain string similarity
    collapses on those, so treat one artist's tokens being a subset of the other's
    as a near-certain match instead.
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    ta, tb = set(a.split()), set(b.split())
    if ta and tb and (ta <= tb or tb <= ta):
        return 0.95
    return ratio(a, b)


def track_keys(tracks):
    """A set of 'artist|song' keys for overlap scoring between two playlists."""
    return {f"{norm(t.get('artist', ''), True)}|{norm(t.get('song', ''), True)}"
            for t in tracks if t.get("artist") and t.get("song")}


def overlap(a_tracks, b_tracks) -> float:
    """Share of the smaller playlist's tracks that also appear in the larger.

    Used to bind a published page to a Spinitron playlist. Deliberately strict --
    exact normalised artist+song only -- because a loose score would happily bind a
    replay to the wrong week, and neighbouring weeks share very few exact pairs.
    """
    ka, kb = track_keys(a_tracks), track_keys(b_tracks)
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / min(len(ka), len(kb))
