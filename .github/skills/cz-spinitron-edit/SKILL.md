---
name: cz-spinitron-edit
description: Edit Spinitron playlist or show metadata via browser automation. Use when asked to "update show titles", "fix descriptions on Spinitron", "rename all playlists", "update a specific show", or "sync Spinitron from the cache".
---

# Editing Spinitron metadata

This skill drives Playwright MCP to make bulk or targeted changes to playlist and
show-level metadata on Spinitron's management interface. It covers two scopes:

| Scope | Spinitron page | Examples |
|---|---|---|
| **Playlist** | `spinitron.com/m/playlist/edit/<id>` (one per broadcast) | Rename playlists, update per-episode descriptions |
| **Show** | `spinitron.com/m/show/edit/<id>` (one record for the whole show) | Update the show's title, description, DJ listing |

The skill does not touch spins, song data, or DJ persona records.

## When to use this skill

Use it when:
- You want to make the same change to many playlists at once ("update all titles to
  `mm.dd.yyyy - DJ` format").
- You want to update the show-level description or title.
- You want to make a targeted change to one specific broadcast.

Do not use it to make changes you have not reviewed. The edit list is a human decision.
This skill is an executor, not a planner.

## Automation approach

**Playwright MCP** (Option A from PR #42). `.mcp.json` already configures
`@playwright/mcp@latest` — no new code is needed. An agent session uses the MCP browser
to log in, navigate, fill forms, and verify results with you watching.

If you find yourself running this skill more than a few times per month without
supervision, that is the signal to invest in Option B: a `czspinitron` Python CLI wrapping
Playwright Python for unattended execution. The credential and edit-list conventions below
are designed to be compatible with that future migration.

## Credential handling

Credentials live in `~/.czspinitron.toml`, **outside** this repository.

```toml
[spinitron]
username = ""
password = ""
```

The shape is documented in `tools/python/czarchive/czspinitron.toml.example` (committed,
no real values). The agent reads the file once at login, fills the form, then discards.
Credentials are never echoed, logged, or written into any repo file.

If `~/.czspinitron.toml` is absent: **stop immediately** and tell the user to create it.

Before first use, also verify `.gitignore` covers `.czspinitron.toml` — add it if
missing — before the dry-run begins.

## Defining the edit list

### Mode A — cache-driven (bulk)

Generate the edit list automatically from the checked-in cache:

```
shows/convergence-zone/playlists/cache/broadcasts/<YYYY-MM-DD>.json
```

For each broadcast file:
- Primary host = `participants[0].name` (first entry = primary host, per the overrides
  convention).
  - `MichaelG` or `Michael G` in the cache → display as **"Michael G"**.
  - `Jim Causey` → **"Jim Causey"**.
  - Anything else → stop and report; do not guess.
- Spinitron playlist ID(s) from
  `shows/convergence-zone/playlists/sources/spinitron/convergence-zone-playlists.json`.
- Target field values derived from the task description (title format, description text,
  etc.).

**Present the full derived edit list to the user before anything else.** Get explicit
approval. Do not begin the dry-run until the list is confirmed.

### Mode B — targeted (specific dates or show)

The user names the dates, IDs, or scope. Derive only those entries. Present for
confirmation before proceeding.

### Show-level edits

Navigate to `spinitron.com/m/show/edit/260646` (Convergence Zone show record). Same
dry-run gate, same safety stops, same confirmation requirement. Show-level changes affect
all future playlists' display — treat them as high-stakes.

## Pre-flight checklist

- [ ] `~/.czspinitron.toml` exists with non-empty `username` and `password`.
- [ ] `.gitignore` covers `.czspinitron.toml`.
- [ ] Edit list derived and **confirmed by the user**.
- [ ] Playwright MCP connected (harmless test: load `https://spinitron.com`, confirm page
  title visible).

## Dry-run (mandatory, fully read-only)

### Step 1 — login and target page
Navigate to the target page. Confirm expected landmarks (heading, table or form fields).
Complete login from `~/.czspinitron.toml` if a login wall appears. Re-confirm landmarks
after login.

### Step 2 — direct edit form access
Navigate directly to the known edit URL for the target item.
- Playlist edits: `/m/playlist/edit/<playlist-id>`
- Show edits: `/m/show/edit/<show-id>`

Use the page itself as the editability check; do not discover editability from the browse
page first. Confirm the captured source cues are present:
- Playlist page title: `Reopen Playlist`
- Playlist canonical path: `/m/playlist/edit/<id>`
- Playlist submit control label: `Submit`
- Show page title: `Edit show "<show name>"`
- Show canonical path: `/m/show/edit/<id>`
- Show submit control label: `Save`

Also confirm title input and description field are present. **Do not fill in or submit
anything.**

### Step 3 — pagination (optional browse-page check)
If the task starts from the browse page, pagination may still be tested as a separate
read-only confidence check. It is no longer part of the core editability path because the
skill loads edit pages directly by known ID.

### Step 4 — description field type
Read the current description field content on one example form. Determine whether it is
plain text or HTML — this governs how link syntax must be written.

### Step 5 — go/no-go
Report all four dry-run findings. Ask for explicit go-ahead. Do not proceed without it.

## Execution loop

For each item in the confirmed edit list:

1. Navigate to the edit form.
2. Confirm URL pattern and presence of title field. If wrong: **stop and explain**.
3. Clear and fill target fields with the approved values.
4. Submit the form using the correct control for the page type.
   - Playlist page → `Submit`
   - Show page → `Save`
   Wait for redirect or confirmation.
5. Confirm the updated value is visible. If not: **stop and explain**.
6. Log the result.
7. Rate-limit before the next item:
   - 3 s after each page load before any interaction.
   - 5 s after submitting before navigating away.
   - 2 s between any click and the next action.
   - Slow/error response (>10 s or any error page): pause 30 s, retry once. If retry
     fails: **stop and explain**.
   - One form at a time. No parallel requests, no multiple tabs.

## Logging

Session log at `~/.copilot/session-state/<session-id>/execution-log.md`:

| Object | Date / ID | Previous value | Target value | Submitted | Verified |
|---|---|---|---|---|---|

Log every attempted item, including read-only dry-run checks and any direct-edit page that
fails to load as expected.

## Safety boundaries

- Confirm URL and form on every edit before writing.
- Unrecognised page → **stop immediately and explain**.
- Post-submit verification failure → **stop immediately and explain**.
- Never touch spins, DJ persona records, or station settings.
- Never commit credentials, logs, or intermediate data to the repository.

## Do not

- Proceed past the dry-run without explicit human go-ahead.
- Infer host from anything other than the cache `participants` field.
- Guess a Spinitron ID — use the snapshot JSON.
- Parallelise or open multiple tabs.
- Fall back to browse-table discovery when the direct edit URL is known.
- Edit a date not in the confirmed edit list.
