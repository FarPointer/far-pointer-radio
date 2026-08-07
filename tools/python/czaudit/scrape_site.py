"""Parse the published playlists from convergencezone.fm into per-episode CSVs.

Unlike the OneNote notes, these pages carry a real header row, so columns are mapped by
header name rather than position. Header wording still varies across episodes
('Song' vs 'Title', 'Time' vs 'Start Time', 'Notes' vs 'Show notes'), hence the alias
table below. Posts that published the set as text rather than as a table are handled by
textlist.py.

Rows that name an hour ('First Hour', 'Second Hour') are section dividers and carry no
song; they are dropped along with any other row that has no song text.

Every post in the sitemap is parsed -- there is no hand-maintained page list -- and each
Spinitron broadcast is then bound to the playlist it matches by song overlap rather than
by trusting any page's date. See bind_broadcasts for why.
"""
import csv
import datetime as dt
import json
import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

from matching import overlap
from textlist import parse_text_playlist

HERE = Path(__file__).parent
HTML_DIR = HERE / "site_html"
SITEMAP = HTML_DIR / "sitemap-posts.xml"
OUT_JSON = HERE / "site_episodes.json"
SOURCES = Path(__file__).resolve().parents[3] / "shows/convergence-zone/playlists/sources"
# The same export czcache builds from, so the audit and the cache can never disagree
# about what Spinitron says. The older Spinssearchresults84208326forKSER.csv holds the
# identical 3,282 spins but lacks DJ ID and Playlist Date-time.
SPINS_CSV = SOURCES / "spinitron" / "Spins-search-results-12-8-19-8-7-26-for-KSER.csv"
OUT_CSV_DIR = SOURCES / "convergencezone.fm"

ALIASES = {
    "artist": "artist", "artists": "artist", "artist name": "artist",
    "song": "song", "title": "song", "track": "song", "track name": "song",
    "song name": "song", "song title": "song",
    "time": "time", "start time": "time", "starttime": "time",
    "album": "album", "release": "album", "album name": "album",
    "label": "label",
    "notes": "notes", "show notes": "notes", "note": "notes",
}

HOUR_RE = re.compile(r"^(first|second|third|hour|set)\b.*hour|^hour\b", re.I)
BREAK_RE = re.compile(r"^(mic\s*break|break|talk|intro|outro|station\s*id|psa|"
                      r"underwriting|promo|legal\s*id|mic|bumper)\W*$", re.I)

# 'first aired 06.11.2024' and 'first aired June 6 2023' both occur, the latter usually
# in the caption of the Mixcloud embed rather than in the body copy.
AIRED_NUM = re.compile(
    r"(?:first\s+)?aired[^0-9]{0,8}(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})", re.I)
AIRED_WORD = re.compile(
    r"(?:first\s+)?aired\s+([A-Z][a-z]+)\.?\s+(\d{1,2}),?\s+(\d{4})", re.I)
MONTHS = {m.lower(): i for i, m in enumerate(
    "January February March April May June July August September October November "
    "December".split(), 1)}


def txt(el) -> str:
    s = el.get_text(" ", strip=True).replace("\xa0", " ")
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def load_spin_playlists():
    """Spinitron playlist date -> list of {artist, song}, in log order."""
    by_date = {}
    with open(SPINS_CSV, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            d = dt.datetime.strptime(r["Playlist Date"], "%b %d, %Y").date()
            by_date.setdefault(d, []).append({"artist": r["Artist"], "song": r["Song"]})
    return by_date


def page_date(soup, body):
    """The air date the page claims, and how it was found."""
    body_text = body.get_text(" ", strip=True)
    if (m := AIRED_NUM.search(body_text)):
        mo, d, y = (int(x) for x in m.groups())
        return dt.date(y + 2000 if y < 100 else y, mo, d), "page"
    if (m := AIRED_WORD.search(body_text)) and m.group(1).lower() in MONTHS:
        return dt.date(int(m.group(3)), MONTHS[m.group(1).lower()],
                       int(m.group(2))), "page"
    pub = soup.find("meta", property="article:published_time")
    if not pub:
        return None, "none"
    # The show airs Tuesday; posts are often published the night of or the day after,
    # so walk back to the Tuesday on or before the publish date.
    d = dt.date.fromisoformat(pub["content"][:10])
    return d - dt.timedelta(days=(d.weekday() - 1) % 7), "published"


def dedupe(playlists, same=0.95):
    """Collapse pages that publish the identical playlist.

    The site carries both 'convergence-zone-004-playlist' and
    'replay-convergence-zone-004' with identical track tables. Left separate they tie on
    every binding and make each other look ambiguous. The canonical page wins; the
    replay post is a repost of it.
    """
    dropped = {}
    for slug in sorted(playlists, key=lambda s: s.startswith("replay-")):
        if slug in dropped:
            continue
        for other in sorted(playlists):
            if other == slug or other in dropped:
                continue
            if overlap(playlists[slug]["tracks"], playlists[other]["tracks"]) >= same:
                dropped[other] = slug
    for slug in dropped:
        playlists.pop(slug)
    return dropped


def bind_broadcasts(playlists, spin_playlists, floor=0.30, replay_floor=0.60):
    """Map each Spinitron broadcast to the published playlist it matches.

    Deliberately in this direction, one reference per broadcast, because the show is
    replayed from automation during vacations and hiatus. A single published playlist
    therefore describes several broadcasts -- its original airing plus every replay --
    so binding a page to one date would silently discard the rest.

    Songs, not dates, do the identifying: a page states the date of the broadcast it was
    written for, which for a replay is months before the airing being audited, and a few
    pages carry no usable date. The date is still worth something as corroboration,
    though, so it sets how strong the content match has to be. When the page claims the
    date being bound, a weak score just means the show drifted from its own set list.
    When it does not, only a near-complete reproduction is credible as a replay --
    distinct consecutive weeks overlap around 0.00-0.08 and real replays 0.6-0.96, so a
    middling score is two shows sharing a few tracks, not a rerun.
    """
    bindings = {}
    for date, spins in spin_playlists.items():
        scored = sorted(((overlap(p["tracks"], spins), slug)
                         for slug, p in playlists.items()), reverse=True)
        if not scored:
            continue
        score, slug = scored[0]
        corroborated = playlists[slug]["first_aired"] == date.isoformat()
        if score < (floor if corroborated else replay_floor):
            continue
        runner = scored[1][0] if len(scored) > 1 else 0.0
        bindings[date] = {
            "slug": slug, "score": round(score, 3), "corroborated": corroborated,
            # Two different playlists scoring alike means the match is not distinctive
            # enough to trust; that is a human's call, not a silent max().
            "ambiguous": score - runner < 0.15,
            "runner_up": [scored[1][1], round(runner, 3)] if len(scored) > 1 else None,
        }
    return bindings


def parse_table(table):
    """Rows of a playlist table, or None if it has no recognisable header.

    Episode 052 has no header row at all -- its first row is already a spin. A two-column
    table is unambiguous enough to read positionally (artist, then song, matching every
    other table on the site), so that one case is handled rather than dropped.
    """
    rows = table.find_all("tr")
    if not rows:
        return None
    header = [ALIASES.get(txt(c).lower(), "") for c in rows[0].find_all(["th", "td"])]
    if "artist" in header and "song" in header:
        body_rows = rows[1:]
    elif len(header) == 2:
        header, body_rows = ["artist", "song"], rows
    else:
        return None
    colmap = {}
    for i, name in enumerate(header):
        if name and name not in colmap:
            colmap[name] = i

    out = []
    for tr in body_rows:
        cells = [txt(c) for c in tr.find_all(["th", "td"])]
        if not any(cells):
            continue
        rec = {k: (cells[i] if i < len(cells) else "") for k, i in colmap.items()}
        artist, song = rec.get("artist", ""), rec.get("song", "")
        if not artist or not song:
            continue
        if HOUR_RE.match(song) or BREAK_RE.match(song) or BREAK_RE.match(artist):
            continue
        # Section dividers repeat the same text across artist and song; no real spin does.
        if artist.strip().lower() == song.strip().lower():
            continue
        out.append(rec)
    return out


def main():
    urls = {}
    if SITEMAP.exists():
        for u in re.findall(r"<loc>([^<]+)</loc>", SITEMAP.read_text(encoding="utf-8")):
            urls[u.rstrip("/").split("/")[-1]] = u

    spin_playlists = load_spin_playlists()
    OUT_CSV_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_CSV_DIR.glob("*.csv"):
        old.unlink()

    playlists, skipped = {}, []
    for f in sorted(HTML_DIR.glob("post-*.html")):
        slug = f.name[len("post-"):-len(".html")]
        soup = BeautifulSoup(f.read_bytes(), "lxml")
        body = soup.select_one(".entry-content")
        if body is None:
            continue
        for bad in body.find_all(["script", "style"]):
            bad.decompose()

        tracks = []
        for t in body.find_all("table"):
            tracks.extend(parse_table(t) or [])
        if not tracks:
            # Roughly half the posts never used a table and list the set as text.
            lines = [ln.strip() for ln in body.get_text("\n", strip=True).split("\n")
                     if ln.strip()]
            tracks = parse_text_playlist(lines)
        if not tracks:
            skipped.append(slug)
            continue

        claimed, how = page_date(soup, body)
        playlists[slug] = {
            "slug": slug, "url": urls.get(slug, ""),
            "first_aired": claimed.isoformat() if claimed else "",
            "date_source": how,
            "tracks": [{"position": i, **{c: t.get(c, "") for c in
                        ("artist", "song", "time", "album", "label", "notes")}}
                       for i, t in enumerate(tracks, 1)],
        }

    duplicates = dedupe(playlists)
    bindings = bind_broadcasts(playlists, spin_playlists)
    for slug, p in playlists.items():
        p["broadcasts"] = sorted(d.isoformat() for d, b in bindings.items()
                                 if b["slug"] == slug)

    for slug, p in sorted(playlists.items()):
        stem = p["first_aired"] or (p["broadcasts"][0] if p["broadcasts"] else "undated")
        with open(OUT_CSV_DIR / f"{stem}-{slug}.csv", "w", encoding="utf-8",
                  newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=["position", "artist", "song", "time",
                                               "album", "label", "notes"])
            w.writeheader()
            w.writerows(p["tracks"])

    OUT_JSON.write_text(json.dumps(
        {"playlists": playlists,
         "broadcasts": {d.isoformat(): b for d, b in sorted(bindings.items())}},
        indent=1, ensure_ascii=False), encoding="utf-8")

    print(f"{'broadcast':11} {'score':>5} {'amb':>4} {'trk':>4}  published playlist")
    for d in sorted(bindings):
        b = bindings[d]
        p = playlists[b["slug"]]
        tag = "YES" if b["ambiguous"] else ""
        print(f"{d} {b['score']:>5.2f} {tag:>4} {len(p['tracks']):>4}  {b['slug']}"
              f"{'  (replay)' if p['first_aired'] and p['first_aired'] != d.isoformat() else ''}")

    reused = {s: p["broadcasts"] for s, p in playlists.items() if len(p["broadcasts"]) > 1}
    never = [s for s, p in playlists.items() if not p["broadcasts"]]
    amb = [d for d, b in bindings.items() if b["ambiguous"]]
    print(f"\n{len(playlists)} published playlists, "
          f"{sum(len(p['tracks']) for p in playlists.values())} tracks")
    print(f"{len(bindings)} of {len(spin_playlists)} Spinitron broadcasts matched a playlist")
    if reused:
        print(f"\nplaylists aired more than once -- {len(reused)}:")
        for s, ds in sorted(reused.items()):
            print(f"  {s:50} {', '.join(ds)}")
    if never:
        print(f"\nplaylists with no matching broadcast -- {len(never)}:")
        for s in sorted(never):
            print(f"  {s:50} first aired {playlists[s]['first_aired'] or '?'}")
    if amb:
        print(f"\nambiguous bindings (runner-up within 0.15) -- {len(amb)}:")
        for d in sorted(amb):
            b = bindings[d]
            print(f"  {d}  {b['slug']} {b['score']:.2f}  vs  "
                  f"{b['runner_up'][0]} {b['runner_up'][1]:.2f}")
    if duplicates:
        print(f"\nduplicate pages folded into the canonical playlist -- {len(duplicates)}:")
        for dup, keep in sorted(duplicates.items()):
            print(f"  {dup:50} -> {keep}")
    print(f"\nposts with no playlist table: {len(skipped)}")
    print(f"CSVs -> {OUT_CSV_DIR}")


if __name__ == "__main__":
    main()
