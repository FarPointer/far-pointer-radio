# Spinitron Browser Automation — Options

**Date:** August 2026
**Issue:** [#41](https://github.com/FarPointer/far-pointer-radio/issues/41)
**Status:** Research complete; no option chosen yet

---

## Background

KSER does not give individual DJs Spinitron API keys, so every Spinitron
change — updating show metadata, creating playlists, logging spins — requires
manually navigating the web interface.  The tasks that accumulate toil:

| Task | Current effort |
|---|---|
| Create a new playlist before a show | Manual: log in, create, set title and time |
| Log spins during or after a show | Manual: search each track, click Add Spin |
| Update show description or image | Manual: Settings → Show, edit form, Save |
| Backfill old playlists | Manual: one playlist at a time |

Since Spinitron has no DJ-level API, the only automation path is the browser
interface — either driven by an agent (Playwright MCP) or by a script (Playwright
Python library or `requests` form posts).

---

## What Spinitron's web interface looks like

Spinitron's DJ interface lives at `https://spinitron.com/m/KSER/` (or the
equivalent DJ login at `https://spinitron.com/m/`).  After a standard
username/password login it exposes:

- **Playlists**: create/edit/delete; add spins one at a time or via bulk import
- **Spins**: each spin has artist, song, release, label, and a time
- **Show settings**: title, description, image, time slot

Forms are standard HTML (`<form method="POST">`); there is no single-page
JavaScript-heavy framework that would require special handling.  Sessions are
cookie-based.  CSRF tokens (`_token`) are present on most write forms — any
automation must read the current token before submitting.

---

## Option A — Playwright MCP (agent-driven, no new code)

This is already wired up.  `.mcp.json` configures `@playwright/mcp@latest`, so
any agent session that has the MCP server available can ask Copilot (or any
MCP-aware agent) to:

> "Log into Spinitron at spinitron.com as {username}, open Playlists, and add
> the following 30 tracks to tonight's show."

The agent uses the Playwright MCP tools (`browser_navigate`, `browser_click`,
`browser_fill_form`, etc.) and can visually verify each step via
`browser_snapshot`.

**Pros**

- Zero new code — it works today in an interactive Copilot session.
- The agent can pause and ask about anything ambiguous.
- Visual verification (`browser_snapshot`, `browser_take_screenshot`) closes the
  loop.
- Credentials never touch the repository; the agent asks for them once per
  session or reads from the environment.

**Cons**

- Not scriptable — requires an agent session for every run.
- Slow if there are many spins (agent tool-call per action).
- Unattended / scheduled execution is not possible without infrastructure to
  launch and supervise an agent session.

**Verdict:** Best choice for occasional one-off tasks (backfills, show-settings
updates, short playlists) where interactive oversight is fine.

---

## Option B — Python Playwright automation script (`czspintron`)

A new package `tools/python/czspintron/` wrapping the `playwright` Python library
(sync API) could expose a CLI:

```sh
uv run czspintron create-playlist --date 2026-08-12 --title "Convergence Zone"
uv run czspintron add-spins --date 2026-08-12 --csv path/to/spins.csv
uv run czspintron update-show --description "This week on Convergence Zone …"
```

Internally it would:

1. Launch a headless Chromium browser.
2. Navigate to `https://spinitron.com/m/`, fill the login form, submit.
3. Parse the resulting page and verify login succeeded.
4. Perform the requested action (navigate to the relevant form, fill in values
   extracted from the input file or arguments, extract the CSRF token, submit).
5. Screenshot on error for diagnostics.
6. Close the browser.

Credentials would live in `~/.czarchive.toml` (reusing the existing config file)
or a new `~/.czspintron.toml`.

**Pros**

- Fully scriptable; can be run from cron or a GitHub Actions workflow on a
  self-hosted runner.
- Fast: headless browser, no human in the loop.
- Integrates naturally with the existing `czarchive` workflow (e.g. auto-create a
  playlist right after download).
- The `playwright` Python library is well-maintained and already available in the
  ecosystem the project uses.

**Cons**

- New code to write and maintain (~200–400 lines for a minimal first version).
- Spinitron's HTML structure could change; selectors would need updating.
- Headless Chromium is a heavier dependency than a pure-requests approach
  (but `playwright install chromium` is a one-line setup).
- Must handle session expiry and CSRF token rotation.

**Verdict:** Best choice if unattended or frequent runs are needed (e.g. logging
spins from a CSV produced by `czarchive download`).

---

## Option C — `requests` + form posts (no browser)

Spinitron's admin forms are plain HTML so a `requests.Session` could replicate
what the browser does: GET the form page to extract the CSRF token, then POST
the form data.  No Playwright, no browser binary.

**Pros**

- No browser binary; very fast.
- Works anywhere `requests` works.

**Cons**

- CSRF token extraction from raw HTML is fragile (no JavaScript rendering, but
  the token shape could change).
- Any future migration to a JavaScript-heavy form (common on Rails/Turbo stacks)
  would break this silently.
- Debugging failures is harder — no screenshot, no DOM snapshot.
- Essentially reimplements what Playwright gives for free.

**Verdict:** Lower resilience for no real advantage over Option B.  Not
recommended.

---

## Recommendation

Start with **Option A** for the immediate backlog: use the Playwright MCP server
in an agent session to handle one-off tasks (e.g. backfilling playlists, updating
show metadata).  The infrastucture is already present and no code needs to land.

Invest in **Option B** (`czspintron` package) if and when the volume of spin
logging makes interactive sessions impractical — for example once `czarchive` is
reliably producing a CSV after each show.  At that point a ~300-line Python
module and one new section in `~/.czarchive.toml` would close the loop entirely.

---

## Decided against

| Approach | Reason |
|---|---|
| Spinitron REST API | Station does not provide a DJ-level API key |
| Selenium | Playwright supersedes it; no advantage here |
| RSS/iCal feed injection | Spinitron does not expose a writable feed endpoint |

---

## If you proceed with Option B — starter scope

A minimum `czspintron` MVP would need:

1. `login(username, password)` — authenticate and return a live session.
2. `create_playlist(show_date, title, start, end)` — create an empty playlist.
3. `add_spin(playlist_id, artist, song, album, spin_time)` — add one spin.
4. `add_spins_from_csv(playlist_id, path)` — bulk-add from a CSV file.
5. `update_show_description(show_id, description)` — update the show bio.

Each function would be wired to a `click` CLI command, matching the style of
`czarchive`.  Tests would use `playwright`'s `page.route()` to mock the
Spinitron responses and avoid hitting the live site in CI.
