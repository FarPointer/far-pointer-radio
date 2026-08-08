<!-- Keep this short. Delete any section that does not apply. -->

## What this changes

<!-- One or two sentences. Link the issue or the decision doc if there is one. -->

## Checklist

- [ ] Scoped to this change — no unrelated files swept in
- [ ] Directory `README.md` updated (or none needed)
- [ ] `AGENTS.md` updated if a working rule or convention changed

### Playlist data

- [ ] Sources touched: <!-- Spinitron export / MichaelG workbook / OneNote / czfm / none -->
- [ ] `make check` passes — cache rebuilt, `verify.py` green, zero-line cache diff
- [ ] Overrides changed: <!-- descriptions / participants / repeats / spins / none -->
      Every override edit records a **human** decision, not an inference
- [ ] `publication-links.json` entries come from real REST responses, not guessed IDs

### Tooling

- [ ] `make lint` and `make test` pass
- [ ] A regression test covers any bug fixed in an override path, parser heuristic, or gate

### Safety

- [ ] No secrets: no `.env*`, `~/.czarchive.toml`, API keys, OAuth tokens, or cookies
- [ ] Superseded work moved to `discarded/` with a `README.md` explaining why
