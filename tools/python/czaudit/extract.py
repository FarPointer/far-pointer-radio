"""Extract set lists from the OneNote show-prep notes.

The tables are hand-built in OneNote and share no common schema, so each file gets an
explicit column map rather than a guessed one. Two quirks drove that decision:

  * Several tables have no header row. OneNote's exporter promoted the first *data*
    row into <th>, so that row is real content and must be read back as data
    (`th_is_data`).
  * Column order is not stable. Episode.065 lists Album BEFORE Song, which a
    positional guess would silently transpose for an entire episode.

Rows that are breaks, or that carry no song at all, are dropped. A few tables use
continuation rows (blank artist, second song by the same artist); those forward-fill
the artist rather than being discarded.
"""
import json
import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

BASE = (Path(__file__).resolve().parents[3]
        / "shows/convergence-zone/playlists/sources/farpointer-onenote")
OUT = Path(__file__).parent / "onenote_episodes.json"

D2023 = "2023 Playlists - Convergence Zone"
D2024 = "2024 Playlists - Convergence Zone"

# air_date -> (relative path, column map, th_is_data)
# Column map values are 0-based indices into the row's <td> list.
SPECS = {
    "2023-05-30": (f"{D2023}/Convergence Zone.012 - May 30 2023.md",
                   {"artist": 0, "song": 1, "time": 2, "album": 3, "notes": 4}, True),
    "2023-06-06": (f"{D2023}/Convergence Zone.013 - June 6 2023.md",
                   {"artist": 0, "song": 1, "time": 2, "album": 3, "date": 5, "notes": 6}, True),
    "2023-07-04": (f"{D2023}/Convergence Zone.017 - July 04 2023.md",
                   {"artist": 0, "song": 1, "time": 2, "album": 3, "label": 4, "notes": 5}, False),
    "2023-07-11": (f"{D2023}/Convergence Zone.018 - July 11 2023.md",
                   {"artist": 0, "song": 1, "time": 2, "album": 3, "label": 4, "notes": 5}, False),
    "2023-08-01": (f"{D2023}/Convergence Zone.019 - August 1 2023.md",
                   {"artist": 0, "song": 1, "time": 2, "album": 3, "label": 4, "notes": 5}, False),
    "2023-08-08": (f"{D2023}/Convergence Zone.020 - August 08 2023.md",
                   {"time": 0, "artist": 1, "song": 2, "album": 3, "notes": 4}, True),
    "2023-08-15": (f"{D2023}/Convergence Zone.021 - 08.15.2013.md",
                   {"time": 0, "artist": 1, "song": 2, "album": 3, "label": 4, "notes": 5}, False),
    "2023-08-22": (f"{D2023}/Convergence Zone.22 - 08.22.23.md",
                   {"artist": 0, "song": 1, "time": 2, "album": 3, "label": 4, "notes": 5}, False),
    # Header row is entirely blank in this file, so nothing is lost by ignoring it.
    # No time column at all.
    "2023-09-26": (f"{D2023}/Convergence Zone.026 - 09.26.23.md",
                   {"artist": 0, "song": 1, "album": 2, "notes": 3}, False),
    # NB: Album precedes Song here. Confirmed against the Bandcamp album URL in the
    # notes column of the first row (barthawkins.bandcamp.com/album/mirror).
    "2024-08-13": (f"{D2024}/Episode.065 - 08.13.2024.md",
                   {"artist": 0, "album": 1, "song": 2, "label": 3, "date": 4, "notes": 6}, False),
    "2024-10-22": (f"{D2024}/Episode 073 - 10.22.2024.md",
                   {"artist": 0, "song": 1, "album": 2, "label": 3, "notes": 4}, False),
    "2025-09-09": (f"{D2024}/Episode 073 - 01.07.2025/09.09.2025 - End of Summer 2025.md",
                   {"artist": 1, "song": 2, "album": 3, "label": 4, "date": 5, "notes": 6}, False),
}

# Non-music rows. Matched against the artist or song cell, case-insensitively.
BREAK_RE = re.compile(
    r"^(mic\s*break|break|talk|intro|outro|station\s*id|psa|underwriting|promo|"
    r"legal\s*id|mic|bumper)\W*$",
    re.I,
)


def cell_text(el) -> str:
    txt = el.get_text(" ", strip=True).replace("\xa0", " ")
    txt = txt.replace("---", " ")
    txt = unicodedata.normalize("NFC", txt)
    return re.sub(r"\s+", " ", txt).strip()


def is_break(*vals) -> bool:
    return any(BREAK_RE.match(v or "") for v in vals)


def extract_file(date: str, rel: str, colmap: dict, th_is_data: bool):
    soup = BeautifulSoup((BASE / rel).read_text(encoding="utf-8"), "lxml")
    table = soup.find("table")
    if table is None:
        return []

    raw_rows = []
    if th_is_data:
        ths = table.find_all("th")
        if ths:
            raw_rows.append([cell_text(t) for t in ths])
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if tds:
            raw_rows.append([cell_text(td) for td in tds])

    tracks, last_artist, seq = [], "", 0
    for cells in raw_rows:
        def get(key):
            i = colmap.get(key)
            return cells[i].strip() if i is not None and i < len(cells) else ""

        artist, song = get("artist"), get("song")
        if is_break(artist, song):
            last_artist = ""          # a break ends any artist run
            continue
        # Continuation row: another song by the artist named on a previous row.
        if not artist and song:
            artist = last_artist
        if artist:
            last_artist = artist
        if not song or not artist:
            continue
        # Section dividers ("HOUR TWO", "Segment two") repeat the same text across
        # the artist and song cells; no real spin does that.
        if artist.strip().lower() == song.strip().lower():
            last_artist = ""
            continue

        seq += 1
        tracks.append({
            "seq": seq,
            "artist": artist,
            "song": song,
            "album": get("album"),
            "label": get("label"),
            "elapsed": get("time"),
            "notes": get("notes")[:400],
            "source_file": Path(rel).name,
        })
    return tracks


def main():
    episodes = {}
    print(f"{'DATE':<12} {'TRACKS':>6}  FILE")
    for date, (rel, colmap, th_is_data) in sorted(SPECS.items()):
        tracks = extract_file(date, rel, colmap, th_is_data)
        episodes[date] = tracks
        print(f"{date:<12} {len(tracks):>6}  {Path(rel).name}")
    OUT.write_text(json.dumps(episodes, indent=1, ensure_ascii=False), encoding="utf-8")
    total = sum(len(v) for v in episodes.values())
    print(f"\ntotal tracks extracted: {total}")
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
