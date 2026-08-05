# Convergence Zone Playlist Automation — Discarded Session Summary

> Historical context only. Superseded by
> `shows/convergence-zone/docs/playlist-publishing-plan.md`.

**Date:** August 5, 2026
**Purpose:** Recap of this session's discussion and implementation, so the
conversation can continue in another model/session with full context.

---

## 1. The ask

Automate creation of new Convergence Zone episode pages on
[convergencezone.fm](https://convergencezone.fm) (WordPress, Twenty
Twenty-Five theme) from the playlist cache at
`shows/convergence-zone/playlists/cache/`. Each page needs:

- Host(s) for the week
- Episode description
- Songs played (tracklist)
- A Mixcloud embed
- A link to the Spinitron playlist

## 2. Key context gathered

- **The playlist cache** (`shows/convergence-zone/playlists/cache/broadcasts/YYYY-MM-DD.json`,
  schema at `playlists/schema.ts`) is the canonical, machine-built source of
  truth — one JSON file per broadcast, with `participants[]` (hosts),
  `description` / `description_status` ("approved" vs "proposed" — **only
  "approved" text should ever be published**), `mixcloud_url` (often null
  until the episode is archived later), `spinitron_playlist_ids` (best-effort,
  may be empty), and `spins[]` (artist/song/release/`publish_note` — never
  `song_note`, which may hold internal-only remarks).
- **A WordPress Application Password already exists**, saved at
  `shows/convergence-zone/playlists/.wordpress-app-password.local.txt`
  (gitignored, username `playlist-scripts`) — strong signal the intended path
  is REST-API-driven publishing, not a manual CMS workflow.
- **`docs/website-rebuild-brief.md`** describes a *possible* full rebuild off
  WordPress (Jekyll/Astro + Decap CMS + Cloudflare Pages) — but the user
  clarified partway through this session: **a full rebuild may never happen;
  plan to stay on WordPress long-term.** This changed the recommendation
  significantly (see below).
- Spinitron playlist URLs follow the pattern
  `https://spinitron.com/{station}/pl/{playlist_id}` (confirmed from
  `tools/python/czarchive/src/czarchive/spinitron.py`); station is `KSER`.

## 3. Recommendation arc (why the design looks the way it does)

1. **First pass** (rebuild still seemed likely): recommended *not* building a
   custom post type or custom fields — just a synced block pattern with
   plain Gutenberg blocks, to avoid throwaway WordPress-specific
   infrastructure.
2. **Revised** (user said WP is likely permanent): recommended investing in
   real structure instead — a custom post type, taxonomy, and structured
   custom fields — since the data model will need to last and be
   hand-editable for years, not just bridge to a rebuild.
3. **Implemented** that revised design (see below), verified end-to-end
   against real cache data.

## 4. What was built

### WordPress plugin — `shows/convergence-zone/website/wp-plugin/cz-playlists/`
- Registers the `playlist` custom post type and `host` taxonomy (kept as a
  **plugin**, not theme code, so it survives theme changes/updates).
- Registers REST-exposed post meta: `cz_air_datetime`, `cz_episode_number`,
  `cz_description`, `cz_description_status`, `cz_mixcloud_url`,
  `cz_spinitron_playlist_url`.
- `acf-json/group_playlist.json` — a Secure Custom Fields (ACF-successor)
  field group for the admin editing UI, including `cz_hosts` and
  `cz_tracklist` repeaters (kept for querying/manual correction — **not**
  the source of the rendered tracklist table, see below). The plugin adds
  `acf/settings/load_json` / `save_json` filters so this JSON round-trips
  through git.
- `README.md` documents install steps (copy into `wp-content/plugins/`,
  install Secure Custom Fields) and the full field mapping table.

### Twenty Twenty-Five child theme — `shows/convergence-zone/website/wp-theme/cz-playlists-child/`
- Child theme (`Template: twentytwentyfive`) so template customization
  survives parent theme updates.
- `templates/single-playlist.html`: core blocks (`post-title`, `post-date`,
  `post-terms` for `host`), a paragraph **bound via the Block Bindings API**
  to `cz_description`, a `core/post-content` block (renders the tracklist
  table + Mixcloud embed — see caveat below), and a button **bound** via its
  `url` attribute to `cz_spinitron_playlist_url`.
- **Important technical caveat, documented in both READMEs:** WordPress's
  core Block Bindings API (as of the 6.5–6.7 line) only supports binding
  paragraph/heading `content`, button `url`/`text`, and image
  `url`/`alt`/`id` — there is **no bindable target for a table's rows or an
  embed block's URL**. That's why the tracklist and Mixcloud embed are
  written directly into `post_content` by the publisher script instead of
  being template-bound, even though they're also stored as structured SCF
  repeater/meta fields for future queryability.

### Publisher CLI — `tools/python/czpublish/`
- `uv`-managed package mirroring `tools/python/czarchive`'s structure
  (`pyproject.toml`, `src/czpublish/`, Click CLI).
- `paths.py` / `config.py`: locates the cache, loads `~/.czpublish.toml`
  (site URL, station, Spinitron fallback URL — created with defaults on
  first run), and parses the existing `.wordpress-app-password.local.txt`.
- `render.py`: pure functions turning a cached `Broadcast` dict into WP
  payload pieces — title, host list, gated description (returns `None`
  unless `description_status == "approved"`), tracklist table block markup
  (HTML-escaped), Mixcloud embed block markup, Spinitron URL (with fallback
  when `spinitron_playlist_ids` is empty).
- `wordpress.py`: minimal REST client — Basic Auth via the Application
  Password, get-or-create for `host` taxonomy terms, and
  find-by-`cz_air_datetime`-then-create-or-update for idempotent publishing.
- `cli.py`: `czpublish publish YYYY-MM-DD [--publish] [--dry-run]` and
  `czpublish publish-all [--publish] [--dry-run]`. **Drafts by default** —
  `--publish` is opt-in, so a first run's output can be reviewed in wp-admin
  before going live.
- **Two-pass publishing by design:** re-running `publish` for the same date
  updates the same post (matched on `cz_air_datetime`) rather than
  duplicating it. This is meant to be run once near air time (no Mixcloud
  embed yet, since `czarchive` hasn't uploaded it) and run again later once
  `czarchive` → `czcache` populate `mixcloud_url` in the cache.

## 5. Verification performed this session

- `uv sync` succeeded in `tools/python/czpublish/`.
- `czpublish publish-all --dry-run` ran against **all 164 real cached
  broadcasts** without error, correctly rendering titles, host lists,
  tracklist tables (HTML-escaped), and the Spinitron fallback URL (no
  broadcast currently has an approved description or Mixcloud URL, since
  the cache's overrides are all still empty).
- Synthetic data was used to exercise the two paths not yet present in real
  data: an `"approved"` description (confirmed it renders; confirmed a
  `"proposed"` one does *not*) and a populated `mixcloud_url` (confirmed the
  `core/embed` block renders correctly, with a real Spinitron
  `playlist_id` producing the expected URL).
- Found and fixed a real bug during testing: the `publish` Click command and
  its `--publish` boolean flag shared a name, causing `ctx.invoke()` in
  `publish-all` to call a bool instead of the command. Fixed by renaming the
  flag's Python parameter to `do_publish` (CLI flag name unchanged).
- Confirmed the ACF field-group JSON parses as valid JSON.
- Confirmed the Gutenberg block comments in `single-playlist.html` are
  balanced (every non-self-closing `wp:` block has a matching `/wp:` close).
- Confirmed `.venv/` artifacts are properly gitignored (only the empty
  directory shows as untracked).

## 6. What's NOT done yet / next steps

- **Nothing has been installed on the live site.** The plugin and child
  theme exist only in this repo; they need to be uploaded to
  convergencezone.fm (via Plugins/Themes → Add New → Upload, or direct file
  copy) and activated, and Secure Custom Fields (or ACF) needs to be
  installed for the admin editing UI.
- No actual WordPress posts have been created or updated — only `--dry-run`
  was exercised, deliberately, to avoid touching the live site without
  explicit sign-off.
- `~/.czpublish.toml` was created locally during testing with default values
  (`site_url = "https://convergencezone.fm"`, `station = "KSER"`) — worth
  reviewing/confirming before a real run.
- Possible follow-ups if wanted later: a scheduled/cron invocation of
  `czpublish publish-all`; wiring `czarchive`'s Mixcloud upload step to
  trigger a `czcache` rebuild + `czpublish` re-publish automatically (closing
  the two-pass loop without a manual second run); deciding whether to also
  surface `episode_number`/host archive pages more prominently in nav.

## 7. File map

```
shows/convergence-zone/website/
├── README.md                              (new)
├── wp-plugin/cz-playlists/
│   ├── cz-playlists.php                   (new — CPT, taxonomy, meta, ACF-JSON filters)
│   ├── README.md                          (new)
│   └── acf-json/group_playlist.json       (new — SCF/ACF field group)
└── wp-theme/cz-playlists-child/
    ├── style.css                          (new — child theme header)
    ├── functions.php                      (new — empty, documented)
    ├── README.md                          (new)
    └── templates/single-playlist.html     (new — block-bound template)

tools/python/czpublish/
├── pyproject.toml                         (new)
├── README.md                              (new)
├── uv.lock                                (new, generated)
└── src/czpublish/
    ├── __init__.py
    ├── paths.py
    ├── config.py
    ├── render.py
    ├── wordpress.py
    └── cli.py

Updated (existing files):
├── tools/python/README.md                 (added czpublish row)
└── shows/convergence-zone/README.md       (added website/wp-plugin, website/wp-theme rows)
```

---

## 8. Follow-up: simplified publishing and external-link identity

The later architecture review recommends **not deploying** the custom post
type/plugin/child-theme stack. The preferred direction is ordinary WordPress
posts in the existing `Show Playlists` category, a core-block Site Editor
pattern, and a narrow Bash/`jq` publisher. See
`docs/playlist-publishing-options.md`.

External identities now have a concrete cache path:

- The spin-search CSV cannot supply Spinitron Playlist IDs because it has no
  ID column.
- The public Convergence Zone show-history page does supply them. A new
  `czcache/fetch_spinitron_playlists.py` snapshots all paginated playlist
  links into
  `playlists/sources/spinitron/convergence-zone-playlists.json`.
- All 164 cached broadcasts match that index by full start datetime. There
  are 170 IDs total: 158 broadcasts have one and six persona-switch
  broadcasts have two.
- `playlists/publication-links.json` now holds WordPress post identity/URL and
  optional Mixcloud URL by broadcast date. `webpage_url` and `mixcloud_url`
  flow into the generated cache.
- A missing Mixcloud recording is normal: publish without the embed, then add
  the URL later, rebuild the cache, and update the same WordPress post.
- After creating or updating a WordPress post, the eventual publisher should
  record the REST response's `id` and `link` in `publication-links.json`.
