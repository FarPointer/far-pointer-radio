# Instagram promo recovery runbook

This document describes what remains to fully operationalize Instagram promo recovery for Convergence Zone, using the new reuse-first tooling that is already implemented in `tools/python/czcache/`.

## Goal

Recover promo copy from `@converge.fm` Instagram posts and feed it into the existing `czcache` description pipeline as **proposed** text (never auto-approved).

## What is already implemented

- `tools/python/czcache/fetch_instagram_promos.py`  
  Normalizes Instagram post captions into `shows/convergence-zone/playlists/sources/instagram/promos.json` from:
  1. Instaloader export (`--instaloader-dir`)
  2. Meta Graph API (`--graph-token` + `--ig-user-id`)
  3. Existing JSON dump (`--input-json`)

- `tools/python/czcache/load_instagram.py`  
  Maps normalized caption posts to broadcast dates and emits description candidates.

- `tools/python/czcache/build.py` integration  
  Merges OneNote + Instagram candidates deterministically (score-first, OneNote tie-break), then preserves review-gated description behavior.

- Reporting/schema/docs integration was added so Instagram provenance appears in review output and `instagram` is a valid source.

## Remaining work to complete

1. Set up a repeatable ingestion source (Instaloader recommended first).
2. Validate Meta prerequisites (for Graph API path now or later).
3. Run first real ingestion and build.
4. Review proposed descriptions and approve selected ones in `overrides/descriptions.yaml`.

## Option A (recommended): Instaloader setup

Use this first to avoid building new infra and avoid Meta app setup friction.

### 1. Install Instaloader

```sh
python3 -m pip install --user instaloader
```

### 2. Export post metadata for `@converge.fm`

From a local working directory for exports:

```sh
instaloader --login=converge.fm --no-pictures --no-videos --no-video-thumbnails --no-compress-json --metadata-json profile converge.fm
```

Notes:
- This creates per-post JSON metadata files containing caption text/timestamps.
- Keep this export folder outside the repo or in a local temp area.

### 3. Normalize export into repo source format

From `tools/python/czcache/`:

```sh
uv run python fetch_instagram_promos.py --instaloader-dir /absolute/path/to/instaloader-output
```

This writes:

`shows/convergence-zone/playlists/sources/instagram/promos.json`

## Option B: Meta Graph API prerequisites and setup

Use this if you want the official API path.

### Required account/platform prerequisites

1. `@converge.fm` must be an Instagram **Professional** account (Business/Creator).
2. Decide login mode:
   - **Instagram Login** path, or
   - **Facebook Login** path (requires linked Facebook Page + admin-equivalent access).
3. Create/configure a Meta developer app.
4. Grant required permissions for media read access.
5. Obtain and maintain long-lived access token(s).

### Access-level expectation

- For a private/internal workflow that only serves your own managed account, target **Standard Access** first.
- **Advanced Access / App Review / Business Verification** is only needed if you serve accounts you do not own/manage.

### Run Graph API ingestion

From `tools/python/czcache/`:

```sh
uv run python fetch_instagram_promos.py --graph-token "$IG_TOKEN" --ig-user-id "$IG_USER_ID"
```

## Option C fallback: existing JSON dump or data-export conversion

If you already have post data in JSON shape:

```sh
uv run python fetch_instagram_promos.py --input-json /absolute/path/to/posts.json
```

Accepted shapes:
- `{"posts": [...]}`
- `[...]` (array of post objects)

Each post should include at least: `id`, `timestamp`, `caption` (plus optional `permalink`, `media_type`, `source`).

## Build and review workflow

From `tools/python/czcache/`:

```sh
uv run --with openpyxl --with beautifulsoup4 --with lxml --with pyyaml python build.py
uv run --with openpyxl --with beautifulsoup4 --with lxml --with pyyaml python verify.py
```

Then review:

- `tools/python/czcache/reports/descriptions-review.md`

Approve selected descriptions by adding entries to:

- `tools/python/czcache/overrides/descriptions.yaml`

Remember:
- Instagram/OneNote candidates stay `description_status: "proposed"` until approved.
- Only override entries become `"approved"`.

## Secrets and safety

- Do **not** commit tokens, cookies, or credentials.
- Keep Meta tokens in environment variables or local secret config.
- Keep any raw account export artifacts outside repo unless intentionally normalized to `promos.json`.

## Definition of done

This work is complete when all are true:

1. A repeatable ingestion path is chosen (Instaloader or Graph API).
2. `promos.json` is generated from real `@converge.fm` posts.
3. `build.py` + `verify.py` run cleanly with the new data.
4. You have reviewed candidate descriptions and approved desired entries in overrides.
