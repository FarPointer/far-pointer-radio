# Discarded Architecture Exploration: WordPress Playlist Publishing

> Historical analysis only. Superseded by
> `shows/convergence-zone/docs/playlist-publishing-plan.md`.

**Date:** August 5, 2026

## Goal

Use the canonical playlist cache to add and update Convergence Zone playlist
posts on WordPress: first in a major catch-up pass, then weekly or in
occasional batches.

The operating workflow should be understandable and repairable without
maintaining a WordPress plugin, a child theme, or a packaged publishing
application unless those components earn their cost.

## Problem

The first implementation grew from a publishing script into a new WordPress
content architecture:

- a `playlist` custom post type
- a `host` taxonomy
- registered custom fields and Block Bindings
- Secure Custom Fields / ACF repeaters
- a Twenty Twenty-Five child theme
- a packaged Python REST client

That architecture is internally coherent, but it solves future querying and
content-model problems that are not currently required. It also conflicts
with the live site's existing organization: 61 playlist pages are already
ordinary WordPress posts in the **Show Playlists** category.

## Invariants

- Existing playlist URLs must keep working.
- Existing manually written descriptions, links, and notes must not be
  destroyed accidentally.
- The playlist cache remains the source of truth for broadcast and spin data.
- Unreviewed descriptions (`description_status != "approved"`) must not be
  published as finished copy.
- Secrets remain outside git.
- New posts are reviewable as drafts before publication.
- Re-running an update must not create duplicate posts or silently unpublish
  an existing published post.

## Non-Goals

- Search-by-artist or database queries over individual spins in WordPress.
- Host archive pages.
- A generalized WordPress content framework.
- Cron, webhooks, or a fully automatic post-air pipeline.
- Replacing WordPress.
- Reformatting every historical post simply for visual uniformity.

## Constraints

- One maintainer and a low-frequency workflow.
- A large initial catch-up, then roughly one post per week or occasional
  batches.
- The live site uses Twenty Twenty-Five and WordPress's REST API.
- `curl` and `jq` are sufficient local dependencies for a shell workflow.
- Current cache coverage is incomplete for publishing:
  - 164 broadcasts
  - 164 with participants
  - 35 with approved descriptions
  - 0 with `webpage_url`
  - 0 with `mixcloud_url`
  - all 164 with `spinitron_playlist_ids` after joining the public Spinitron
    show-history index (170 IDs total; six broadcasts have two)

## External Surfaces

- WordPress REST API:
  - `/wp-json/wp/v2/posts`
  - `/wp-json/wp/v2/categories`
- Existing **Show Playlists** category (`id=2`, slug=`list`)
- WordPress Application Password in
  `shows/convergence-zone/playlists/.wordpress-app-password.local.txt`
- Playlist cache under
  `shows/convergence-zone/playlists/cache/broadcasts/`
- Mixcloud and Spinitron URLs, once those are present in the cache or a small
  publishing override file

## Current System

| Area | Current Owner | Inputs | Outputs | Dependencies | Pain |
|---|---|---|---|---|---|
| Live playlist pages | Standard WordPress posts | Hand-authored blocks | 61 published posts under date-based URLs | Twenty Twenty-Five, category `list` | Content is inconsistent and stops in June 2024 |
| Canonical playlist data | `czcache` | Spinitron exports, set lists, overrides | 164 broadcast JSON files | Python cache builder | Publish-critical URLs are currently absent |
| Proposed WP data model | `cz-playlists` plugin | REST payloads | New CPT, taxonomy, meta | Plugin + SCF/ACF | Duplicates the live site's existing post model |
| Proposed presentation | Child theme | CPT/meta/content | `single-playlist.html` | Parent theme + plugin | Extra deployment and maintenance surface |
| Proposed publisher | `czpublish` Python package | Cache JSON | CPT REST writes | Python, Click, requests, plugin | More concepts than the operating cadence needs |

## Review of the Existing Implementation

### What is worth preserving

- The field mapping from cache data to page content.
- HTML escaping in tracklist rendering.
- Draft-first publishing.
- The distinction between `publish_note` and internal `song_note`.
- The rule that only approved descriptions are published.
- Idempotent create/update as an explicit requirement.
- The two-pass reality that Mixcloud may arrive after the playlist.
- The dry-run concept.

### What is unnecessary now

- A new `playlist` custom post type: it would split old and new playlists
  across two REST endpoints, two archives, and two URL schemes.
- A `host` taxonomy: host archive pages are not a current requirement; a
  simple "Hosted by" block is sufficient.
- Six custom meta fields and Block Bindings: the requested information can
  live directly in ordinary Gutenberg post content.
- SCF/ACF repeaters: they duplicate the rendered tracklist and add a plugin
  dependency. The publisher does not currently populate the repeaters.
- A child theme: Site Editor templates/patterns are adequate for the current
  scope and do not require deploying PHP/theme files.
- A packaged Python CLI: the operation is a small REST transaction over one
  JSON file and can be expressed as a shell script plus a `jq` rendering
  filter.

### Correctness gaps that block deploying it as-is

- The live API has no `playlist` post type because the plugin is not
  installed; deploying it would introduce a parallel content system.
- Core WordPress REST collections do not expose arbitrary
  `meta_key`/`meta_value` querying by default. The current idempotency lookup
  depends on that query without registering REST collection parameters.
- `_build_payload()` always starts with `status: "draft"`. Updating an
  existing published post without `--publish` could move it back to draft.
- `cz_episode_number` writes `0` when the cache value is null, changing
  "unknown" into a real episode number.
- The claimed SCF/ACF `cz_hosts` and `cz_tracklist` copies are not included in
  the REST payload.
- The cache currently contains none of the requested Mixcloud or Spinitron
  URLs, so neither the sophisticated implementation nor a simple script can
  yet produce complete pages.
- Re-rendering an existing post from the cache would remove richer historical
  details that are not represented in the cache, including linked releases
  and some manually formatted timing information.

## Option 1: Keep the Plugin, CPT, Child Theme, and Python Package

### Architecture Shape

Install the work already built, migrate existing playlist posts into the new
`playlist` post type, and use `czpublish` for all future writes.

### Why It Might Work

- Strong structured-data boundaries.
- Future host archives and spin-level querying could be built on top.
- Presentation and content data are explicitly separated.

### Tradeoffs

- Highest concept count and deployment burden.
- Requires migration and redirects for 61 existing posts, or leaves a split
  archive indefinitely.
- Requires fixing the correctness gaps above before the first live write.
- Solves several non-goals.

### Failure Modes

| Failure mode | Warning signal | Prevention |
|---|---|---|
| Old and new playlists diverge | Two archive pages and inconsistent URLs | Migrate all old posts and add redirects |
| Plugin/theme drift | WordPress update breaks bindings or fields | Maintain integration tests and staging site |
| Manual edits disagree with cache | Same tracklist exists in content and repeater meta | Choose one source of truth and remove duplication |

### Disqualifier

Choose this only if host archives, spin queries, or a distinct playlist
content type become near-term product requirements.

## Option 2: Standard Posts + Site Editor + Bash/`jq` Publisher

### Architecture Shape

Keep playlists as ordinary WordPress posts in category `list`. Configure the
existing Single Posts template for the desired common presentation, and
create an unsynced "Playlist Post" block pattern as the manual fallback.

A small `publish-playlists.sh` script:

1. reads one or more cache JSON files
2. renders ordinary Gutenberg blocks with `jq`
3. resolves the existing post from a one-time post map or a deterministic
   slug for new posts
4. creates or updates `/wp-json/wp/v2/posts`
5. preserves the status of existing posts and defaults new posts to draft

### Why It Might Work

- Matches the live site's current content model and URLs.
- Requires no WordPress code deployment or third-party field plugin.
- Makes the WordPress editor show exactly what visitors see.
- Easy to run once, weekly, or over a selected date range.
- Easy to discard if the workflow changes later.

### Tradeoffs

- No structured spin-level queries inside WordPress.
- Bash needs disciplined JSON/HTML handling; use `jq @html`, not shell string
  interpolation.
- Existing posts need a one-time date-to-post-ID mapping because their slugs
  are inconsistent and the cache's `webpage_url` is empty.
- A clear ownership rule is required so automated updates do not overwrite
  valuable manual content.

### Failure Modes

| Failure mode | Warning signal | Prevention |
|---|---|---|
| Existing post is duplicated | Same air date appears at two URLs | Use a reviewed post map; deterministic slugs only for new posts |
| Manual prose is overwritten | Update removes links or special formatting | Back up raw post content; manage only marked blocks or skip historical body replacement |
| Published post becomes draft | Post disappears after an update | Preserve existing `status`; use draft only on creation |
| Bad HTML enters a table | Artist/title containing `&`, `<`, or quotes renders incorrectly | Render with `jq @html`; validate a fixture with special characters |

### Disqualifier

Reject this if WordPress must support database queries over hosts or
individual spins, rather than merely displaying them.

## Option 3: Pattern-Only Manual Publishing

### Architecture Shape

Create an unsynced Playlist Post pattern in the Site Editor. Generate a
Markdown/HTML table locally or copy from the cache, then fill and publish the
post manually.

### Why It Might Work

- Almost no code or operational surface.
- WordPress remains the only editing interface.
- Safest for occasional updates.

### Tradeoffs

- The initial catch-up of roughly 100 missing posts becomes repetitive.
- High risk of transcription errors and inconsistent titles/categories.
- Bulk corrections require touching posts individually.

### Disqualifier

Reject this if the major catch-up includes dozens of posts; the manual effort
will exceed the cost of a small script.

## Tradeoff Matrix

| Dimension | Option 1: Structured WP stack | Option 2: Posts + Bash | Option 3: Manual pattern |
|---|---|---|---|
| Simplicity | Low — multiple deployed components | High — one script, one content model | Highest — no publishing code |
| Fit with live site | Low — introduces a parallel type | Highest — uses existing posts/category | High |
| Initial bulk pass | Medium after migration | High | Low |
| Weekly operation | High but overbuilt | High | Medium |
| Existing URL safety | Low until migration/redirects | High | High |
| Manual editability | Medium — data split across fields/content | High — ordinary blocks | High |
| Query/extensibility | Highest | Low | Low |
| Cleanup burden | High | Low | Lowest |
| Rollback | Hard after CPT migration | Easy | Easy |

## Assumptions

| Assumption | Why It Matters | How to Verify | Fastest Disproof |
|---|---|---|---|
| The live site should keep ordinary posts | Determines whether CPT migration has value | Confirm playlists remain part of the main editorial stream | A concrete requirement for host/spin queries |
| Site Editor can provide acceptable playlist presentation | Avoids a child theme | Build one draft with the configured template/pattern | Required layout cannot be made with core blocks |
| Existing post IDs can be mapped reliably | Prevents duplicate bulk updates | Match the 61 category posts to air dates/episode numbers and review exceptions | Many ambiguous repeats/specials cannot be resolved |
| Publish-critical URLs can be sourced | Complete pages need them | Populate one broadcast with real Mixcloud and Spinitron URLs | No reliable source exists for one or both |
| The script may own a clearly marked portion of content | Enables safe updates | Round-trip one existing draft while preserving surrounding blocks | WordPress normalizes markers unpredictably |

## Risk Register

| Risk | Option(s) affected | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| Cache lacks Mixcloud URLs | All | Certain now | Medium | Publish without the embed; backfill through `publication-links.json` |
| Historical data loses rich links/timing | 1, 2 | High if bodies are replaced | High | Do not bulk-replace old bodies until a preservation policy is chosen |
| Repeat broadcasts map to the wrong post | 1, 2 | Medium | High | Use broadcast date as identity; manually review repeat exceptions |
| Bulk publish makes many bad posts live | 1, 2 | Medium | High | Draft batches of 10–20; review before publishing |
| Site Editor customization is lost/hidden after theme switch | 2, 3 | Low while staying on TT5 | Medium | Export WordPress templates/patterns after configuration |

## Validation Spikes

| Spike | Question answered | Cost | Success signal | Failure signal |
|---|---|---|---|---|
| Build one playlist draft manually with core blocks | Is a plugin/child theme actually needed? | 30–60 minutes | Host, description, table, embed, and link look good on mobile/desktop | Core blocks cannot produce acceptable layout |
| Populate one cache record's external URLs | Can the requested page be generated completely? | 30 minutes | One record has real Mixcloud and Spinitron URLs after cache rebuild | URL ownership/source remains unclear |
| Create a 61-row post map | Can existing posts be updated safely? | 1–2 hours | Every existing playlist maps to one broadcast or an explicit exception | Many ambiguous records remain |
| Bash/`jq` dry-run for one old and one new post | Is the smaller tool sufficient? | 1–2 hours | Deterministic payload, escaped content, preserved status | Shell rendering becomes opaque or fragile |
| Update one private/draft copy twice | Is the workflow idempotent and edit-safe? | 30 minutes | Same post ID updated; manual surrounding block survives | Duplicate or destructive update |

## Recommendation

Choose **Option 2: Standard Posts + Site Editor + Bash/`jq` Publisher**.

It matches the existing site, the real operating cadence, and the requested
level of maintainability. It preserves the valuable parts of the first
implementation (safe rendering rules, draft-first creation, idempotency,
approved-description gating) without deploying a parallel WordPress data
model.

The script should not attempt to be a general CMS client. Its supported
operations should stay narrow:

```text
preview DATE
draft DATE
update DATE
bulk --from DATE --to DATE
```

New posts should use a deterministic slug such as
`convergence-zone-YYYY-MM-DD`. Existing posts should be addressed by a
reviewed date-to-post-ID map, not guessed from inconsistent slugs.

The checked-in `playlists/publication-links.json` is that identity map and the
source for optional recording links. The publisher contract should be:

1. For an existing entry, update `wordpress_post_id`; for a first-time legacy
   edit, accept a post ID/URL once and record it.
2. For a new entry, create the WordPress post and read `id` and `link` from the
   REST response.
3. After a successful WordPress write, atomically record
   `wordpress_post_id` and `webpage_url` under the broadcast date.
4. Include a Mixcloud block only when `mixcloud_url` is non-null.
5. When a recording appears later, add `mixcloud_url`, rebuild the cache, and
   update the same WordPress post. The missing recording is normal state, not
   a publication error.

For existing posts, prefer one of these ownership rules, in order:

1. Update only a clearly marked generated section, preserving manual blocks.
2. If marker replacement proves unreliable, do not automate historical body
   updates; use the script to create missing posts and produce reviewable
   content for manual replacement.
3. Only let the script own the entire body for newly created posts.

## Runner-Up

Option 3 is reasonable after the catch-up is complete if updates become truly
occasional. The same Site Editor pattern remains useful as a fallback even
when Option 2 is adopted.

## Why Option 1 Loses

The structured stack is not bad engineering; it is the wrong scale for the
current problem. Its strongest benefits are outside the stated goals, while
its costs are immediate: migration, redirects, plugin/theme deployment,
duplicated storage, and a split from the 61 existing playlist posts.

## Proposed Next Steps

1. **Do not install the current plugin or child theme.** Keep the files
   temporarily as reference until the simple path is proven.
2. **Configure one Playlist Post pattern and one representative draft** in
   Twenty Twenty-Five using only core blocks. Confirm mobile table behavior,
   Mixcloud embed height, host line, description spacing, and Spinitron link.
3. **Resolve remaining data readiness before automation:** populate optional
   Mixcloud URLs and approved descriptions as available. Spinitron playlist
   IDs are now recovered automatically from the public show-history index.
4. **Build and review the existing-post map** for the 61 Show Playlists posts.
   Back up each post's raw title, slug, date, status, categories, template,
   and content before any update.
5. **Replace `czpublish` with a narrow shell prototype** using `curl` and
   `jq`; prove it on one new draft and one copied historical draft.
6. **Run the catch-up in draft batches of 10–20**, reviewing exceptions,
   repeats, specials, descriptions, embeds, and mobile tables before
   publication.
7. **After the simple workflow succeeds, delete the unused architecture:**
   `website/wp-plugin/cz-playlists/`,
   `website/wp-theme/cz-playlists-child/`, and `tools/python/czpublish/`;
   then update the repository READMEs and session summary.
8. **Reassess after 6–8 weeks.** Add scheduling or richer WordPress structure
   only if actual weekly use demonstrates a concrete need.

## Handoff

### Chosen architecture

Pending confirmation: ordinary WordPress posts in category `list`, rendered
with core blocks and managed by a small Bash/`jq` REST script.

### Critical workflows

- Preview one generated payload.
- Create one new draft.
- Update one existing post without changing its URL or publication status.
- Bulk-create drafts for a date range.
- Re-run after Mixcloud/Spinitron data becomes available.

### Expected deletion zones

- `shows/convergence-zone/website/wp-plugin/cz-playlists/`
- `shows/convergence-zone/website/wp-theme/cz-playlists-child/`
- `tools/python/czpublish/`
- Their entries in parent READMEs

### What still needs proof

- The final Site Editor pattern/template.
- Reliable external URL population.
- Existing post mapping.
- Safe generated-section replacement in Gutenberg content.
