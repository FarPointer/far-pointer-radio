"""Parse MichaelG's per-episode workbooks into canonical, ordered track lists.

These are the best source the archive has for the 28 episodes they cover: written after
the show, complete, ordered, and carrying artist origins and long-form notes that exist
nowhere else. Everything here treats the workbook as authoritative and Spinitron as the
thing that fills in gaps.

The files are hand-made, so the parser is header-driven rather than positional. Five
layouts exist across 28 files and one of them has no ordering column at all, so sequence
always comes from row position -- the "Order" column is decorative ("1.1", "1.1.1") and
in one file holds clock times instead.

The one hazard worth stating plainly: **the air date comes from the filename, never the
title cell.** Four files carry a title-cell date that disagrees with their filename
(2026.04.14 says "March 31, 2025"). All 28 filename dates match a real broadcast; none
of the four title-cell dates do.
"""
import datetime as dt
import re

import openpyxl

from paths import MICHAELG_DIR

# Column aliases -> canonical field. Header text is lowercased and stripped first.
COLUMNS = {
    "artist": "artist",
    "song": "song", "track": "song",
    "from": "origin", "origin": "origin", "location": "origin",
    "album": "release", "album/single": "release", "release": "release",
    "released": "released", "year": "released",
    "label": "label",
    "comments/notes": "notes", "notes": "notes", "comments": "notes",
    "mic summary": "notes",          # 2026-06-23 renamed the column
    "order": "order", "time": "order",
    "verify clean": "verify_clean",  # 2026-03-17 only; an internal review flag
}

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}

FILENAME_DATE_RE = re.compile(r"(\d{4})\.(\d{2})\.(\d{2})")


def _text(v):
    """Cell -> trimmed string, with internal newlines collapsed to spaces."""
    if v is None:
        return ""
    if isinstance(v, (dt.datetime, dt.date)):
        return v.isoformat()
    s = str(v).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def _first_line(v):
    """First line of a cell.

    Artist and song cells sometimes carry a second line of commentary -- a pronunciation
    guide ("Bete Grise / Beht Greeze"), a band-member note. Keeping it would corrupt
    every match against Spinitron, so only the first line is the name.
    """
    if v is None:
        return ""
    s = str(v).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s.split("\n")[0]).strip()


def parse_released(raw):
    """Messy release text -> (partial ISO date, precision).

    The workbooks are far more precise than Spinitron here -- roughly 43% of values name
    a month or a day where Spinitron records only a year -- which is why this is worth
    parsing rather than passing through. Reissue commentary ("1996 (original on Relic)
    1998 (Reissue)") is discarded and the first date wins.
    """
    s = _text(raw)
    if not s:
        return None, None

    # "March 13, 2026" / "March 13 2026"
    m = re.search(r"\b([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})\b", s)
    if m and m.group(1).lower() in MONTHS:
        mo = MONTHS[m.group(1).lower()]
        day = int(m.group(2))
        if 1 <= day <= 31:
            return f"{int(m.group(3)):04d}-{mo:02d}-{day:02d}", "day"

    # "June 2024"
    m = re.search(r"\b([A-Za-z]+)\s+(\d{4})\b", s)
    if m and m.group(1).lower() in MONTHS:
        return f"{int(m.group(2)):04d}-{MONTHS[m.group(1).lower()]:02d}", "month"

    # ISO, occasionally produced when Excel stored the cell as a real date.
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s)
    if m:
        return m.group(0)[:10], "day"

    m = re.search(r"\b(19|20)\d{2}\b", s)
    if m:
        return m.group(0), "year"

    return None, None


def find_header(rows):
    """Index of the header row: the first row naming both an artist and a song column."""
    for i, row in enumerate(rows[:8]):
        vals = {_text(c).lower() for c in row if c is not None}
        if "artist" in vals and ({"song", "track"} & vals):
            return i
    return None


def parse_file(path):
    """One workbook -> dict with air_date, tracks, and the layout it used."""
    m = FILENAME_DATE_RE.search(path.name)
    if not m:
        raise SystemExit(f"{path.name}: no YYYY.MM.DD date in the filename")
    air_date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        rows = list(wb["Sheet1"].iter_rows(values_only=True))
    finally:
        wb.close()

    hi = find_header(rows)
    if hi is None:
        raise SystemExit(f"{path.name}: could not find a header row")

    header = [_text(c).lower() for c in rows[hi]]
    colmap = {}
    for idx, name in enumerate(header):
        field = COLUMNS.get(name)
        if field and field not in colmap:
            colmap[field] = idx

    title_cell = next((_text(c) for r in rows[:hi] for c in r if _text(c)), None)

    tracks = []
    for row in rows[hi + 1:]:
        def get(field, first_line=False):
            i = colmap.get(field)
            if i is None or i >= len(row):
                return ""
            return _first_line(row[i]) if first_line else _text(row[i])

        artist, song = get("artist", True), get("song", True)
        if not artist or not song:
            continue

        released, precision = parse_released(get("released"))
        tracks.append({
            "seq": len(tracks) + 1,          # row position; "Order" is not a number
            "artist": artist,
            "song": song,
            "release": get("release"),
            "label": get("label"),
            "released_date": released,
            "released_precision": precision,
            "origin": get("origin"),
            "notes": get("notes"),
        })

    return {
        "air_date": air_date,
        "file": path.name,
        "title_cell": title_cell,
        "columns": [h for h in header if h],
        "tracks": tracks,
    }


def load():
    """All 28 workbooks, keyed by air date from the filename."""
    out = {}
    for path in sorted(MICHAELG_DIR.glob("*.xlsx")):
        if path.name.startswith("~$"):       # Excel lock file
            continue
        wb = parse_file(path)
        if wb["air_date"] in out:
            raise SystemExit(f"two workbooks claim {wb['air_date']}")
        out[wb["air_date"]] = wb
    return out


def title_cell_mismatches(workbooks):
    """Files whose title-cell date disagrees with their filename date.

    Reported, never acted on. Kept visible because a silent disagreement between a
    filename and the text inside the file is exactly the kind of thing that later gets
    'fixed' in the wrong direction.
    """
    out = []
    for date, wb in sorted(workbooks.items()):
        m = re.match(r"([A-Za-z]+)\s+(\d{1,2}),?\s*(\d{4})", wb["title_cell"] or "")
        if not m or m.group(1).lower() not in MONTHS:
            continue
        stated = (f"{int(m.group(3)):04d}-{MONTHS[m.group(1).lower()]:02d}"
                  f"-{int(m.group(2)):02d}")
        if stated != date:
            out.append({"air_date": date, "file": wb["file"],
                        "title_cell": wb["title_cell"], "stated_date": stated})
    return out


if __name__ == "__main__":
    wbs = load()
    total = sum(len(w["tracks"]) for w in wbs.values())
    print(f"workbooks: {len(wbs)}   tracks: {total}")
    layouts = {}
    for w in wbs.values():
        layouts.setdefault(tuple(w["columns"]), []).append(w["air_date"])
    print(f"\ndistinct layouts: {len(layouts)}")
    for cols, dates in sorted(layouts.items(), key=lambda kv: -len(kv[1])):
        print(f"  {len(dates):>2}x  {' | '.join(cols)}")
        if len(dates) <= 3:
            print(f"        {dates}")
    print("\ntitle-cell date mismatches (filename wins):")
    for m in title_cell_mismatches(wbs):
        print(f"  {m['air_date']}  file says {m['stated_date']}  ({m['file']})")
    prec = {}
    for w in wbs.values():
        for t in w["tracks"]:
            prec[t["released_precision"]] = prec.get(t["released_precision"], 0) + 1
    print(f"\nreleased precision: {prec}")
