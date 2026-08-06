# czpublish (discarded)

> Historical prototype only. Do not install or run; see the archive parent README.

Publishes Convergence Zone playlist pages to WordPress, reading directly from
the canonical cache at
[`shows/convergence-zone/playlists/cache/broadcasts/`](../../../shows/convergence-zone/playlists/cache/broadcasts/)
(built by [`czcache`](../czcache/)). Requires the companion
[CZ Playlists plugin](../../../shows/convergence-zone/website/wp-plugin/cz-playlists/)
and its child theme to be installed on the site.

## What it publishes

| WordPress field | Source |
|---|---|
| Title | `Broadcast.show_name` + episode number or air date |
| `host` taxonomy | `Broadcast.participants[].name` |
| `cz_description` meta | `Broadcast.description`, only if `description_status == "approved"` |
| Tracklist table (in `post_content`) | `Broadcast.spins[]` — artist, song, release, `publish_note` |
| Mixcloud embed (in `post_content`) | `Broadcast.mixcloud_url`, if present |
| `cz_spinitron_playlist_url` meta | built from `Broadcast.spinitron_playlist_ids[0]`, or a station-history fallback if empty |

## Setup

```bash
cd tools/python/czpublish
uv sync
```

Requires:
- `~/.czpublish.toml` — created with defaults on first run; review `site_url`/`station`.
- `shows/convergence-zone/playlists/.wordpress-app-password.local.txt` — a
  WordPress Application Password (Users → Profile → Application Passwords),
  in the format:

  ```
  username: playlist-scripts
  application-password: xxxx xxxx xxxx xxxx xxxx xxxx
  ```

  This file is gitignored — never commit it.

## Usage

```bash
# Preview the exact payload for one broadcast without touching the site:
uv run czpublish publish 2026-07-28 --dry-run

# Create/update the draft post for one broadcast:
uv run czpublish publish 2026-07-28

# ...and actually publish it (default is draft, for review first):
uv run czpublish publish 2026-07-28 --publish

# Every cached broadcast:
uv run czpublish publish-all --dry-run
```

Re-running `publish` for a date that already has a post updates it in place
(matched by the `cz_air_datetime` meta value) rather than creating a
duplicate. That's what makes **two-pass publishing** work: run once near air
time (no Mixcloud embed yet), run again after `czarchive` has uploaded the
episode to Mixcloud and `czcache` has rebuilt the cache with `mixcloud_url`
populated — the second run adds the embed to the same post.

## Why draft by default

`--publish` is opt-in. The first run of a new pipeline like this is exactly
when a rendering bug is most likely to show up (bad HTML escaping, a
description that shouldn't have gone out yet, etc.) — reviewing a draft in
wp-admin before it goes live costs one click and catches that class of
mistake before it doesn't matter.
