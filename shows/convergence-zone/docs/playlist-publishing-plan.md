# Playlist Publishing Plan

**Status:** Active plan. This replaces the custom-post-type/plugin/child-theme
approach archived under `discarded/playlist-cpt-automation/`.

## Recommendations

1. Keep playlists as ordinary WordPress posts in the existing **Show
   Playlists** category.
2. Build one playlist pattern in the Twenty Twenty-Five Site Editor using core
   blocks for hosts, description, tracklist, optional Mixcloud embed, and the
   Spinitron link.
3. Use a small Bash script with `curl` and `jq` for previewing, creating drafts,
   updating posts, and processing date ranges.
4. Store WordPress post IDs/URLs and optional Mixcloud URLs in
   `playlists/publication-links.json`, keyed by broadcast date.
5. Treat a missing Mixcloud recording as normal. Publish without an embed and
   add it later by updating the link data and the same WordPress post.
6. Continue extracting Spinitron playlist IDs from the public show-history
   snapshot. The spins CSV itself does not contain Playlist IDs.
7. Preserve existing post URLs, slugs, categories, and publication status.
8. Back up existing post content and avoid overwriting manually written prose,
   links, or formatting without review.
9. Run the initial catch-up as draft batches of 10–20 posts, then use the same
   workflow weekly or for occasional bulk updates.

## Deliverables

| Deliverable | Steps required | Kind |
|---|---|---|
| Playlist block pattern | Build it in Site Editor; check desktop/mobile table behavior and Mixcloud layout; export/save the configuration | WordPress configuration |
| Bash/`jq` publisher | Add preview, create-draft, update, and date-range modes; authenticate with the existing application password; escape generated HTML | Tooling |
| Publication-link handling | Read and atomically update `publication-links.json`; record REST response `id` and `link`; preserve optional `mixcloud_url` | Tooling |
| Existing-post map | Fetch the 61 Show Playlists posts; match each applicable broadcast to a WordPress post ID; review exceptions and repeats | Tooling + review |
| Existing-post backup | Save raw title, slug, date, status, categories, template, and content before bulk updates | Tooling |
| Safe update boundary | Prefer replacing a clearly marked generated section; if that proves unreliable, automate new posts and review historical replacements manually | Tooling + process |
| Spinitron identity refresh | Run `czcache/fetch_spinitron_playlists.py` before rebuilding after new shows; retain all IDs for persona-split broadcasts | Tooling — completed |
| Mixcloud backfill procedure | Add a URL when a recording exists; rebuild the cache; update the same WordPress post | Process |
| Pilot | Test one new draft and one copied historical post twice to prove stable identity and non-destructive updates | Process |
| Catch-up pass | Create/update drafts in batches of 10–20; review descriptions, hosts, repeats, tables, and links before publishing | Process |
| Weekly/bulk procedure | Document the short refresh → preview → draft/update → review sequence | Documentation |

## Work Breakdown

- **Tooling/configuration:** 7 deliverables, including the completed Spinitron
  identity work.
- **Process/review:** 4 deliverables.
- **Documentation:** this plan plus the final short operating procedure.

## Required Order

1. Configure and approve the WordPress pattern.
2. Implement publication-link updates and the Bash publisher.
3. Build the existing-post map and backups.
4. Prove one new and one historical update.
5. Run the catch-up in draft batches.
6. Write the final weekly/bulk operating procedure after the workflow has been
   used successfully.

## Publication Identity

For existing posts, use the recorded WordPress post ID. For new posts, create
the draft and record the REST response's `id` and `link` in
`publication-links.json`. Never infer identity from inconsistent historical
slugs after the initial mapping.

`mixcloud_url` may be absent or null. Its absence does not block publishing.
Adding it later updates the same post.

## Out of Scope

- A custom WordPress post type
- Host taxonomies or host archive pages
- Secure Custom Fields/ACF
- A child theme
- A packaged Python publisher
- Scheduled unattended publishing
- Spin-level search inside WordPress
