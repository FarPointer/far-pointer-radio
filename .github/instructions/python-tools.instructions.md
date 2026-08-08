---
applyTo: "tools/python/**"
---

# Python tools

- Python **3.11+**, environments managed with [`uv`](https://docs.astral.sh/uv/). Never
  `pip install` into the system interpreter and never commit a `.venv/`.
- Run everything through the task runner in `tools/python/Makefile` rather than by hand,
  so the required ordering lives in one place: `make build`, `make verify`, `make all`,
  `make missing-spins`, `make refresh-spinitron`, `make lint`, `make test`.
- Each package declares its own dependencies in its `pyproject.toml`. `uv run` syncs them
  automatically; do not re-derive a `--with` incantation.
- `czcache` imports matching primitives from `czaudit` via `sys.path` (see
  `czcache/paths.py:CZAUDIT`). That is deliberate — the audit and the cache must never
  disagree about what matched what. Do not fork or reimplement `czaudit.matching`.

## Order matters

`czcache` steps have a required order, encoded in `make all`:

1. `fetch_spinitron_playlists.py` — refresh the public playlist-ID snapshot
2. `build.py` — rebuild the cache
3. `verify.py` — assert the invariants; exits non-zero on failure
4. `build_missing_spins.py` then `enrich_missing_spins.py` — regenerate the analysis
   workbook

Repeat detection runs before classification inside `build.py`; do not reorder it.

## Before you commit

- `make build && make verify` must pass, and a rebuild that changes nothing must produce a
  **zero-line diff** under `shows/convergence-zone/playlists/cache/`. CI enforces both.
- `make lint` (ruff) must be clean for files you touched.
- Add a `pytest` case whenever you fix a bug in an override path, a parser heuristic, or a
  gate — those are the failures that have historically passed silently.

## Never

- Hand-edit `shows/convergence-zone/playlists/cache/` — it is derived output.
- Write `czcache/overrides/*.yaml` on your own judgement. Those are human decisions.
- Commit `reports/`, `site_html/`, intermediate JSON, or workbook copies beside the
  scripts — all gitignored on purpose.
