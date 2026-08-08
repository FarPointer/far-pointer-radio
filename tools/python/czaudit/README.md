# czaudit

Reconciles Convergence Zone set lists against what Spinitron actually logged, and writes
the audit workbook at `shows/convergence-zone/playlists/analysis/cz-playlist-spinitron-audit.xlsx`.

## Pipeline

Run in order — each step feeds the next.

| Step | Script | Reads | Writes |
|---|---|---|---|
| 1 | `extract.py` | `sources/farpointer-onenote/*.md` | `onenote_episodes.json` |
| 2 | `scrape_site.py` | `site_html/*.html` + the Spinitron CSV | `sources/convergencezone.fm/*.csv`, `site_episodes.json` |
| 3 | `build_audit.py` | both JSONs + the Spinitron CSV | the audit workbook |

`matching.py` holds the normalisation and similarity helpers the other two share.
`textlist.py` parses the posts that published their set list as text instead of a table.

`dump_tables.py` is an inspection aid, not part of the pipeline: it prints the header and
first rows of every table in a OneNote export so a new file's column map can be
established by eye before it is added to `extract.SPECS`.

```sh
uv run python dump_tables.py                      # every OneNote file
uv run python dump_tables.py <file.md> --rows 5   # one file, more rows
```

"the Spinitron CSV" means `Spins-search-results-12-8-19-8-7-26-for-KSER.csv` — the same
export `czcache` builds the cache from, so the audit and the cache are never reconciling
different files. Earlier exports are kept as archives and are no longer read; when a
newer one lands, change the path in `build_audit.py`, `scrape_site.py`, and
`czcache/paths.py` together.

The JSON files are intermediate and land beside the scripts; only the CSVs and the
workbook belong in the repo, so `site_html/`, the JSONs, and the scripts' own copy of the
workbook are gitignored. Copy the finished workbook to
`shows/convergence-zone/playlists/analysis/` by hand.

Step 2 is optional. Its input HTML is not kept in the repo, so a fresh clone can run
steps 1 and 3 alone — every episode then falls back to its OneNote note, and the eight
published playlists stay as archived in `sources/convergencezone.fm/`.

```sh
# dependencies come from pyproject.toml; uv run syncs them
uv run python extract.py && uv run python build_audit.py   # or: make audit
```

## Refreshing the site scrape

`scrape_site.py` parses HTML already on disk rather than fetching, so the download is a
separate, deliberate step. There is no page list to maintain — it reads the sitemap and
parses every post it finds:

```sh
curl -A "far-pointer-radio playlist archiver" \
  https://convergencezone.fm/sitemap-post-type-post.xml -o site_html/sitemap-posts.xml
# then, for each <loc> in that file, with a short pause between requests:
curl -A "far-pointer-radio playlist archiver" <url> -o site_html/post-<slug>.html
```

The site archive runs from Episode 001 (2023-03-14) to Episode 059 (2024-06-22) and stops
there.

## Why the code looks the way it does

**Per-file column maps in `extract.py`.** The OneNote tables share no schema. Column
order varies — `Episode.065` lists Album *before* Song — and several tables have no
header row at all, because the exporter promoted the first data row into `<th>`
(`th_is_data`). A positional guess would silently transpose whole episodes, so every
file is mapped by hand and new files need a new entry.

**Header-driven mapping in `scrape_site.py`.** The published pages *do* have real
headers, so columns are matched by name through an alias table (`Song`/`Title`,
`Time`/`Start Time`) rather than position. Episode 052 is the one exception — its table
has no header row at all, and a two-column table is read positionally.

**`textlist.py` exists because tables are the minority.** Only 25 of the 47 published
playlists are HTML tables. The rest are lines inside a paragraph, broken by `<br>`, in
three styles that changed over time: `Artist – Song – 00:00`, `Artist / Song / Release /
Duration / Released`, and five-line blocks of `10:30 PM` / artist / `"song" from` / album
/ year. The hard part is not splitting the lines but telling a set list from prose —
every post opens with sentences that also contain dashes. So a style only counts when it
repeats: the parser takes the longest consecutive run of lines in one style, requires at
least five, and rejects rows whose "artist" is sentence-shaped (too long, too many words,
trailing comma). Without those guards, opening paragraphs parse as tracks.

Two year-end articles (`top-music-of-2023`, `ten-picks-for-bandcamp-friday`) list albums
in prose and are deliberately *not* treated as playlists — they are recommendations, not
as-aired logs.

**Broadcasts, not episodes, in `scrape_site.py`.** The show is replayed from automation
during vacations and hiatus, and every replay is logged in Spinitron as its own playlist.
So the binding runs one reference *per broadcast*: each Spinitron playlist is matched to
the published playlist whose songs it overlaps most. Binding by date instead would be
wrong twice over — a replay post states the original broadcast's date, and one playlist
legitimately covers several airings (episode 021 aired four times).

Dates are still used as corroboration, setting how strong the content match must be. If
the page claims the date being bound, a weak score just means the show drifted from its
own set list, so 0.30 suffices. If it does not, only a near-complete reproduction is
credible as a replay, so the bar is 0.60 — distinct consecutive weeks overlap around
0.00–0.08 while genuine replays run 0.6–0.96, which leaves a wide gap to cut in.

**`dedupe` in `scrape_site.py`.** The site publishes `convergence-zone-004-playlist` and
`replay-convergence-zone-004` with identical tables. Left separate they tie on every
binding and flag each other as ambiguous, so identical playlists collapse to the
canonical page.

**Artist token containment in `build_audit.py`.** Spinitron often logs only the lead
artist where the set list names everyone. Plain string similarity collapses on those —
`Sin Fang` vs `Sin Fang, Kjartan Holm, Fischersund` scores about 0.4 — so `artist_score`
treats one name's words being a subset of the other's as a near-certain match. Without
it the audit invents duplicate spins.

## What the numbers mean

`Coverage` is the share of Spinitron spins the reference explains. `Reference logged` is
the share of reference tracks that reached Spinitron. They answer different questions,
and **high coverage with low reference-logged is the actionable case**: the set list
tracks the show closely and Spinitron is the one missing entries.

Low coverage means the note was abandoned mid-write, not that Spinitron is wrong — which
is why the `Spins not in notes` sheet is explicitly not a removal list.

## Caveat that governs everything

The published playlists and the OneNote notes are the **same document**: track sets are
identical across every episode where both exist. The site text is cleaner, so the audit
prefers it, but it is not independent corroboration that a track aired. Both are prep
written before broadcast.

Replay rows inherit a second layer of that problem. A replay airs the recording of the
original show, so what it truly contains is what that episode *actually* played — which
may already differ from the published plan being compared against.
