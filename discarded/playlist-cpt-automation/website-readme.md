# Website README from discarded playlist architecture

> Historical context only. Do not follow these installation instructions.

WordPress theme overrides, custom CSS, copy, and assets for
[convergencezone.fm](https://convergencezone.fm).

## Directory Structure

| Directory | Contents |
|---|---|
| `wp-plugin/cz-playlists/` | Plugin registering the `playlist` custom post type, `host` taxonomy, and custom fields — see its README |
| `wp-theme/cz-playlists-child/` | Twenty Twenty-Five child theme providing the `single-playlist` template — see its README |

`site-mockup-homepage.html` and `site-mockup-v2.html` are static design mockups
from an earlier full-rebuild exploration (see
`../docs/website-rebuild-brief.md`) — kept for reference, not part of the live
site.

## How these fit together

Episode pages are published automatically by
[`tools/python/czpublish`](../../../tools/python/czpublish/), which reads
`../playlists/cache/broadcasts/` and creates/updates `playlist` posts via the
WordPress REST API. The plugin and child theme here are what make those
posts render correctly:

1. `wp-plugin/cz-playlists/` defines the data model (post type, taxonomy,
   custom fields).
2. `wp-theme/cz-playlists-child/` defines how a `playlist` post displays.
3. `tools/python/czpublish/` fills in the data.
