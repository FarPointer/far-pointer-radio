# Discarded Playlist CPT Automation

**Status:** Discarded August 5, 2026. Do not install, run, or use as current
guidance.

This prototype introduced a WordPress `playlist` custom post type, host
taxonomy, custom fields, Secure Custom Fields/ACF integration, a Twenty
Twenty-Five child theme, and a packaged Python publisher.

It was discarded because:

- The live site already has 61 playlist pages as ordinary posts in the
  **Show Playlists** category.
- A new post type would split old and new playlists across different archives,
  REST endpoints, and URL schemes.
- The plugin, field plugin, child theme, and Python package created more
  maintenance than a weekly or occasional bulk-publishing workflow requires.
- The same visible result can be produced with core WordPress blocks and a
  narrow Bash/`jq` publisher.

The active replacement is:

`shows/convergence-zone/docs/playlist-publishing-plan.md`

## Contents

| Path | Contents |
|---|---|
| `wordpress-plugin/` | Discarded custom post type, taxonomy, metadata, and SCF/ACF field-group prototype |
| `wordpress-child-theme/` | Discarded Twenty Twenty-Five child-theme template |
| `python-publisher/` | Discarded packaged REST publisher |
| `playlist-automation-session-summary.md` | Historical session record |
| `playlist-publishing-options.md` | Longer architecture exploration |
| `website-readme.md` | Website README written for the discarded architecture |

The useful rules discovered during this work remain active elsewhere:
approved-description gating, HTML escaping, stable WordPress post identity,
optional/backfillable Mixcloud links, and public Spinitron playlist-ID
extraction.
