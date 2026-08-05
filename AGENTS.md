# AGENTS.md

This file provides guidance to GitHub Copilot CLI (and other agent tools that read `AGENTS.md`) when working with code in this repository.

## Repository

A monorepo for radio show production, tooling, and related content. See `README.md` for the full directory layout.

## Convergence Zone

A weekly ambient, atmospheric, and space music program airing Tuesday nights at 8:30 PM PT on **90.7 KSER-FM** (Everett, WA) and **89.9 KXIR-FM** (Freeland, WA), streaming at kser.org and on TuneIn. Hosted by Jim Causey and MichaelG. The show spotlights Pacific Northwest artists alongside the contemporary and legendary musicians who inspire them.

Site: [convergencezone.fm](https://convergencezone.fm) — currently WordPress, hosted through Porkbun. A rebuild is in planning; see `shows/convergence-zone/docs/website-rebuild-brief.md` for the analysis, decisions, and open questions.

### Website design tokens

Used by the mockups in `shows/convergence-zone/website/`, documented at the bottom of each HTML file:

| Role | Value |
|---|---|
| Headings | Cormorant Garamond |
| Body | Inter |
| Metadata / code | Space Mono |
| Background | `#080b12` (deep navy) |
| Accent — teal | `#7cc4c0` |
| Accent — violet | `#8f88be` |
| Accent — gold | `#c4a97e` |

The mockups are self-contained static HTML with embedded `<style>` blocks — no JavaScript, no build tools, no dependencies. Serve them with `python3 -m http.server 8080` from the `website/` directory.

## Conventions

- **Every directory carries a `README.md`** with a table mapping each subdirectory to its purpose. New directories are expected to ship with one.
- **kebab-case** for all file and directory names.
- Playlists are named `YYYY-MM-DD-episode-title.csv`.
- Empty directories are held by `.gitkeep`.
- `.gitattributes` enforces LF for text, CRLF for PowerShell, and binary handling for audio/image/office formats.

## Tooling

- `tools/python/` — Python 3.11+ packages and scripts, managed with `uv`.
- `tools/powershell/` — PowerShell modules and scripts.

### czarchive

`tools/python/czarchive/` archives Convergence Zone episodes — pulls playlists from Spinitron, captures audio from the Spinitron Ark stream via ffmpeg, and uploads to Mixcloud.

Credentials live in `~/.czarchive.toml`, **outside** this repo. Note that `config.py` writes a default config to that path on first load, and `save_token()` writes the Mixcloud OAuth token back into it. Never commit it — it is gitignored, and `.czarchive.toml.example` documents the shape.

## Secrets

Never commit: `.env*`, `~/.czarchive.toml`, Spinitron API keys, Mixcloud client secrets or OAuth tokens, or session cookies. `.gitignore` covers the common cases but is not a substitute for checking `git status` before committing.
