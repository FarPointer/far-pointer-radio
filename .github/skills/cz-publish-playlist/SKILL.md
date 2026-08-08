---
name: cz-publish-playlist
description: Publish or update the convergencezone.fm WordPress post for a broadcast. Use when asked to "publish the playlist for <date>", "update the WordPress post", "add the Mixcloud link", or "run the catch-up batch".
---

# Publishing a playlist to WordPress

The plan of record is `shows/convergence-zone/docs/playlist-publishing-plan.md`. Read it
before doing anything; this skill is the operating procedure, not the decision.

## Shape of the solution

Playlists are **ordinary WordPress posts** in the existing **Show Playlists** category,
rendered by one block pattern built in the Twenty Twenty-Five Site Editor. Publishing is a
small Bash script using `curl` and `jq`.

Explicitly out of scope — do not propose or build these:

- A custom post type, host taxonomies, or host archive pages
- Secure Custom Fields / ACF
- A child theme
- A packaged Python publisher
- Scheduled unattended publishing
- Spin-level search inside WordPress

An earlier custom-post-type approach was tried and rejected; it is archived under
`discarded/playlist-cpt-automation/` with the reasoning.

## Post identity

`shows/convergence-zone/playlists/publication-links.json`, keyed by broadcast date:

```json
{
  "2026-07-28": {
    "wordpress_post_id": 123,
    "webpage_url": "https://convergencezone.fm/2026/07/convergence-zone-2026-07-28/",
    "mixcloud_url": null
  }
}
```

- **Existing post:** use the recorded `wordpress_post_id`.
- **New post:** create the draft, then record the REST response's `id` and `link`.
- **Never** guess an ID, and never re-derive identity from historical slugs — they are
  inconsistent, and the initial mapping is the only time they are consulted.
- `webpage_url` and `mixcloud_url` flow into the cache; `wordpress_post_id` does not
  (it is not part of `schema.ts`).
- Update the file atomically. Losing it means losing post identity for the whole archive.

## Steps

1. **Refresh the data.** Run the `cz-cache-rebuild` skill first if anything upstream
   changed. Publish from the cache, never from a source file.

2. **Check the description.** Only `description_status: "approved"` may be published. A
   `proposed` description is an unreviewed guess — omit it and say so, or route the user
   through `cz-override-review`. Publishing unreviewed prose is the specific failure this
   whole gate exists to prevent.

3. **Preview.** Render the post body and show it before any write. Never write first.

4. **Back up before touching an existing post.** Save the raw title, slug, date, status,
   categories, template, and content. There are ~61 existing Show Playlists posts, many
   with hand-written prose, links, and formatting.

5. **Write.**
   - New post → create as a **draft**, then record `id` and `link`.
   - Existing post → replace only the clearly marked generated section. If that boundary
     cannot be located reliably, **stop** and hand the post to the user for manual review.
     Automate new posts; do not automate destructive historical replacements.
   - Preserve existing URLs, slugs, categories, and publication status.

6. **Batch.** Catch-up runs go in draft batches of 10–20, reviewed before publishing.
   Check descriptions, hosts, repeats, table rendering, and links each batch.

7. **Verify.** Re-fetch the post and confirm the identity, URL, and status are unchanged.
   Prove one new post and one historical update twice before trusting a batch.

## Mixcloud

Most episodes have no recording. That is normal and **does not block publishing** — the
post simply omits the embed. When a recording appears later: add `mixcloud_url`, rebuild
the cache, update the same post. The post identity and URL do not change.

## Credentials

The WordPress application password lives outside the repository, in the environment. Never
write it into a file here, never echo it, never put it in a URL that gets logged.

## Do not

- Overwrite hand-written prose without showing the user first.
- Publish a `proposed` description.
- Change a post's slug, category, or status as a side effect.
- Commit, push, or open a PR unless asked.
