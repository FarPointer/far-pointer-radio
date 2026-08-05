"""Decide whether a spin counts as local, and record *why*.

"Local" is two different claims that happen to share a field. An artist can be from the
Pacific Northwest, and a label can be based here -- a Seattle band on a London label and
a London band on a Seattle label are both "local" to some listener, but not in the same
way, and a station reporting local content cares which. So `local_basis` carries the
reason rather than collapsing both into a bare boolean.

Three bases exist:

  artist   -- MichaelG's "From" column, which describes the artist's origin or current
              home. This is the only large source of real locality data (651 populated
              cells across the 28 workbooks).
  label    -- a handful of labels name their city parenthetically ("Neon Sigh (Seattle)").
  dj_flag  -- Spinitron's L flag. The DJ judged it local in the booth but the export does
              not record on what grounds, so it cannot be attributed to artist or label.

The rule is deliberately conservative and text-only. It never guesses from an artist
name, and origin text it cannot classify leaves `local` null -- "not assessed" -- rather
than defaulting to false.
"""
import re

# Washington, D.C. is the reason this list exists as a subtraction. "Born Washington,
# D.C." and "Washington, DC" both appear in the workbooks and both would otherwise match
# a naive /washington/ test.
NOT_PNW_RE = re.compile(r"washington\s*,?\s*d\.?\s*c\.?|\bd\.c\.\b", re.I)

PNW_CITIES = (
    "seattle", "tacoma", "everett", "olympia", "bellingham", "spokane", "bellevue",
    "bothell", "kirkland", "redmond", "renton", "bremerton", "yakima", "richland",
    "snoqualmie", "mount vernon", "anacortes", "bainbridge", "port townsend",
    "port angeles", "chimacum", "freeland", "whidbey", "walla walla", "vashon",
    "portland", "eugene", "salem", "corvallis", "bend", "astoria", "cottage grove",
    "hood river", "boise", "vancouver", "victoria", "burnaby", "surrey",
)

PNW_REGIONS = (
    "pacific northwest", "puget sound", "british columbia", "cascadia", "olympic peninsula",
)

_CITY_RE = re.compile(r"\b(" + "|".join(re.escape(c) for c in PNW_CITIES) + r")\b", re.I)
_REGION_RE = re.compile(r"\b(" + "|".join(PNW_REGIONS) + r")\b|\bPNW\b", re.I)
# States only count with a separator in front, so a stray "or"/"id" in prose cannot match.
_STATE_RE = re.compile(
    r"(?:^|[,/;()\s])(?:WA|OR|ID|BC)(?:[\s,./;)]|$)|"
    r"\b(?:washington|oregon|idaho)\b",
    re.I,
)

# "Neon Sigh (Seattle)" -- a label naming its city. Only the parenthetical is considered;
# a label whose *name* contains a city ("Seattle Sound Records") says nothing about where
# it operates.
_LABEL_PAREN_RE = re.compile(r"\(([^)]*)\)")


def _is_pnw(text: str) -> bool:
    if not text:
        return False
    stripped = NOT_PNW_RE.sub(" ", text)
    if _REGION_RE.search(stripped) or _CITY_RE.search(stripped):
        return True
    return bool(_STATE_RE.search(stripped))


def artist_is_local(origin_raw):
    """(local, basis) for an artist origin string.

    Returns (None, None) when there is no origin text at all -- that is "not assessed",
    which the schema keeps distinct from "assessed, not local".
    """
    if not (origin_raw or "").strip():
        return None, None
    return (True, "artist") if _is_pnw(origin_raw) else (False, None)


def label_origin(label_raw):
    """Pull a location out of a label's parenthetical, if it reads like one.

    Returns (origin_text, is_local) or (None, None). Parentheticals that are clearly not
    places -- "(?)", "(US)", "(Re-released ...)" -- are ignored rather than stored, so
    label_origin_raw stays a location field.
    """
    if not (label_raw or "").strip():
        return None, None
    for inner in _LABEL_PAREN_RE.findall(label_raw):
        text = inner.strip()
        if not text or len(text) > 60:
            continue
        if re.fullmatch(r"[?\d\s.]*", text):
            continue
        if _is_pnw(text):
            return text, True
        # A place we recognise as a place but not as local: keep it, mark not-local.
        if re.search(r"[A-Za-z]{3,}", text) and "," in text:
            return text, False
    return None, None


def resolve(artist_origin_raw=None, label_raw=None, dj_flag=False):
    """Combine every available basis into (local, local_basis, label_origin_raw).

    Any single basis resolving to True makes the spin local; the bases accumulate rather
    than override each other, because they are independent claims.
    """
    bases, verdicts = [], []

    a_local, a_basis = artist_is_local(artist_origin_raw)
    if a_basis:
        bases.append(a_basis)
    if a_local is not None:
        verdicts.append(a_local)

    label_origin_raw, l_local = label_origin(label_raw)
    if l_local:
        bases.append("label")
    if l_local is not None:
        verdicts.append(l_local)

    if dj_flag:
        bases.append("dj_flag")
        verdicts.append(True)

    if not verdicts:
        return None, [], label_origin_raw
    local = any(verdicts)
    return local, (sorted(set(bases)) if local else []), label_origin_raw
