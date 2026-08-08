# Operating Procedures

The short version of each recurring workflow. Each one has a matching agent skill in
`.github/skills/`; these are the human-readable steps behind them.

## Weekly, after a show airs

1. Export spins from Spinitron if the current export in
   `shows/convergence-zone/playlists/sources/spinitron/` does not cover the new date. Use
   the **spin search** export — only the `Spins-search-results-` format carries `DJ ID`,
   `Playlist Date-time`, and `Playlist Duration`. If it is a new file, update `SPINS_CSV`
   in `czcache/paths.py` together with `czaudit/build_audit.py` and
   `czaudit/scrape_site.py`.
2. From `tools/python/`:
   ```sh
   make all      # refresh Spinitron IDs, build, verify, regenerate missing-spins
   ```
3. Read the cache diff. Only the new broadcast should have changed. Anything else moving is
   the signal worth chasing.
4. Skim `czcache/reports/` (gitignored, regenerated every build):
   `discrepancies.md`, `repeats.md`, `unmatched.md`, `descriptions-review.md`.
5. Open a PR. CI reruns build + verify and asserts the cache diff is empty.

Skill: `cz-cache-rebuild`.

## Reviewing overrides

Only when a report names something a human has to decide.

1. `make build`, so the reports reflect the current sources.
2. Work through one report at a time, **item by item**. Never batch-apply.
3. Write approvals into `czcache/overrides/*.yaml`, keyed by air date. Quoted and unquoted
   date keys both work.
4. `make check`. If the cache did not change, the override did not fire — investigate
   rather than deleting the entry.
5. Write up any call made against the evidence.

Skill: `cz-override-review`. Background: `shows/convergence-zone/docs/playlist-cache-review-session.md`.

## Publishing a playlist

Plan of record: `shows/convergence-zone/docs/playlist-publishing-plan.md`.

1. Rebuild the cache first. Publish from the cache, never from a source.
2. Confirm the description is `approved`. A `proposed` description is an unreviewed guess
   and must not be published.
3. Preview the rendered post before any write.
4. Back up existing post content — title, slug, date, status, categories, template, body.
5. New post → create as a draft, record the REST `id` and `link` in
   `publication-links.json`. Existing post → replace only the marked generated section, or
   hand it to a human.
6. Catch-up runs go in draft batches of 10–20, reviewed before publishing.

Skill: `cz-publish-playlist`.

## Backfilling a Mixcloud recording

Add `mixcloud_url` to the broadcast's entry in `publication-links.json`, rebuild the cache,
update the same WordPress post. The post identity and URL do not change. A missing
recording is normal and never blocks publishing.

## Archiving an episode

`tools/python/czarchive/` pulls the playlist from Spinitron, captures audio from the
Spinitron Ark stream via ffmpeg, and uploads to Mixcloud. Credentials live in
`~/.czarchive.toml`, outside this repository. Record the resulting Mixcloud URL as above.

## Ending an exploratory session

Write the outcome to a checked-in markdown file — what was decided, why, what was decided
*against* the evidence, and what is still open. Move superseded artifacts to `discarded/`
with a README explaining why.

Skill: `decision-record`. Model: `shows/convergence-zone/docs/playlist-cache-review-session.md`.
