---
name: cz-code-review
description: Review a change in this repository against its specific failure modes — derived data hand-edited, an override that silently does nothing, a non-idempotent build, a source edited in place, a secret. Use when asked to "review this", "review the PR", "check my changes", or before opening a pull request.
---

# Reviewing a change here

Generic review advice is already covered by the reviewer you are running inside. This skill
is only about the mistakes *this* repository makes, which are quiet ones: a feature that
ships documented, with a worked example, and does nothing.

Read the diff, not the description. Then work the checklist below in order — the first
section catches the expensive failures.

## 1. Silent no-ops — the expensive class

This has happened three separate times. It is the first thing to look for.

- **Was a new option, override key, or config field actually threaded through to the code
  that consumes it?** `spins.yaml merge_duplicates` was documented, shipped with a worked
  example, and read by nothing. Trace the value from the file it is written in to the
  function that acts on it. Do not accept "it's in the loader" — find the call site.
- **Does a new gate distinguish "holds" from "not wired up"?** `verify.py` check 9 passed
  for weeks because the file it checked was empty. A check that passes on absent input is
  not a check.
- **Does a YAML date key survive parsing?** PyYAML resolves an unquoted `2026-07-07:` to
  `datetime.date`, not `str`, and the lookups use string broadcast ids. `load_overrides()`
  normalises both forms; anything new reading YAML by date must too.
- **Is there a test that would fail if the wiring were removed?** For override paths,
  parser heuristics, and gates, that test is required — see
  `tools/python/czcache/tests/test_overrides.py`.

## 2. The playlist cache

- **`shows/convergence-zone/playlists/cache/` is derived.** A diff there must be
  explainable by a source or override change in the same PR. A hand-edit is a defect even
  if the value is right.
- **Is the cache diff proportionate?** Adding one broadcast should change one broadcast.
  Dozens of unrelated files moving means a loader or an ordering changed — say so.
- **Is the build still idempotent?** `cd tools/python && make check` must pass: build,
  verify, and a zero-line cache diff. This is what makes the cache reviewable at all.
- **`playlists/sources/` is read-only.** A modified export, workbook, or OneNote file is
  wrong; a *new* file alongside the old is right.
- **Did `SPINS_CSV` change?** It re-bases the whole archive and must move together with
  `czaudit/build_audit.py` and `czaudit/scrape_site.py`, or the cache and the audit will
  reconcile different files.

## 3. Human decisions

- **`czcache/overrides/*.yaml` records what a person decided.** In a PR authored by an
  agent, every added entry needs evidence the user approved that specific item. Inferred
  entries are the failure, not the typo.
- **No `proposed` description may become `approved` in an automated change.** Approved text
  is what the site publishes.
- **`publication-links.json` IDs come from real REST responses.** A guessed
  `wordpress_post_id`, or identity re-derived from a historical slug, breaks post identity
  irreversibly.
- **`dj_ids` is not host attribution.** Any new code deriving hosts from `dj_id` is wrong —
  two personas display the identical name "Jim Causey".

## 4. Scope and hygiene

- **Is the diff scoped to one change?** Unrelated files that were already dirty in the
  working tree should not be here.
- **Secrets:** no `.env*`, `~/.czarchive.toml`, API keys, OAuth tokens, or cookies — in the
  diff *or* in an example, a test fixture, a log line, or a URL.
- **New directory?** It needs a `README.md` with a table of its contents.
- **Names:** kebab-case; playlists `YYYY-MM-DD-episode-title.csv`.
- **Superseded work** belongs in `discarded/` with a README explaining what replaced it,
  not deleted.
- **Documentation that is now false.** A changed run command, path, or count invalidates
  the README next to it. `AGENTS.md` is the single source — a rule added to `CLAUDE.md` or
  `.github/copilot-instructions.md` is in the wrong file.

## 5. Python

- `make lint` and `make test` clean.
- Dependencies declared in the package's `pyproject.toml` with `uv.lock` updated — not a
  `--with` flag, not a `requirements.txt`.
- New `sys.path` manipulation needs a reason; the existing `czaudit` import is deliberate
  and documented, not a precedent for more.
- Reports, intermediate JSON, `site_html/`, and workbook copies beside the scripts are
  gitignored on purpose and must not appear.

## How to report

Lead with anything in section 1 — a silent no-op is worth more than everything else
combined. Then correctness, then scope, then style.

For each finding: the file and line, what breaks, and how you know. Distinguish
"this is wrong" from "I could not verify this from the diff" — for the second, say what
would settle it (usually running `make check` and reading the cache diff).

Say clearly when the change is fine. Do not manufacture findings.

## Do not

- Run `make build` against a dirty tree and attribute the resulting diff to the PR.
- Edit the code you are reviewing.
- Commit, push, or approve anything.
