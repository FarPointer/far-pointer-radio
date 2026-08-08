# Python Tools

Python scripts and packages for radio production.

## Contents

| Directory | Purpose | Requires |
|---|---|---|
| `czarchive/` | Archives Convergence Zone episodes — Spinitron playlist → Ark stream capture → Mixcloud upload | Python 3.11+, `uv`, `ffmpeg` |
| `czaudit/` | Reconciles Convergence Zone set lists (OneNote notes, convergencezone.fm playlists) against Spinitron and writes the audit workbook | Python 3.11+, `uv` |
| `czcache/` | Builds the canonical playlist cache at `shows/convergence-zone/playlists/cache/` from every playlist source | Python 3.11+, `uv` |

## Task runner

Ordering matters between the czcache steps, so it lives in `Makefile` rather than in
anyone's memory. From this directory:

| Target | Does |
|---|---|
| `make build` | Rebuild the playlist cache |
| `make verify` | Assert the cache invariants; exits non-zero on failure |
| `make check` | `build` + `verify` + assert a zero-line diff under `cache/` — what CI runs |
| `make refresh-spinitron` | Re-snapshot Spinitron playlist IDs from the public show page |
| `make missing-spins` | Regenerate `cz-missing-spins.xlsx` and `cz-removal-candidates.csv` |
| `make all` | `refresh-spinitron` → `build` → `verify` → `missing-spins` |
| `make audit` | Run the czaudit pipeline |
| `make lint` / `make format` | `ruff check` / `ruff format`, configured in `ruff.toml` |
| `make test` | `pytest` |

## Conventions

Every tool declares its dependencies in its own `pyproject.toml` and commits a `uv.lock`.
Run them with `uv run <command>` from the package directory — [`uv`](https://docs.astral.sh/uv/)
syncs the environment automatically, so there is no `--with` incantation and no
`requirements.txt`. Virtual environments (`.venv/`) are never committed.

`czcache` and `czaudit` are flat scripts run in place rather than installed distributions
(`[tool.uv] package = false`); `czcache` reaches into `czaudit` through `sys.path` so the
cache and the audit can never disagree about what matched what. `czarchive` is a real
packaged CLI.

Lint and format settings are shared across all three in `ruff.toml`.
