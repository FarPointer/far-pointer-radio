# convergencezone.fm playlists

Playlists published on [convergencezone.fm](https://convergencezone.fm), scraped from the
live WordPress site and flattened to CSV. One file per published playlist, named
`YYYY-MM-DD-<post-slug>.csv` where the date is the episode's **first** broadcast, so each
row traces back to the page it came from.

Columns: `position`, `artist`, `song`, `time`, `album`, `label`, `notes`. `time` is an
offset from the start of the show — except in the block-format posts, where the site
printed clock times. Break and "First Hour" divider rows are dropped; everything else is
verbatim.

**47 playlists, 1,062 tracks**, spanning Episode 001 (2023-03-14) through the Summer
Solstice special (2024-06-18). They match **64 of the 164** Spinitron broadcasts.

## Published formats

The site never settled on one layout, and half the playlists are not tables at all. The
scraper handles four shapes:

| Format | Example | Posts |
|---|---|---|
| HTML table | header row of `Artist`/`Song`/`Time`/`Album` | 25 |
| Dash lines | `Destroyer – Savage Night at the Opera – 00:00` | 18 |
| Slash lines | `Patricia Wolf / Pacific Coast Highway / See-Through / 6:00 / 2022` | 3 |
| Five-line blocks | `10:30 PM` / artist / `"song" from` / album / year | 1 |

Table layouts vary further — `Track` vs `Song`, `Artist Name` vs `Artist`, and Episode 052
has no header row at all. Dash lines appear with and without a trailing time, and
sometimes with a trailing album.

## Scope and caveats

All 66 posts in the site's sitemap were fetched. 47 carry a set list; 17 are prose only
(promo blurbs, two interview posts, and two year-end recommendation articles); the
remaining 2 are `replay-convergence-zone-004` and `replay-convergence-zone-006`, which
republish an earlier post's table verbatim and are folded into the original.

Five playlists match no Spinitron broadcast: 003, 009, 010 and 011 aired before Spinitron
logging began on 2023-05-30 and were never replayed, and the 2024 Summer Solstice special
was a six-hour Thursday broadcast with no corresponding Tuesday playlist.

Fifteen playlists match more than one broadcast — the show is replayed from automation
during vacations and hiatus. Episode 021 aired four times.

**These are not an independent record.** Where a matching OneNote note exists in
`../farpointer-onenote/`, the track sets are identical — same document, published. The
site version is the better text (real accents, typos fixed, scratch artifacts like
`MIC BREAK brass clouds` removed), which is why the audit prefers it, but it cannot
corroborate that a track actually aired. It is not uniformly cleaner either: the site
spells `Erwillian` where the note has the correct `Erwilian`.

Regenerate with `tools/python/czaudit/scrape_site.py`; see that directory's README.
