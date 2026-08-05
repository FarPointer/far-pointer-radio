# Python Tools

Python scripts and packages for radio production.

## Contents

| Directory | Purpose | Requires |
|---|---|---|
| `czarchive/` | Archives Convergence Zone episodes — Spinitron playlist → Ark stream capture → Mixcloud upload | Python 3.11+, `uv`, `ffmpeg` |
| `czaudit/` | Reconciles Convergence Zone set lists (OneNote notes, convergencezone.fm playlists) against Spinitron and writes the audit workbook | Python 3.11+, `uv` |
| `czcache/` | Builds the canonical playlist cache at `shows/convergence-zone/playlists/cache/` from every playlist source | Python 3.11+, `uv` |

## Conventions

Packaged tools manage their own dependencies with [`uv`](https://docs.astral.sh/uv/) and ship a `pyproject.toml` and `uv.lock`. Run them with `uv run <command>` from the package directory; `uv sync` recreates the environment. Virtual environments (`.venv/`) are never committed.

Standalone single-file scripts ship a `requirements.txt` instead.
