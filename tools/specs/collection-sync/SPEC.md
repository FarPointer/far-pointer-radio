# Collection Sync Tool Specification

## Overview

**Tool Name:** `collection-sync`  
**Purpose:** Keep a personal music collection synchronized across a QNAP NAS, a shared Dropbox, and upstream acquisition sources (Bandcamp, Qobuz, label drops) — with safe agent-friendly controls and human-readable reporting at every step.  
**Owner:** Jim Causey  
**Status:** Specification (not yet implemented)

---

## Goals

- **Primary Goal:** Eliminate the manual work of getting newly-acquired music from Bandcamp, label drops, and other sources into the NAS collection and the shared Dropbox without duplicating effort or losing metadata.
- **Secondary Goals** (priority order):
  1. Keep the shared Dropbox (used by Jim and MichaelG for Convergence Zone) in two-way sync with the NAS.
  2. Sync audio tags across collections without re-uploading or re-downloading whole files.
  3. Auto-ingest label-sent media (Dropbox links, WeTransfer, etc.) into the canonical collection.
  4. Run anywhere — macOS, Linux, Windows — and offer a first-class QNAP deployment path (Docker or QNAP Container Station).
  5. Be fully usable by both humans at a terminal and coding agents operating autonomously.

### Non-Goals

- Streaming or playback — Logitech Media Server handles that; this tool only manages files and metadata.
- DRM circumvention — only files already in a downloadable/unprotected format are in scope.
- Managing purchases or subscriptions — the tool downloads from accounts, it does not purchase.
- Full database sync between LMS instances.
- Replacing a general-purpose backup tool — disaster recovery is out of scope.

---

## Architecture & Design

### System Boundaries

```
┌──────────────────────────────────────────────────────────────────┐
│                     Acquisition Sources                          │
│  ┌──────────────┐  ┌───────────┐  ┌────────────────────────┐   │
│  │  Bandcamp    │  │   Qobuz   │  │  Label drops           │   │
│  │  (API/scrape)│  │  (API)    │  │  (Dropbox / WeTransfer)│   │
│  └──────┬───────┘  └─────┬─────┘  └────────────┬───────────┘   │
└─────────┼────────────────┼─────────────────────┼───────────────┘
          │                │                     │
          ▼                ▼                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                    collection-sync                              │
│                                                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │  Acquirer   │  │   Packager   │  │  Sync Engine           │ │
│  │  (download, │  │  (unpack,    │  │  (rsync-style diff,    │ │
│  │   fetch)    │  │   rename,    │  │   tag propagation,     │ │
│  │             │  │   tag)       │  │   conflict resolution) │ │
│  └──────┬──────┘  └──────┬───────┘  └──────────┬─────────────┘ │
│         └────────────────┴─────────────────────┘               │
│                          │                                      │
│  ┌───────────────────────▼──────────────────────────────────┐   │
│  │  State DB  (SQLite — index, changelog, sync state)       │   │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ writes / reads
          ┌────────────────┴──────────────────┐
          ▼                                   ▼
┌──────────────────┐               ┌────────────────────┐
│  QNAP NAS        │  ←— rsync ——→ │  Shared Dropbox    │
│  (primary store) │               │  (Jim + MichaelG)  │
│  LMS-indexed     │               │  (label ingest)    │
└──────────────────┘               └────────────────────┘
```

### Key Components

| Component | Responsibility |
|-----------|----------------|
| **Acquirer** | Queries Bandcamp (fan API), Qobuz API, and label-drop sources to discover undownloaded items; downloads selected formats; handles auth tokens. |
| **Packager** | Unpacks archives, applies configurable naming templates (`{artist}/{year} - {album}/{track} - {title}.{ext}`), normalizes tags via a tag map. |
| **Sync Engine** | Computes diffs between NAS, Dropbox, and any staging areas; propagates new/changed files; propagates tag-only changes without re-transferring audio; resolves conflicts by configured policy. |
| **State DB** | SQLite database tracking every known album/track (path, hash, source, sync state, tag snapshot). Single source of truth for index and changelog. |
| **Reporter** | Reads State DB and produces human- and agent-readable output: status reports, dry-run previews, changelogs, and sync diffs — without mutating anything. |
| **Config Loader** | Loads and validates `collection-sync.yaml`; enforces agent-lock fields; surfaces misconfigurations at startup. |

### Data Flow

1. **Discover** — Acquirer fetches the Bandcamp fan collection (or other source) and compares against State DB; produces a list of items not yet downloaded.
2. **Download** — Acquirer downloads each item in the requested format(s) to a configurable staging area.
3. **Package** — Packager unpacks archives, renames files per template, writes/normalizes tags, and moves to the NAS collection directory.
4. **Index** — State DB is updated with file paths, checksums, tags, and source metadata.
5. **Diff** — Sync Engine computes which files exist on NAS but not Dropbox (and vice versa), and which have tag-only differences.
6. **Sync** — Files are transferred (NAS→Dropbox or Dropbox→NAS as configured). Tags are written to remote copies without re-transfer when only metadata changed.
7. **Ingest label drops** — Dropbox paths configured as `label_inbox` are scanned; new files are packaged and merged into the canonical collection.
8. **Report** — A changelog entry is appended to the State DB and a human-readable summary is written to `collection-sync.log`.

---

## Functional Specification

### Inputs

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `--config` | path | No | Path to config file (default: `~/.config/collection-sync/collection-sync.yaml`) | `--config /nas/music/.collection-sync.yaml` |
| `--source` | string | No | Override: which source to acquire from | `bandcamp`, `qobuz`, `label-inbox` |
| `--target` | string | No | Override: which target to sync to | `nas`, `dropbox`, `all` |
| `--format` | string | No | Audio format(s) to download (comma-separated) | `flac,mp3-v0` |
| `--dry-run` | flag | No | Report what would change without changing anything | |
| `--report` | flag | No | Print sync status without making changes | |
| `--json` | flag | No | Emit JSON to stdout for machine-readable summaries | `--json` |
| `--mode` | enum | No | `acquire`, `sync`, `tag-sync`, `ingest`, `all` | `--mode all` |
| `--since` | date | No | Limit acquisition to items added to source after this date | `2025-01-01` |
| `--album` | string | No | Acquire/sync a single album by URL or ID | |
| `--no-agent` | flag | No | Refuse to run if the process appears to be run by an agent (CI, automated) | |
| `--log-level` | enum | No | `debug`, `info`, `warn`, `error` | `--log-level info` |

### Outputs

| Output | Type | Condition | Description |
|--------|------|-----------|-------------|
| Exit code `0` | int | Always on clean run | No errors; dry-run or actual. |
| Exit code `1` | int | On any error | At least one operation failed; partial results may exist. |
| Exit code `2` | int | On config/auth error | Nothing was attempted. |
| Stdout | text/JSON | Always | Human-readable or `--json` structured summary of actions taken or planned. |
| `collection-sync.log` | append log | Always | Timestamped changelog of every action (or dry-run preview). |
| State DB | SQLite | After mutating runs | Updated index, checksums, tag snapshots, sync state. |
| `sync-report-YYYY-MM-DD.md` | Markdown | `--report` flag | Human- and agent-readable sync status snapshot. |

### Core Behaviors

#### Behavior 1: Bandcamp pending-download check
- **Trigger:** `--mode acquire --source bandcamp` or `--mode all`.
- **Actions:** Authenticate with Bandcamp fan API using stored token; fetch full fan collection; cross-reference with State DB; output list of items not yet downloaded.
- **Output:** Printed list (or JSON with `--json`); nothing is downloaded unless `--dry-run` is absent.
- **Idempotency:** Yes — discovering pending items does not change state.

#### Behavior 2: Bandcamp download and package
- **Trigger:** `--mode acquire` with items identified as pending.
- **Actions:** Download each album in the configured format(s); unpack archives to staging; apply naming template; normalize tags; move to NAS collection path; record in State DB.
- **Output:** Files appear in NAS collection; State DB updated; log entry appended.
- **Idempotency:** Yes — already-indexed items with matching checksums are skipped.

#### Behavior 3: NAS ↔ Dropbox sync
- **Trigger:** `--mode sync`.
- **Actions:** Compute diff between NAS collection root and Dropbox collection root (using cached checksums in State DB, not re-hashing every file); upload NAS-only files to Dropbox; download Dropbox-only files to NAS (new from MichaelG or labels); log all transfers.
- **Output:** Collections converge; State DB updated.
- **Idempotency:** Yes — identical files are skipped.

#### Behavior 4: Tag-only sync
- **Trigger:** `--mode tag-sync`.
- **Actions:** Compare tag snapshots in State DB against actual tags on NAS and Dropbox files; write updated tags to any copy that is out of sync; do not re-transfer audio data.
- **Output:** Tags are consistent across all copies; State DB tag snapshots updated.
- **Idempotency:** Yes.

#### Behavior 5: Label inbox ingest
- **Trigger:** `--mode ingest` or `--mode all`.
- **Actions:** Scan configured `label_inbox` paths in Dropbox (or local staging); for each new folder/file matching audio patterns, run Packager; merge into canonical NAS collection; sync result to Dropbox; update State DB.
- **Output:** Label drops become part of the canonical collection.
- **Idempotency:** Yes — already-ingested items (matched by checksum) are skipped.

#### Behavior 6: Dry run
- **Trigger:** `--dry-run` flag (any mode).
- **Actions:** Execute all discovery and diff logic; print every action that would be taken; write a dry-run section to the log. No files are moved, written, or deleted. No tags are written. State DB is not modified.
- **Output:** Report to stdout and log.
- **Idempotency:** Yes — by definition.

#### Behavior 7: Report
- **Trigger:** `--report` flag.
- **Actions:** Read State DB and current filesystem/Dropbox state; produce `sync-report-YYYY-MM-DD.md` with per-source counts, last-sync timestamps, pending items, and any detected drift. No mutations.
- **Output:** Markdown report file + summary to stdout.
- **Idempotency:** Yes.

### Agent Safety Controls

The config file supports an `agent_guard` section that an implementing agent must obey:

```yaml
agent_guard:
  # Refuse to run in any mode that writes files when set to true.
  read_only: false
  # Refuse to run without --dry-run when called from a non-interactive session.
  require_dry_run_in_ci: true
  # Modes the agent is never allowed to initiate (human must run them).
  locked_modes: []       # e.g. ["sync", "ingest"] to lock those modes
  # If true, any agent invocation exits 2 immediately.
  disable_agent_invocation: false
```

The tool detects agent invocation by inspecting environment variables (`CI`, `GITHUB_ACTIONS`, `COPILOT_CLI`, `NO_TTY`, etc.) and the presence of a TTY. When `require_dry_run_in_ci` is `true` and no TTY is detected, the tool will refuse to run without `--dry-run`.

### Per-Mode Automation Config

Each mode can be individually enabled or disabled for automated (scheduled) runs, independently of whether it is allowed for agents or humans at the terminal:

```yaml
automation:
  # Controls which modes run when the tool is invoked by a scheduler/cron.
  # Modes not listed here, or set to false, are skipped in automated runs.
  # A human running the tool interactively is unaffected by these flags.
  scheduled_modes:
    acquire: true        # Download pending Bandcamp albums nightly
    sync: true           # Sync NAS ↔ Dropbox nightly
    tag_sync: true       # Propagate tag changes
    ingest: true         # Process label inbox
  # Modes that require explicit human confirmation even when called interactively.
  # The tool will prompt before proceeding (cannot be bypassed with --yes in agent runs).
  confirm_modes:
    - ingest             # Label drops may need a human sanity-check before merge
  # When true, automated runs append a brief summary to a file agents can read.
  write_agent_summary: true
  agent_summary_path: ~/.local/share/collection-sync/last-run-summary.json
```

This lets you, for example, enable `acquire` and `sync` to run on a nightly schedule while leaving `ingest` (label drops) as human-only, without needing separate cron entries or wrapper scripts.

### Error Handling

| Error Scenario | Root Cause | Recovery Action | Exit Code |
|---|---|---|---|
| Missing or invalid config | Bad YAML or missing required field | Print config error with field name; no action taken | 2 |
| Bandcamp auth failure | Expired or missing token | Print auth error; instruct user to refresh token via `collection-sync auth bandcamp` | 2 |
| Download failure (network) | Transient network error | Retry up to `download.max_retries` times with backoff; log failure; continue with remaining items | 1 |
| Checksum mismatch after download | Corrupt download | Delete partial file; log warning; mark item as `download_failed` in State DB | 1 |
| Dropbox API error | Rate limit or auth | Back off and retry; log error; skip affected files for this run | 1 |
| Agent guard violation | Agent invocation blocked by config | Log reason; exit without any action | 2 |
| Conflict detected (file on both sides, different content) | Both NAS and Dropbox modified the same file | Apply `conflict_resolution` policy (see config); log both versions | 1 (if `manual`) |
| Staging disk full | Insufficient local space | Abort download; log error; suggest `--staging-path` override | 1 |

### Edge Cases

1. **Album available in multiple formats:** Download the first format in the configured `preferred_formats` list that is available. Record all available formats in State DB for future reference.
2. **File already exists with different checksum:** Do not overwrite. Log a conflict. If `conflict_resolution: newest`, compare mtime and keep the newer file. If `conflict_resolution: manual`, flag for human review.
3. **Label drop contains a non-audio file (PDF, artwork):** Package and preserve it alongside the audio under the same album directory. Do not discard.
4. **Bandcamp collection is very large (1000+ albums):** Page through the API response; do not load everything into memory. Progress is checkpointed in State DB so an interrupted run resumes.
5. **Dropbox path does not exist yet:** Create the target path before syncing; do not fail.
6. **NAS unreachable:** If the NAS mount is absent, abort immediately with a clear error. Do not proceed with Dropbox operations that assume NAS as authoritative.
7. **Duplicate album from two sources:** Identify by `{artist} + {album}` (normalized). Record both source entries; keep one canonical file set; note both sources in State DB.

---

## Implementation Details

### Dependencies

| Package / Service | Version | Why needed |
|---|---|---|
| Python | ≥ 3.11 | Implementation language |
| `httpx` | ≥ 0.27 | HTTP client for APIs (async-capable) |
| `bandcamp-downloader` | ≥ 0.10 | Wraps Bandcamp's undocumented fan collection JSON endpoints for discovery and download |
| `dropbox` SDK | ≥ 12 | Dropbox API access |
| `mutagen` | ≥ 1.47 | Audio tag reading and writing (FLAC, MP3, ALAC, AAC, OGG) |
| `SQLite3` | stdlib | State DB (no external DB required) |
| `rich` | ≥ 13 | Human-friendly terminal output, progress bars |
| `click` | ≥ 8 | CLI interface |
| `pydantic` | ≥ 2 | Config validation |
| `rclone` | ≥ 1.67 (external binary) | File transfer engine for NAS↔Dropbox sync; Dropbox backend, `--bwlimit` schedule, dry-run, filtering |
| `uv` | latest | Dependency management (consistent with repo tooling) |

### Configuration

```yaml
# collection-sync.yaml
# Credentials are never stored here — use environment variables or keyring.

collection:
  # Canonical root on the NAS (or local path on any platform)
  nas_root: /volume1/Music
  # Staging area for downloads before packaging
  staging_path: /volume1/Music/.staging
  # Naming template for packaged files
  naming:
    album_dir: "{artist}/{year} - {album}"
    track_file: "{track:02d} - {title}.{ext}"
    # Fallback when track number is absent
    track_file_no_number: "{title}.{ext}"
  # Formats to request from Bandcamp (in preference order)
  preferred_formats:
    - flac
    - aiff
    - mp3-v0

dropbox:
  # Root of the shared music collection in Dropbox
  collection_root: /Music/Convergence Zone Shared
  # Paths to scan for label-delivered media
  label_inbox:
    - /Music/Label Drops/Inbox
  # Whether to sync to Dropbox at all
  enabled: true

sources:
  bandcamp:
    enabled: true
    # Token loaded from BANDCAMP_TOKEN env var at runtime
    fan_id: null   # auto-discovered from token if null
  qobuz:
    enabled: false
    # Credentials from QOBUZ_APP_ID / QOBUZ_TOKEN env vars

sync:
  # Direction: nas_to_dropbox | dropbox_to_nas | bidirectional
  direction: bidirectional
  # Policy when the same file exists on both sides with different content
  conflict_resolution: manual   # newest | oldest | manual
  # Delete files from target that were deleted from source
  propagate_deletes: false      # default false — safe default
  # Only sync files matching these extensions
  audio_extensions:
    - flac
    - mp3
    - m4a
    - aiff
    - wav
    - ogg
  # Also sync artwork and liner notes
  companion_extensions:
    - jpg
    - png
    - pdf

tags:
  # Fields to sync across copies of the same file
  sync_fields:
    - title
    - artist
    - albumartist
    - album
    - year
    - tracknumber
    - genre
    - comment
  # Never overwrite these fields if already set
  protected_fields:
    - isrc

state:
  db_path: ~/.local/share/collection-sync/state.db
  log_path: ~/.local/share/collection-sync/collection-sync.log

agent_guard:
  read_only: false
  require_dry_run_in_ci: true
  locked_modes: []
  disable_agent_invocation: false

automation:
  scheduled_modes:
    acquire: true
    sync: true
    tag_sync: true
    ingest: false      # label drops require human review
  confirm_modes:
    - ingest
  write_agent_summary: true
  agent_summary_path: ~/.local/share/collection-sync/last-run-summary.json

# Bandwidth schedule — limits transfer rate by time of day.
# Useful on a residential connection (e.g. Comcast) where peak hours are congested.
# Times are in local wall-clock time (the machine's configured timezone).
# Rates accept rclone/rsync-style suffixes: K (KiB/s), M (MiB/s), 0 = unlimited.
bandwidth:
  schedule:
    - start: "00:00"
      end: "07:00"
      rate: "0"          # unlimited — overnight, off-peak
    - start: "07:00"
      end: "22:00"
      rate: "2M"         # ~2 MiB/s during the day (leaves headroom for other use)
    - start: "22:00"
      end: "24:00"
      rate: "0"          # unlimited — late evening
  # Hard cap regardless of schedule (set to 0 to disable)
  max_rate: "0"
  # Pause all transfers when a speed test or ping shows the connection is saturated
  congestion_backoff: true
```

### State & Persistence

#### Index format decision: our own SQLite, not LMS's database

LMS maintains a SQLite database (typically `squeezebox.db`) that indexes music files by path and embeds tag data. It is tempting to use this as the canonical index — the data is already there and LMS keeps it current.

However, we use our own independent SQLite State DB rather than piggy-backing on LMS for the following reasons:

| Factor | LMS database | Our State DB |
|---|---|---|
| **Portability** | Requires LMS to be running; LMS-specific schema that changes across versions | Plain SQLite, readable on any machine with Python and `sqlite3` |
| **Scope** | NAS only — no concept of Dropbox copies, source provenance, or sync state | Tracks NAS path, Dropbox path, checksums for both, source (Bandcamp/label/etc.) |
| **Write access** | LMS owns this DB; writing to it externally risks corruption and is unsupported | We own it; agents and humans can query and write safely |
| **Tag snapshots** | LMS stores tags at index time but does not track which copy is authoritative | We store tag snapshots per-copy to drive tag-sync without re-reading every file |
| **Changelog** | None | Append-only changelog suitable for human and agent review |
| **Cross-platform** | LMS may not be installed on macOS or Windows dev machines | Works anywhere Python runs |

**Decision:** The State DB is our own schema, independent of LMS. After a sync or ingest that lands new files on the NAS, the tool can optionally trigger an LMS library rescan via the LMS JSON-RPC API — but LMS remains a consumer of files, not a source of truth for our index.

#### State DB schema

| Table | Contents |
|-------|----------|
| `albums` | One row per album: `source`, `source_id`, `artist`, `album`, `year`, `nas_path`, `dropbox_path`, `formats_downloaded`, `ingest_date`, `last_synced` |
| `tracks` | One row per file: `album_id`, `path_nas`, `path_dropbox`, `checksum_nas`, `checksum_dropbox`, `tag_snapshot_json`, `last_seen` |
| `changelog` | Append-only log: `timestamp`, `mode`, `action`, `subject_path`, `detail`, `dry_run` |

Sync runs are idempotent because they compare checksums in `tracks` against the filesystem rather than re-hashing everything (checksums are refreshed only when mtime has changed).

Interrupted runs are resumable: any item in `albums` with `ingest_date IS NULL` and `formats_downloaded IS NULL` is treated as pending.

---

## Validation & Success Criteria

### Definition of Success

- ✅ Running `collection-sync --mode acquire --source bandcamp --dry-run` correctly lists all Bandcamp albums not yet present in the NAS collection without downloading anything.
- ✅ Running `collection-sync --mode acquire --source bandcamp` downloads and packages all pending albums, with correct directory naming and tags, and records them in the State DB.
- ✅ Running `collection-sync --mode sync` brings the Dropbox collection in sync with the NAS (bidirectional), and files added by MichaelG appear on the NAS.
- ✅ Running `collection-sync --mode tag-sync` writes updated tags to all copies of a file without re-uploading audio data.
- ✅ Running `collection-sync --report` produces a Markdown file with accurate counts and last-sync timestamps.
- ✅ Running any mutating command without `--dry-run` in a CI environment (no TTY, `CI=true`) when `require_dry_run_in_ci: true` exits with code 2 and makes no changes.
- ✅ Running `collection-sync --mode ingest` moves a label-drop folder from the Dropbox inbox into the canonical collection with correct naming and tags.
- ✅ The tool runs on macOS, Ubuntu Linux, and Windows without platform-specific workarounds required by the user.

### Acceptance Tests

```bash
# 1. Dry-run Bandcamp pending check
collection-sync --mode acquire --source bandcamp --dry-run
# Expected: list of pending albums; exit 0; no files written; DB unchanged

# 2. Acquire a single album
collection-sync --mode acquire --source bandcamp --album https://artist.bandcamp.com/album/title
# Expected: album downloaded, packaged under nas_root/{artist}/{year} - {album}/; DB updated

# 3. Sync NAS → Dropbox
collection-sync --mode sync --dry-run
# Expected: report of files to upload/download; exit 0; no changes made

# 4. Tag sync only
collection-sync --mode tag-sync --dry-run
# Expected: list of files with stale tags; exit 0; no tags written

# 5. Agent guard — CI environment
CI=true collection-sync --mode sync
# Expected: exit 2; message explains dry-run required in CI

# 6. Report generation
collection-sync --report
# Expected: sync-report-YYYY-MM-DD.md written; stdout summary printed; exit 0

# 7. Ingest label inbox
collection-sync --mode ingest --dry-run
# Expected: list of label-drop items that would be ingested; no changes

# 8. Idempotency
collection-sync --mode acquire --source bandcamp
collection-sync --mode acquire --source bandcamp
# Expected: second run is a no-op; log shows "0 new items"
```

---

## Deployment

### macOS / Linux (local)

```bash
cd tools/python/collection-sync
uv sync
uv run collection-sync --help
```

Store credentials in environment variables (e.g., via `direnv` or a `.env` file excluded from git):

```
BANDCAMP_TOKEN=...
DROPBOX_ACCESS_TOKEN=...
```

### QNAP (Docker / Container Station)

#### Dropbox sync approach: rclone, not QNAP Cloud Drive Sync

QNAP ships a built-in **Cloud Drive Sync** app that supports Dropbox. It is worth knowing it exists, but we deliberately do not use it as the primary sync mechanism for this tool. The reasons:

| Factor | QNAP Cloud Drive Sync | Our rclone-based approach |
|---|---|---|
| **Control** | GUI only; no scripting or dry-run | Full CLI control; `--dry-run`, `--filter`, bandwidth scheduling |
| **Selectivity** | Syncs entire Dropbox folders as configured in the GUI | Can sync any subset of paths, skip audio formats we don't want, filter by extension |
| **Agent visibility** | Opaque to scripts and agents | rclone output is parseable; state is in our State DB |
| **Conflict handling** | QNAP decides; not configurable | Our `conflict_resolution` policy applies |
| **Tag sync** | None | We propagate tag-only changes without re-upload |
| **Portability** | QNAP only | Same rclone commands run on macOS, Linux, Windows |
| **Bandwidth schedule** | None | rclone `--bwlimit` with time-of-day schedule |

**Decision:** Use [rclone](https://rclone.org/) (configured with the Dropbox backend) as the transfer engine inside the `collection-sync` Docker container. rclone handles the actual file movement; our Sync Engine drives it (computes what to transfer, calls rclone, interprets results, updates State DB). QNAP Cloud Drive Sync can still be used for other purposes (e.g. backing up NAS photos to Dropbox) but is not part of this tool's stack.

#### Container Station deployment

A `Dockerfile` and `docker-compose.yml` will be provided. The container:

- Mounts the NAS music volume at `/music` (read-write).
- Reads config from `/config/collection-sync.yaml` (a volume-mounted host path).
- Reads credentials from environment variables passed by docker-compose.
- Runs on a cron schedule configurable in `docker-compose.yml`.
- Exposes a `/reports` volume for generated Markdown reports.
- Includes `rclone` pre-installed and an `rclone.conf` volume mount for the Dropbox OAuth token.

```yaml
# docker-compose.yml sketch
services:
  collection-sync:
    image: ghcr.io/farpointer/collection-sync:latest
    volumes:
      - /volume1/Music:/music
      - /volume1/collection-sync/config:/config
      - /volume1/collection-sync/reports:/reports
      - /volume1/collection-sync/rclone:/root/.config/rclone   # rclone.conf lives here
    environment:
      - BANDCAMP_TOKEN
      - DROPBOX_ACCESS_TOKEN   # used for direct API calls (discovery, label inbox)
    # Run every night at 2 AM via Container Station scheduler
    # or set entrypoint to a cron wrapper
```

### Windows

Native Python install or WSL2. No platform-specific code paths required — all paths are handled via `pathlib`.

---

## Limitations & Future Work

### Known Limitations

- **Bandcamp API:** Bandcamp does not publish an official public API. The tool relies on the undocumented fan collection JSON endpoints (e.g. `bandcamp.com/api/fancollection/1/collection_items`) that are called by Bandcamp's own web UI, and on the [`bandcamp-downloader`](https://pypi.org/project/bandcamp-downloader/) PyPI package which wraps them. These endpoints are not guaranteed stable. Mitigation: abstract the Bandcamp client behind a narrow interface (`BandcampClient`) so the implementation can be swapped without touching the rest of the tool. Integration tests should flag breakage quickly.
- **Qobuz / Amazon Music:** These services have more restrictive APIs. Qobuz is feasible with an API key; Amazon Music is likely infeasible programmatically and may require manual export. Scope for v1 is Bandcamp only.
- **WeTransfer:** No persistent API for monitoring incoming transfers. Label drops via WeTransfer require manual download to the label inbox; the tool handles everything after that.
- **Dropbox delta:** Dropbox API v2 supports delta/longpoll, but an initial implementation can use full listings (e.g. `files/list_folder`) for simplicity. Large collections may be slow on first run; subsequent runs use the State DB cache.
- **LMS rescan:** After new files land on the NAS, LMS must be triggered to rescan. The tool can optionally call the LMS JSON-RPC API to trigger a library rescan, but this is not in v1 scope.

### Future Enhancements

- [ ] LMS rescan trigger after NAS sync
- [ ] Qobuz download support
- [ ] Webhook / watch mode — monitor Dropbox for changes and react in near-real-time instead of polling
- [ ] Web UI (read-only) for sync status visible on local network
- [ ] Notification on new label drops (email or pushover)
- [ ] Smart duplicate detection by acoustic fingerprint (AcoustID)
- [ ] Export collection to Beets library for advanced tagging workflows

---

## Examples & Use Cases

### Use Case 1: Weekly Bandcamp catch-up

**Scenario:** Jim has bought several albums over the past month and wants to get them all onto the NAS.

```bash
# See what's pending
collection-sync --mode acquire --source bandcamp --dry-run

# Download all pending in FLAC
collection-sync --mode acquire --source bandcamp

# Sync to Dropbox so MichaelG has access
collection-sync --mode sync
```

### Use Case 2: Pre-show prep — pulling MichaelG's additions

**Scenario:** Before a Tuesday show, Jim wants to make sure anything MichaelG added to the shared Dropbox is on the NAS and indexed in LMS.

```bash
collection-sync --mode sync --dry-run   # see what's new
collection-sync --mode sync              # pull it down
```

### Use Case 3: Label drop ingest

**Scenario:** A label sent a Dropbox folder link with three albums. Jim has already accepted the share and the folder is in the Dropbox `label_inbox`.

```bash
collection-sync --mode ingest --dry-run   # confirm what will be ingested
collection-sync --mode ingest             # ingest and sync
```

### Use Case 4: Sync status report for an agent

**Scenario:** An agent needs to know which albums are pending download before suggesting music for an episode.

```bash
collection-sync --report --json
# Outputs machine-readable JSON with pending counts, last sync time, and any drift
```

### Use Case 5: QNAP overnight scheduled run (Docker)

**Scenario:** Container Station runs the sync every night at 2 AM.

```bash
# Container entrypoint
collection-sync --mode all --log-level info
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Bandcamp changes undocumented API | Medium | High | Abstract client; monitor for breakage; fall back to browser-based manual download with tool picking up files from a watched folder |
| Accidental deletion propagated to Dropbox | Low | High | `propagate_deletes: false` by default; require explicit flag to enable |
| Credentials committed to git | Low | High | Credentials via env vars only; `.env` in `.gitignore`; secret-scan hook in `.claude/hooks/` |
| Large initial sync saturates NAS / Dropbox bandwidth (Comcast residential connection) | Medium | Medium | rclone `--bwlimit` with time-of-day schedule; configurable in `bandwidth.schedule`; defaults to unlimited overnight and ~2 MiB/s during the day |
| Conflict overwrites work by MichaelG | Low | Medium | `conflict_resolution: manual` default; conflicts logged and flagged, not auto-resolved |
| State DB corruption | Low | High | SQLite WAL mode; periodic backup of DB to a versioned path; DB can be rebuilt from filesystem scan |
| QNAP Docker image out of date | Medium | Low | Pin image versions; include update instructions in QNAP deployment docs |

---

## Appendices

### A. Related Tools & Systems

- **rclone:** The transfer engine used for NAS↔Dropbox sync. Chosen over QNAP Cloud Drive Sync for scriptability, bandwidth scheduling, dry-run support, and cross-platform portability. See the QNAP deployment section for the decision rationale.
- **Logitech Media Server (LMS):** Indexes the NAS music collection and serves it to Squeezebox and compatible players. `collection-sync` is upstream of LMS — it populates the files that LMS indexes.
- **Bandcamp:** Primary music acquisition source. Fan collection API used to discover purchased albums.
- **Dropbox:** Shared storage between Jim and MichaelG; also used by labels to deliver promotional music.
- **Convergence Zone playlist cache (`czcache`):** Reads the LMS-indexed collection to cross-reference played tracks. `collection-sync` keeps that collection current.
- **Beets (future):** Community music library tool; could be integrated as an optional tagging backend.
- **AcoustID / MusicBrainz:** Fingerprinting and metadata lookup; future integration for duplicate detection and tag enrichment.

### B. Glossary

- **NAS:** Network-Attached Storage — Jim's QNAP device, the primary authoritative music store.
- **Label drop:** A promotional album delivered by a record label, typically via a Dropbox share or WeTransfer link.
- **Label inbox:** A Dropbox path configured to receive label drops; `collection-sync ingest` processes it automatically.
- **Staging area:** A temporary local directory where files are downloaded and unpacked before being moved into the canonical collection.
- **Canonical collection:** The organized, tagged, named music library on the NAS, indexed by LMS.
- **Tag sync:** Propagating metadata (ID3/Vorbis tags) across all copies of a file without re-transferring audio.
- **Dry run:** An execution mode that computes and reports all planned changes without applying any of them.
- **Agent guard:** Configuration that restricts what an autonomous coding agent can do with this tool.
- **State DB:** The SQLite database that tracks every known album, track, checksum, tag snapshot, and sync event.

### C. References

- [Bandcamp fan API (unofficial)](https://bandcamp.com/api/fancollection/1/collection_items) — undocumented JSON endpoint used by Bandcamp's own web UI; wrapped by [`bandcamp-downloader`](https://pypi.org/project/bandcamp-downloader/) on PyPI
- [Dropbox Python SDK](https://github.com/dropbox/dropbox-sdk-python)
- [Mutagen audio tag library](https://mutagen.readthedocs.io/)
- [LMS JSON-RPC API](https://lms-community.github.io/lms-server-API/)
- [Beets music library tool](https://beets.io/)

### D. Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 0.1 | 2026-08-09 | Jim Causey | Initial spec template |
| 0.2 | 2026-08-09 | Jim Causey | Full spec completed |
| 0.3 | 2026-08-09 | Jim Causey | Fixed Bandcamp API reference; added per-mode automation config; added bandwidth schedule; rclone vs QNAP Cloud Drive Sync decision; LMS index format decision |

