# Convergence Zone (Twenty Twenty-Five Child — discarded)

> Historical prototype only. Do not activate; see the archive parent README.

A child theme of Twenty Twenty-Five whose only job is to ship
[`templates/single-playlist.html`](templates/single-playlist.html) — the
template WordPress uses for the `playlist` custom post type registered by
the [CZ Playlists plugin](../../wp-plugin/cz-playlists/).

## Why a child theme

Twenty Twenty-Five is a block (FSE) theme, so in principle you could add a
`single-playlist` template straight from the Site Editor UI. A child theme
is preferred here instead because:

- It's a plain file you can review in a pull request, not a database row.
- It isn't lost if the Twenty Twenty-Five parent theme is updated or (per
  WordPress's normal FSE behavior) a "Reset" is done on customized templates
  in the Editor.
- It travels with this repo, so restoring or moving the site doesn't depend
  on remembering to redo Site Editor customizations by hand.

## What it does

`single-playlist.html` composes standard core blocks:

- `core/post-title`, `core/post-date`, `core/post-terms` (the `host`
  taxonomy) — no custom fields needed, these read directly off the post.
- A paragraph **bound** via the Block Bindings API to the `cz_description`
  post meta (registered by the plugin) — populated only when the source
  broadcast's `description_status` is `"approved"`.
- `core/post-content` — renders the tracklist table and Mixcloud embed that
  the publisher script writes into `post_content` directly. These are *not*
  bound to custom fields: WordPress's Block Bindings API doesn't currently
  support binding a table's rows or an embed block's URL, only the
  `content` of paragraph/heading, `url`/`text` of a button, and `url`/`alt`/
  `id` of an image.
- A button **bound** via `url` to `cz_spinitron_playlist_url`.

## Install

Copy `cz-playlists-child/` into `wp-content/themes/`, then Appearance →
Themes → activate "Convergence Zone (Twenty Twenty-Five Child)". Twenty
Twenty-Five must already be installed (as the parent) — do not delete it.

## Requires

- WordPress 6.5+ (Block Bindings API)
- The [CZ Playlists plugin](../../wp-plugin/cz-playlists/) active, for the
  `playlist` post type, `host` taxonomy, and `cz_*` post meta this template
  binds to
