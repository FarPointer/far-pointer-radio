---
name: cz-cache-rebuild
description: Rebuild the Convergence Zone playlist cache after a new episode airs or a source changes. Use when asked to "rebuild the cache", "a new episode aired", "refresh Spinitron", or "regenerate missing spins".
---

# Rebuilding the playlist cache

The cache at `shows/convergence-zone/playlists/cache/` is derived output that lives in the
repository. It is reviewable in a pull request only because the build is idempotent: a run
that changes nothing produces a zero-line diff. Your job is to keep that true.

## Scope

You rebuild. You **do not** decide anything. If the build asks for a human decision — a
description to approve, a host to attribute, a repeat to confirm — report it and stop.
Editing `tools/python/czcache/overrides/*.yaml` is the `cz-override-review` skill's job,
and it happens with the user present.

## Steps

Work from `tools/python/`. Never invent a `uv run --with` incantation; dependencies come
from each package's `pyproject.toml`.

1. **Confirm a clean starting point.** `git status --porcelain`. If the cache or the
   sources are already dirty, say so and ask before proceeding — you cannot tell your
   diff from someone else's.

2. **Refresh Spinitron identity, but only if new broadcasts have aired.**

   ```sh
   make refresh-spinitron
   ```

   This re-snapshots playlist IDs from the public show-history page into
   `sources/spinitron/convergence-zone-playlists.json`. Skip it if nothing new has aired —
   it is a network call against someone else's site.

   The spins export itself has **no Playlist ID column**, so this snapshot is the only
   source of those IDs. If the public page has changed shape, do not improvise a scrape:
   the documented fallback is the Spinitron v2 API with a station key kept outside the
   repo. Report and stop.

3. **Is a new spins export needed?** `paths.SPINS_CSV` names the authoritative export. A
   new episode's spins are only in the cache if the export covers them. If it does not,
   the user must export from Spinitron — only the `Spins-search-results-` format carries
   `DJ ID`, `Playlist Date-time`, and `Playlist Duration`. Changing `SPINS_CSV` re-bases
   the whole archive and must be done together with `czaudit/build_audit.py` and
   `czaudit/scrape_site.py`. Ask first.

4. **Build and verify.**

   ```sh
   make check
   ```

   That is `build.py`, then `verify.py`, then `git diff --exit-code` on the cache. All
   three must pass. `verify.py` exits non-zero on failure and prints exactly which
   invariant broke.

5. **Regenerate the analysis workbook** if workbooks or the export changed:

   ```sh
   make missing-spins
   ```

## Reporting

Summarise, do not dump. The user wants to know what moved:

- Counts before and after: broadcasts, spins, A/B/C class split.
- The **cache diff by file** — which broadcasts changed and how. A diff touching
  broadcasts nobody expected to change is the signal worth surfacing.
- New entries in `reports/discrepancies.md`, `reports/repeats.md`, and
  `reports/unmatched.md` — these name what a human may need to decide.
- New proposed descriptions in `reports/descriptions-review.md`. State the count and stop.
  **Never** promote `proposed` to `approved`.

`reports/` is gitignored and regenerated every build. Do not commit it.

## Failure modes to name explicitly

- **The build changed the cache but you changed no source.** That is a non-idempotent
  build, i.e. a bug. Do not commit it; investigate.
- **`verify.py` fails.** Report the failing check verbatim. Do not "fix" the cache by hand
  — it is derived; fix the source or the loader.
- **An override produced no change.** An entry that names a pair or a date that does not
  exist does nothing silently. `verify.py`'s gate checks catch this; take a failure there
  seriously rather than deleting the entry.

## Do not

- Hand-edit anything under `cache/`.
- Touch `overrides/*.yaml`.
- Commit, push, or open a PR unless asked.
