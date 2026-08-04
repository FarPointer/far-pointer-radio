# Playlist Sources

Raw playlist material as it came out of each upstream system. Nothing here is
hand-corrected — these are the originals that normalized playlists get derived from,
kept so any downstream file can be traced back to where it came from.

Files keep the names their originating system gave them, so the usual kebab-case and
`YYYY-MM-DD-episode-title.csv` conventions do not apply inside this directory.

## Directory Structure

| Directory | Contents |
|---|---|
| `farpointer-onenote/` | Markdown exports of the OneNote playlist notebooks, 2023–2025 — show prep notes, set lists, and on-air rundowns |
| `michaelg/` | MichaelG's per-episode playlist workbooks (`.xlsx`), 2025-04-29 through 2026-06-23 |
| `spinitron/` | Spinitron exports — logged spins as actually played |
| `convergencezone.fm/` | Playlist material recovered from the WordPress site (empty for now) |

## Notes

- The OneNote exports carry YAML frontmatter (`title`, `created`, `updated`) from the
  export tool, and mix show-prep prose with the set list itself.
- MichaelG's workbooks are per-episode and multi-sheet; date in the filename is the air date.
- `spinitron/cz-038.tsv` is a hand-assembled tab-separated set list, not a Spinitron export.
  It predates the CSV exports and is CRLF-encoded.
