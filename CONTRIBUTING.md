# Contributing

A personal/volunteer working repository. These are the conventions that keep it navigable.

## Branch and pull request

Work on a feature branch and open a pull request for anything significant. The PR template
is the checklist; the important lines are the ones about scope and about the playlist
cache.

Keep a commit scoped to one change. Do not sweep up unrelated files that happened to be
dirty in the working tree.

## Directory conventions

- **Every directory carries a `README.md`** with a table mapping each subdirectory to its
  purpose. A new directory ships with one.
- **kebab-case** for all file and directory names.
- Playlists are named `YYYY-MM-DD-episode-title.csv`.
- Empty directories are held by `.gitkeep`. An empty directory with a confident README is
  worse than no directory — delete it.
- Superseded work moves to `discarded/`, in its own subdirectory with a `README.md` naming
  what replaced it and why. Update the table in `discarded/README.md`.

## Python

Python 3.11+, environments managed with [`uv`](https://docs.astral.sh/uv/). From
`tools/python/`:

```sh
make build      # rebuild the playlist cache
make verify     # assert the cache invariants
make check      # build + verify + assert a zero-line cache diff -- what CI runs
make lint       # ruff check
make test       # pytest
make all        # refresh Spinitron IDs, build, verify, regenerate missing-spins
```

Each package declares its dependencies in its own `pyproject.toml` and commits a
`uv.lock`. There is no `requirements.txt` and no `--with` incantation.

Add a test whenever you fix a bug in an override path, a parser heuristic, or a gate.
`tools/python/czcache/tests/` exists because three documented features shipped doing
nothing, and only an assertion about the wiring could tell the difference.

## The playlist cache

`shows/convergence-zone/playlists/cache/` is derived output that is committed. It is
reviewable in a pull request only because the build is idempotent: a rebuild that changes
nothing produces a zero-line diff. CI enforces this.

- Never hand-edit the cache. Change a source or an override and rebuild.
- `playlists/sources/` is read-only. Add a new export; never edit one in place.
- `tools/python/czcache/overrides/*.yaml` records human decisions. Never auto-approve a
  description; `proposed` becomes `approved` only when a person says so.
- `publication-links.json` holds WordPress post identity. Record real REST response values;
  never guess an ID.

## Secrets

Never commit `.env*`, `~/.czarchive.toml`, Spinitron API keys, Mixcloud client secrets or
OAuth tokens, or session cookies. `.gitignore` covers the common cases but is not a
substitute for reading `git status` before committing.

## Working with agents

`AGENTS.md` is the single source of agent guidance; `CLAUDE.md` and
`.github/copilot-instructions.md` are pointers at it. Path-scoped rules live in
`.github/instructions/`, repeatable procedures in `.github/skills/`, and Claude Code hooks
in `.claude/hooks/`. Edit `AGENTS.md`, not the pointers.
