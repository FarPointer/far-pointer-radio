# AGENTS.md

**This file is the single source of agent guidance for this repository.** `CLAUDE.md` and
`.github/copilot-instructions.md` are pointers at this file — edit this one, never the
pointers.

| Surface | Holds |
|---|---|
| `AGENTS.md` (this file) | Everything general: how the repository works, how I work, what must not be touched |
| `.github/instructions/*.instructions.md` | Path-scoped rules, applied by `applyTo` glob |
| `.github/skills/*/SKILL.md` | Repeatable procedures — cache rebuild, override review, publishing, code review, decision records, episode prep |
| `.claude/hooks/` | Claude Code hooks: secret scan, overrides guard, verify reminder |
| `.github/workflows/verify-cache.yml` | The CI gate that enforces the cache invariants |
| `CONTRIBUTING.md` · `docs/operating-procedures.md` | The same conventions and workflows, written for a person |

## Repository

A monorepo for radio show production, tooling, and related content. See `README.md` for the full directory layout.

## Convergence Zone

A weekly ambient, atmospheric, and space music program airing Tuesday nights at 8:30 PM PT on **90.7 KSER-FM** (Everett, WA) and **89.9 KXIR-FM** (Freeland, WA), streaming at kser.org and on TuneIn. Hosted by Jim Causey and MichaelG. The show spotlights Pacific Northwest artists alongside the contemporary and legendary musicians who inspire them.

Site: [convergencezone.fm](https://convergencezone.fm) — WordPress, hosted through Porkbun. The site is actively maintained and being improved. An earlier rebuild exploration is archived at `shows/convergence-zone/docs/website-rebuild-brief.md`.

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

## How I work

These are working rules, not suggestions. They come from repeated corrections in past
sessions.

- **Never commit, push, or open a PR unless asked.** Show the diff and wait. If work has
  already been committed locally, say so before doing anything else.
- **Scope every commit and PR to the files touched in this session.** Do not sweep up
  unrelated changes that were already in the working tree.
- **Explore and confirm direction before building tooling.** Propose options, get a
  decision, then implement. A sophisticated tool nobody asked for is a worse outcome than
  a short script that matches the intent.
- **Superseded work moves to `discarded/`**, not to the trash — with a `README.md` naming
  what replaced it and why. See `discarded/README.md`.
- **Decision docs are a deliverable.** When a session settles a question, write it to a
  checked-in markdown file (in `docs/` or the relevant `shows/*/docs/`) covering what was
  decided, why, and anything decided *against* the evidence. Chat history is not storage.
  `shows/convergence-zone/docs/playlist-cache-review-session.md` is the model.
- **Ask item by item** when reviewing a list of human decisions. Do not batch-apply.
- **Prefer an issue for multi-step work**, then let the coding agent pick it up.

## Data safety

Some files encode human judgement and must never be written by inference:

| Path | Rule |
|---|---|
| `tools/python/czcache/overrides/*.yaml` | Checked-in human decisions. Never auto-approve a description; `proposed` becomes `approved` only when a person says so. Propose edits, never apply them unasked. |
| `shows/convergence-zone/playlists/publication-links.json` | WordPress post identity. Record the REST response's `id` and `link`; never guess an ID and never re-derive identity from historical slugs. |
| `tools/python/czcache/paths.py` (`SPINS_CSV`) | Names the authoritative Spinitron export. Changing it re-bases the whole cache — change it deliberately, together with `czaudit/build_audit.py` and `czaudit/scrape_site.py`. |
| `shows/convergence-zone/playlists/cache/` | Derived output. Never hand-edit; change a source or an override and rebuild. |
| `shows/convergence-zone/playlists/sources/` | Raw upstream material. Read-only. |

## Conventions

- **Every directory carries a `README.md`** with a table mapping each subdirectory to its purpose. New directories are expected to ship with one.
- **kebab-case** for all file and directory names.
- Playlists are named `YYYY-MM-DD-episode-title.csv`.
- Empty directories are held by `.gitkeep`.
- `.gitattributes` enforces LF for text, CRLF for PowerShell, and binary handling for audio/image/office formats.

## Tooling

- `tools/python/` — Python 3.11+ packages and scripts, managed with `uv`.
- `tools/powershell/` — PowerShell modules and scripts.

Run the Python tools through the task runner rather than by hand, so ordering stays in one
place. From `tools/python/`:

```sh
make build      # rebuild the playlist cache
make verify     # assert the cache invariants (exits non-zero on failure)
make all        # refresh Spinitron IDs, build, verify, regenerate missing-spins
make lint       # ruff check
make test       # pytest
```

### czcache

`tools/python/czcache/` builds the canonical playlist cache. The build is idempotent — a
run that changes nothing produces a zero-line diff, which is what makes the cache
reviewable in a pull request. Always run `make verify` after `make build`; CI does the
same on every PR.

### czaudit

`tools/python/czaudit/` reconciles set lists against Spinitron and writes the audit
workbook. `czcache` imports its matching primitives, so the two can never disagree about
what matched what.

### czarchive

`tools/python/czarchive/` archives Convergence Zone episodes — pulls playlists from Spinitron, captures audio from the Spinitron Ark stream via ffmpeg, and uploads to Mixcloud.

Credentials live in `~/.czarchive.toml`, **outside** this repo. Note that `config.py` writes a default config to that path on first load, and `save_token()` writes the Mixcloud OAuth token back into it. Never commit it — it is gitignored, and `.czarchive.toml.example` documents the shape.

## Secrets

Never commit: `.env*`, `~/.czarchive.toml`, Spinitron API keys, Mixcloud client secrets or OAuth tokens, or session cookies. `.gitignore` covers the common cases but is not a substitute for checking `git status` before committing.

## MCP servers

`.mcp.json` configures two, both chosen for work that actually happens here:

- **github** — this repository is worked through issues and pull requests, and CI status is
  part of the loop. The `Authorization` header reads `$GITHUB_PERSONAL_ACCESS_TOKEN` from
  the environment; no token is ever written into the file.
- **playwright** — Spinitron's calendar and host display, convergencezone.fm rendering, and
  the WordPress block pattern are visual verification problems that fetching HTML cannot
  settle.
