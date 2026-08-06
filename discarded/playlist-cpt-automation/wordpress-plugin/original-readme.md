# CZ Playlists (WordPress plugin — discarded)

> Historical prototype only. Do not install; see the archive parent README.

Registers the `playlist` custom post type, `host` taxonomy, and the custom
fields used to publish Convergence Zone episode pages automatically from
[`shows/convergence-zone/playlists/cache/`](../../../playlists/cache/). See
[`tools/python/czpublish/`](../../../../tools/python/czpublish/) for the
script that populates these posts.

## Why a plugin, not theme code

Twenty Twenty-Five (or any theme) can change or get replaced; a plugin keeps
the `playlist` post type, its taxonomy, and its custom fields intact
regardless of theme. The presentation half of this (the single-post
template) lives in the paired child theme,
[`../../wp-theme/cz-playlists-child/`](../../wp-theme/cz-playlists-child/).

## Install

1. Copy `cz-playlists/` into `wp-content/plugins/` on the site and activate
   it under Plugins, **or** zip the folder and upload via Plugins → Add New →
   Upload Plugin.
2. Install and activate [Secure Custom
   Fields](https://wordpress.org/plugins/secure-custom-fields/) (the
   WordPress-core-maintained ACF successor) or ACF PRO/Free. On activation it
   will pick up `acf-json/group_playlist.json` automatically (the plugin adds
   the necessary `acf/settings/load_json` / `save_json` filters) and show a
   "Playlist Details" field group.
3. Activate the **CZ Playlists Child** theme (parent: Twenty Twenty-Five) to
   get the `single-playlist.html` template — see its README.

## Fields registered

| Meta key | Type | Source (playlist cache) |
|---|---|---|
| `cz_air_datetime` | string | `Broadcast.air_datetime` (informational — `post_date` drives display) |
| `cz_episode_number` | integer | `Broadcast.episode_number` |
| `cz_description` | string | `Broadcast.description`, only when `description_status == "approved"` |
| `cz_description_status` | string | `Broadcast.description_status` |
| `cz_mixcloud_url` | string (URL) | `Broadcast.mixcloud_url` |
| `cz_spinitron_playlist_url` | string (URL) | built from `Broadcast.spinitron_playlist_ids[0]` |
| `cz_hosts` (repeater, SCF-only) | array | `Broadcast.participants[]` |
| `cz_tracklist` (repeater, SCF-only) | array | `Broadcast.spins[]` |

The `host` taxonomy is also assigned by the publisher script, one term per
`participants[].name`.

## What's NOT stored as a bindable field

The rendered **tracklist table** and the **Mixcloud embed** are written
directly into `post_content` by the publisher script, not read from custom
fields at display time. WordPress's core Block Bindings API (as of the
6.5–6.7 line) only supports binding the `content` attribute of
paragraph/heading blocks, the `url`/`text` of a button, and the `url`/`alt`/
`id` of an image — there's no bindable target for a table's rows or an embed
block's URL. Storing the tracklist in `cz_tracklist` (SCF repeater) anyway
gives you a queryable copy for future features (e.g. "search by artist")
without it being the source of the rendered table.
