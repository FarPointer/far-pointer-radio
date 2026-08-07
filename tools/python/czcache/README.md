# czcache

Builds the canonical playlist cache at `shows/convergence-zone/playlists/cache/` from
every upstream source, following the schema in `playlists/schema.ts`.

`czaudit` reconciles sources and reports to a human; `czcache` owns the datastore. It
imports `czaudit.matching` and `czaudit.build_audit.match_episode` rather than
reimplementing them, so the two tools can never disagree about what matched what.

## Running

One command, no arguments, from anywhere:

```sh
uv run --with openpyxl --with beautifulsoup4 --with lxml --with pyyaml python build.py
uv run --with openpyxl --with beautifulsoup4 --with lxml --with pyyaml python verify.py
uv run --with openpyxl python enrich_missing_spins.py
```

The third command backfills import-ready `Release` (year), `Local`, `Duration`, and
`Label` columns in `shows/convergence-zone/playlists/analysis/cz-missing-spins.xlsx`
and refreshes `cz-removal-candidates.csv` from the `Remove or replace` sheet.

Rebuilds are idempotent — a run that changes nothing produces a zero-line diff, which is
what makes the cache reviewable in a pull request. Every loader also runs standalone
(`python load_workbooks.py`) and prints what it found, which is the fastest way to see
what a source actually contains.

## Modules

| Module | Purpose |
|---|---|
| `paths.py` | Filesystem locations and the persona/host constants |
| `model.py` | Broadcast and Spin constructors — the one place field order and the null convention are enforced |
| `fetch_spinitron_playlists.py` | Snapshots playlist IDs and URLs from the public Convergence Zone show-history page; no API key required |
| `load_spinitron.py` | The Spinitron export → broadcast skeletons and logged spins; merges cross-persona duplicate spins |
| `repeats.py` | Archive-wide overlap clustering → `first_broadcast_id` |
| `load_workbooks.py` | MichaelG's 28 `.xlsx` workbooks across five header layouts |
| `load_setlists.py` | convergencezone.fm CSVs and OneNote tables, bound to broadcasts by content |
| `load_prose.py` | OneNote prose → candidate broadcast descriptions |
| `locality.py` | Resolves `local` and records *why* (artist, label, or DJ flag) |
| `merge.py` | The three per-class merge strategies, plus host attribution |
| `emit.py` | Writes `cache/` and `reports/` |
| `build.py` | Entry point |
| `verify.py` | Asserts the invariants the build guarantees; exits non-zero on failure |

## The three classes

Each broadcast has exactly one canonical source. Class A takes precedence over B.

| Class | Canonical source | Broadcasts |
|---|---|---|
| A | MichaelG's workbook — plus three repeats of one, which have no workbook of their own | 31 |
| B | A set list merged with Spinitron; neither is authoritative | 70 |
| C | Spinitron alone | 63 |

## Two things that are easy to get wrong

**`dj_ids` is not host attribution.** Two Spinitron personas display the identical name
"Jim Causey" — 173567 is Jim's original account, 174269 a second one — and 26 of
MichaelG's 28 episodes were logged under Jim's original account. Hosts come from workbook
presence and `overrides/participants.yaml`. See `reports/attribution.md`.

**Repeat detection runs before classification, not after.** Three of MichaelG's episodes
were re-aired on weeks with no workbook; without the repeat pass they look like ordinary
Spinitron-only broadcasts and lose his attribution, artist origins, and notes. Repeats
also form chains — episode 021 aired four times — so clustering resolves each to the
*original*, never to the previous airing.

## Overrides

Checked-in human decisions in `overrides/`. All four are optional and start empty; the
build always produces a complete cache without them.

| File | Decides |
|---|---|
| `descriptions.yaml` | Approved description text, or `skip`. Nothing reaches `description_status: "approved"` any other way. |
| `participants.yaml` | Host attribution where the workbook rule is wrong or a show was co-hosted |
| `repeats.yaml` | Force or suppress a repeat pairing the 0.60 threshold got wrong |
| `spins.yaml` | Merge a same-persona duplicate the build deliberately left alone |

## Reports

Regenerated every build into `reports/` (gitignored — they are derived, and they change
whenever a source does). Never blocking: the cache is always complete.

| Report | Contents |
|---|---|
| `build-summary.md` | Counts per class, evidence, locality, descriptions |
| `discrepancies.md` | Merged and flagged duplicates, set-list vs Spinitron conflicts, weak workbook matches |
| `repeats.md` | Clusters, chosen originals, and every pair scoring 0.40–0.95 |
| `attribution.md` | Persona × workbook cross-tab and the broadcasts that break the alternation |
| `unmatched.md` | Planned-only, workbook-only, and Spinitron-only tracks |
| `descriptions-review.md` | Each proposed description *and the text that was rejected* |

## Source of truth for spins

Read `Spins-search-results-12-5-19-8-4-26-for-KSER.csv`, not the older
`Spinssearchresults84208326forKSER.csv`. Both cover the same 3,282 spins, but only the
newer one has `DJ ID`, `Playlist Date-time`, and `Playlist Duration`. The loader asserts
its expected columns, so a re-export in the old format fails loudly.

## Spinitron playlist IDs

The spins export has no Playlist ID column. Refresh the checked-in public-index snapshot
before a cache build when new broadcasts have aired:

```sh
uv run --with beautifulsoup4 --with lxml python fetch_spinitron_playlists.py
```

The script follows pagination from
`https://spinitron.com/KSER/show/260646/Convergence-Zone` and writes
`shows/convergence-zone/playlists/sources/spinitron/convergence-zone-playlists.json`.
`load_spinitron.py` joins it to the spins export by the full playlist start datetime and
fails loudly if any cached broadcast is missing an ID. Six persona-switch broadcasts
correctly carry two IDs.

If Spinitron changes the public page, the official fallback is its v2 API. Log in and
open **Admin → Automation & API** to obtain the station API key, then page through:

```text
GET https://spinitron.com/api/playlists?show_id=260646&count=200&page=1
```

The only required fields are playlist `id` and `start`. Keep the key outside the repo.
If an API key is unavailable and a manual export is necessary, export/search
**playlists**, not spins, and retain a playlist URL (whose `/pl/NUMBER/` segment is the
ID) plus the playlist start datetime. Another spin-search export cannot solve this: its
available columns do not contain Playlist ID.

## Publication links

`shows/convergence-zone/playlists/publication-links.json` is the durable bridge to
external publication state. It is keyed by air date:

```json
{
  "2026-07-28": {
    "wordpress_post_id": 123,
    "webpage_url": "https://convergencezone.fm/2026/07/convergence-zone-2026-07-28/",
    "mixcloud_url": null
  }
}
```

`webpage_url` and `mixcloud_url` flow into the cache. `wordpress_post_id` is retained for
the publishing script's idempotent updates but is not part of `schema.ts`. Missing or
null Mixcloud URLs are expected: the WordPress page simply omits the embed until a
recording becomes available. Adding the URL later, rebuilding the cache, and updating
the post backfills the embed without changing the post identity or URL.
