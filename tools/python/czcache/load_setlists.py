"""Load the pre-air set lists: the convergencezone.fm playlists and the OneNote tables.

Both describe the same thing -- what the show intended to play -- and where both exist
for an episode they hold the same tracks, the site version with cleaner text. So they
are one class with a preference order (site first, OneNote as fallback) rather than two.

Set lists are bound to broadcasts by *content*, never by date. A published playlist names
the date it was written for, which for a replay is months before the airing being
described, and the show is re-aired from automation during hiatus -- so one set list
legitimately describes several broadcasts. czaudit.scrape_site.bind_broadcasts already
encodes that reasoning and its thresholds; this module reuses it rather than restating it.

The OneNote tables are hand-built and share no schema, so each file carries an explicit
column map. czaudit maps the twelve its audit needed; the twelve added here cover the
rest. They live in this module rather than in czaudit/extract.py so that extending the
cache cannot silently change the audit workbook's contents.
"""
import csv
import re
import sys
from pathlib import Path

from paths import CZAUDIT, CZFM_DIR, ONENOTE_DIR

sys.path.insert(0, str(CZAUDIT))
from extract import SPECS as CZAUDIT_SPECS  # noqa: E402
from extract import extract_file
from matching import overlap  # noqa: E402

D2023 = "2023 Playlists - Convergence Zone"
D2024 = "2024 Playlists - Convergence Zone"

# The twelve tables czaudit does not map. Values are 0-based indices into each row's
# cells; `th_is_data` marks the tables where OneNote's exporter promoted the first *data*
# row into <th>, so that row is content and must be read back.
EXTRA_SPECS = {
    "2023-04-11": (f"{D2023}/Convergence Zone 005 April 11 2023.md",
                   {"artist": 0, "song": 1, "album": 2, "label": 3, "notes": 4}, True),
    "2023-04-18": (f"{D2023}/Convergence Zone 006 April 18 2023.md",
                   {"artist": 0, "song": 1, "album": 2, "notes": 3}, True),
    "2023-04-25": (f"{D2023}/Convergence Zone 007 April 25 2023.md",
                   {"artist": 0, "song": 1, "album": 2}, True),
    "2023-05-02": (f"{D2023}/Convergence Zone.008 May 2 2023.md",
                   {"artist": 0, "song": 1, "album": 2, "label": 3, "notes": 4}, True),
    # Real header row, and an unusual column order: Song and Album precede Artist.
    "2023-05-09": (f"{D2023}/Convergence Zone.009 - May 9 2023.md",
                   {"time": 0, "song": 1, "album": 2, "artist": 3, "date": 4, "notes": 5}, False),
    "2023-05-16": (f"{D2023}/Convergence Zone.010 - May 16 2023.md",
                   {"time": 0, "song": 1, "album": 2, "artist": 3, "date": 4, "notes": 5}, False),
    "2023-06-20": (f"{D2023}/Convergence Zone.015 - June 20 2023.md",
                   {"artist": 0, "song": 1, "time": 2, "album": 3, "notes": 4}, True),
    "2023-10-31": (f"{D2023}/Convergence Zone.031 - 10.31.23.md",
                   {"artist": 0, "song": 1, "album": 2, "notes": 3}, True),
    "2024-03-12": (f"{D2024}/Episode.048 - 03.12.2024 - 1 Yr Anniversary.md",
                   {"artist": 0, "song": 1, "album": 2, "label": 3, "date": 4}, False),
    "2024-04-09": (f"{D2024}/Episode 052 - 04.09.2024.md",
                   {"artist": 0, "song": 1, "album": 2, "date": 3, "label": 4}, True),
    # "Local?" sits at index 4; it is a set-list author's guess, not a resolved locality,
    # so it is not read into the `local` field.
    "2024-08-06": (f"{D2024}/Episode.064 - 08.06.2024.md",
                   {"artist": 0, "song": 1, "album": 2, "date": 3, "notes": 5}, False),
}

# One table does not have separate artist and song columns at all: it lists
# "Depeche Mode, New Life" in a single cell, with gear/personnel notes alongside. Split
# on the first comma. Handled apart from SPECS because no column map can express it.
COMBINED_SPECS = {
    "2025-10-21": (f"{D2024}/Episode 073 - 01.07.2025/10.21.2025 - ARP Anniversary.md",
                   0, 1),   # (path, combined artist+song column, notes column)
}

CZFM_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)\.csv$")
EPISODE_RE = re.compile(r"(?:episode|convergence-zone)[-.]?(\d{2,3})\b")


def parse_offset(v):
    """'02:50' or '01:11:03' -> seconds from show start. None if unparseable."""
    v = (v or "").strip()
    if not re.fullmatch(r"\d{1,2}(:\d{2}){1,2}", v):
        return None
    parts = [int(p) for p in v.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def load_czfm():
    """The scraped WordPress playlists, keyed by slug."""
    out = {}
    for path in sorted(CZFM_DIR.glob("*.csv")):
        m = CZFM_DATE_RE.match(path.name)
        if not m:
            continue
        first_aired, slug = m.group(1), m.group(2)
        tracks = []
        with open(path, encoding="utf-8-sig") as fh:
            for row in csv.DictReader(fh):
                artist = (row.get("artist") or "").strip()
                song = (row.get("song") or "").strip()
                if not artist or not song:
                    continue
                tracks.append({
                    "seq": len(tracks) + 1,
                    "artist": artist,
                    "song": song,
                    "album": (row.get("album") or "").strip(),
                    "label": (row.get("label") or "").strip(),
                    "notes": (row.get("notes") or "").strip(),
                    "offset_seconds": parse_offset(row.get("time")),
                    "elapsed": (row.get("time") or "").strip(),
                })
        if not tracks:
            continue
        ep = EPISODE_RE.search(path.name.lower())
        out[f"czfm:{path.stem}"] = {
            "source": "wordpress",
            "first_aired": first_aired,
            "episode_number": int(ep.group(1)) if ep else None,
            "file": path.name,
            "tracks": tracks,
        }
    return out


def _load_combined(date, rel, combined_col, notes_col):
    """The one table whose artist and song share a cell."""
    from bs4 import BeautifulSoup
    from extract import cell_text

    soup = BeautifulSoup((ONENOTE_DIR / rel).read_text(encoding="utf-8"), "lxml")
    table = soup.find("table")
    if table is None:
        return []

    rows = [[cell_text(c) for c in table.find_all("th")]] if table.find_all("th") else []
    rows += [[cell_text(td) for td in tr.find_all("td")]
             for tr in table.find_all("tr") if tr.find_all("td")]

    tracks = []
    for cells in rows:
        raw = cells[combined_col] if combined_col < len(cells) else ""
        if "," not in raw:
            continue
        artist, song = (p.strip() for p in raw.split(",", 1))
        if not artist or not song:
            continue
        tracks.append({
            "seq": len(tracks) + 1, "artist": artist, "song": song,
            "album": "", "label": "",
            "notes": cells[notes_col] if notes_col < len(cells) else "",
            "offset_seconds": None, "elapsed": "",
        })
    return tracks


def load_onenote():
    """OneNote set-list tables, keyed by air date stated in the note."""
    out = {}
    specs = {**CZAUDIT_SPECS, **EXTRA_SPECS}
    for date, (rel, colmap, th_is_data) in sorted(specs.items()):
        tracks = extract_file(date, rel, colmap, th_is_data)
        if not tracks:
            continue
        for t in tracks:
            t["offset_seconds"] = parse_offset(t.get("elapsed"))
        ep = EPISODE_RE.search(Path(rel).name.lower().replace(" ", ""))
        out[f"onenote:{date}"] = {
            "source": "onenote", "first_aired": date, "file": Path(rel).name,
            "episode_number": int(ep.group(1)) if ep else None, "tracks": tracks,
        }

    for date, (rel, cc, nc) in sorted(COMBINED_SPECS.items()):
        tracks = _load_combined(date, rel, cc, nc)
        if tracks:
            out[f"onenote:{date}"] = {
                "source": "onenote", "first_aired": date, "file": Path(rel).name,
                "episode_number": None, "tracks": tracks,
            }
    return out


def load():
    """Every set list, site playlists first so they win ties during binding."""
    return {**load_czfm(), **load_onenote()}


def bind(setlists, broadcasts, floor=0.30, replay_floor=0.60):
    """Choose one set list per broadcast. Returns {broadcast_id: binding}.

    Mirrors czaudit.scrape_site.bind_broadcasts: a set list whose stated date matches the
    broadcast only has to clear a low bar, because a show drifting from its own plan is
    ordinary. One claiming a different date has to look like a near-complete reproduction
    before it is accepted as describing a replay.
    """
    bindings = {}
    for bid, b in broadcasts.items():
        spins = b["raw_spins"]
        scored = sorted(
            ((overlap(sl["tracks"], spins), 0 if sl["source"] == "wordpress" else 1, key)
             for key, sl in setlists.items()),
            key=lambda x: (-x[0], x[1], x[2]),
        )
        if not scored:
            continue
        score, _, key = scored[0]
        corroborated = setlists[key]["first_aired"] == b["date"]
        if score < (floor if corroborated else replay_floor):
            continue
        # The runner-up is only evidence of ambiguity if it describes a *different*
        # episode. Most episodes have both a site playlist and a OneNote note, and those
        # two scoring alike is agreement, not doubt.
        rival = next(((s, k) for s, _, k in scored[1:]
                      if setlists[k]["first_aired"] != setlists[key]["first_aired"]),
                     None)
        bindings[bid] = {
            "setlist": key,
            "score": round(score, 4),
            "corroborated": corroborated,
            # Two unrelated set lists scoring alike means the match is not distinctive
            # enough to trust silently; that is a human's call, not a max().
            "ambiguous": bool(rival) and (score - rival[0]) < 0.15,
            "runner_up": [rival[1], round(rival[0], 4)] if rival else None,
        }
    return bindings


if __name__ == "__main__":
    import load_spinitron

    sls = load()
    czfm = sum(1 for k in sls if k.startswith("czfm:"))
    print(f"set lists: {len(sls)}  (czfm {czfm}, onenote {len(sls) - czfm})")
    print(f"tracks: {sum(len(s['tracks']) for s in sls.values())}")

    bcs, _, _ = load_spinitron.load()
    binds = bind(sls, bcs)
    print(f"\nbroadcasts with a set list: {len(binds)} of {len(bcs)}")
    print(f"  ambiguous: {sum(1 for v in binds.values() if v['ambiguous'])}")
    print(f"  uncorroborated (replay bindings): "
          f"{sum(1 for v in binds.values() if not v['corroborated'])}")
    reuse = {}
    for v in binds.values():
        reuse.setdefault(v["setlist"], 0)
        reuse[v["setlist"]] += 1
    multi = {k: n for k, n in reuse.items() if n > 1}
    print(f"  set lists bound to more than one broadcast: {len(multi)}")
    for k, n in sorted(multi.items(), key=lambda kv: -kv[1])[:8]:
        print(f"    {n}x  {k}")
