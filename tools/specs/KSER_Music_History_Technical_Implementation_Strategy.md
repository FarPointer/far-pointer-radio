# KSER Music History Database

## Technical Implementation Strategy

**Purpose:** Build a maintainable, source-backed music-history database for KSER DJs and Convergence Zone show preparation, with strong Pacific Northwest filtering and generated daily and weekly research packets.

**Pacific Northwest scope:** Washington, Oregon, Idaho, and British Columbia.

## Goals

- Cover every calendar date, including February 29.
- Preserve births, deaths, releases, performances, chart milestones, band formations, awards, and other significant music events.
- Support filtering by city, state or province, metro area, artist, label, venue, studio, genre, era, and type of regional connection.
- Explain why each result is considered PNW-related.
- Retain citations, source assertions, confidence, and review status for every published fact.
- Build initial content without overloading upstream services.
- Refresh incrementally and produce reviewable pull requests.
- Run development and investigation tasks in GitHub Copilot Cloud where practical.
- Use GitHub Actions for deterministic scheduled refreshes and publishing.

## Architectural Approach

Use Python 3.11+, source-controlled JSONL records, and a generated SQLite database.


```text
source connectors
    -> cached raw responses
    -> normalized assertions
    -> identity and location reconciliation
    -> reviewed events
    -> SQLite database
    -> daily pages, weekly packets, JSON, DOCX, and PDF
```

GitHub Copilot Cloud is an ephemeral development and investigation environment. It should be used to implement connectors, resolve anomalies, review candidate records, and prepare pull requests. GitHub Actions should own recurring collection, validation, and publication.

## Proposed Repository Structure

```text
src/music_history/
  connectors/
  normalize/
  reconcile/
  publish/
  cli.py
config/
  sources.yml
  pnw.yml
data/
  events/MM/DD.jsonl
  entities/
  places/
migrations/
tests/
  fixtures/
  contracts/
reports/
.github/workflows/
```

JSONL files remain human-reviewable in Git. The generated SQLite database and document exports should be published as workflow or release artifacts rather than treated as the editable source of truth.

## Core Data Model

### Entities

Artists, people, groups, labels, venues, studios, festivals, releases, recordings, and works.

Recommended fields include:

- Internal stable identifier
- Entity type
- Canonical name and aliases
- Wikidata QID
- MusicBrainz MBID
- Discogs identifier
- External authority identifiers
- Genre and descriptive tags

### Places

- City
- State or province
- Country
- Latitude and longitude
- Metro area
- PNW inclusion flag
- Place authority identifiers

### Entity-to-Place Relationships

Geography must be modeled as a sourced, time-bounded relationship rather than a single hometown field.

Artist relationship types:

- Born in
- Formed in
- Based in
- Active in
- Member connection
- Recorded in
- Scene association

Label relationship types:

- Founded in
- Headquarters
- Branch office
- Distribution territory

Event relationship types:

- Venue
- Recording studio
- Festival
- Release territory
- Label location at the time of release

Each relationship should retain start and end dates, source assertions, confidence, and an explanatory note.

### Events and Assertions

An event represents the reconciled editorial fact. Assertions preserve what individual sources claim.

Event fields should include:

- Calendar month and day
- Event year and full date when known
- Date precision and uncertainty
- Category and event type
- Subject entities
- Place relationships
- Original editorial summary
- PNW relevance and explanation
- Review status
- Last verified timestamp

Assertion fields should include:

- Claimed value
- Source URL and publisher
- Source tier
- Retrieval timestamp
- License or usage classification
- Confidence
- Supporting quotation only when legally appropriate

Conflicting dates must remain visible as separate assertions until reviewed.

## Research Source Strategy

### Structured Foundation

- [Wikidata](https://www.wikidata.org/wiki/Wikidata:Data_access) for people, places, occupations, formation locations, birth dates, and death dates.
- [MusicBrainz](https://musicbrainz.org/doc/MusicBrainz_Database) for artists, releases, recordings, labels, events, relationships, and stable identifiers.
- [Discogs monthly dumps](https://data.discogs.com/) for releases, artists, labels, and master releases.
- [Wikimedia APIs](https://www.mediawiki.org/wiki/Wikimedia_APIs) for discovery and linked supporting material.
Wikidata and MusicBrainz core data are available under CC0; Discogs dumps are governed by Discogs’ Data Usage Policy (not CC0). MusicBrainz API clients must use a meaningful User-Agent and remain at or below one request per second.
Wikidata, MusicBrainz core data, and Discogs dumps are available under CC0. MusicBrainz API clients must use a meaningful User-Agent and remain at or below one request per second.

### Specialist and Archival Sources

- [setlist.fm API](https://api.setlist.fm/docs/1.0/index.html) for performances and venues.
- [Internet Archive metadata](https://archive.org/developers/metadata-schema/) for archived performances, broadcasts, and historical recordings.
- [Library of Congress APIs](https://www.loc.gov/apis/) for authority and collection records.
- Artist, label, venue, festival, chart, award, and institutional sites for authoritative corroboration.

### PNW Sources

- [Northwest Music Archives](https://nwmusicarchives.com/)
- [Northwest Digital Heritage](https://www.northwestdigitalheritage.org/)
- [University of Washington Libraries Digital Collections](https://content.lib.washington.edu/)
- University of Washington Special Collections and Ethnomusicology Archives
- [Northwest Folklife Archive](https://nwfolklife.org/archive/)
- [Archives West](https://archiveswest.orbiscascade.org/)
- Oregon Historical Society performing-arts collections
- BC Archives and MemoryBC
- Everett Public Library Northwest Room
- Other municipal, university, state, provincial, and community archives

### Editorial Corroboration

AllMusic, Pitchfork, Rolling Stone, NPR Music, BBC, Stereogum, NME, The Guardian, local publications, oral histories, and label catalogs can provide discovery and context.

Do not scrape or reproduce copyrighted editorial prose. Capture factual claims, source links, and independently written summaries. Sites without approved APIs should default to a manual research queue.

## Connector Contract

Every source connector should implement:

```python
probe()
estimate(plan)
fetch_page(cursor)
normalize(response)
checkpoint()
```

Connectors emit source assertions. They must not write directly into the published event tables.

## Responsible Network Access

All connectors should use one shared HTTP layer with:

- Per-host token-bucket throttling
- Per-source concurrency limits
- Meaningful User-Agent identification
- Retry-After support
- Exponential backoff with jitter for 429 and 503 responses
- ETag and Last-Modified conditional requests
- Persistent response caching
- Hard request, byte, and runtime budgets
- Resumable checkpoints
- Approved-domain allowlists
- Source terms and robots-policy documentation

Recommended defaults:

| Source | Default policy |
|---|---|
| MusicBrainz | Maximum one request per second and one concurrent request |
| Wikidata SPARQL | One query at a time; small paginated queries |
| Discogs | Prefer monthly dumps for bulk ingestion |
| Wikimedia APIs | Cached pagination with low concurrency |
| setlist.fm | Enforce API-key and response-header limits |
| Archives and editorial sites | Manual queue unless automated access is explicitly supported |

Each workflow must stop when its configured budget is exhausted. It should save a checkpoint and report an incomplete run rather than silently dropping records.

## Command-Line Operating Modes

```text
music-history doctor
music-history plan --mode backfill
music-history sample --date 08-26
music-history backfill --request-budget 500 --dry-run
music-history refresh --since-watermark
music-history validate
music-history publish
```

### Doctor

Tests DNS, TLS, firewall access, credentials, response schemas, cache writes, and one-record source probes. Produces `reports/source-health.json`.

### Plan

Estimates request counts, bytes, runtime, cache hits, and runner storage before a network-intensive operation.

### Sample

Processes one date or a small known entity set without persistent writes.

### Backfill

Builds initial content with explicit budgets, source checkpoints, and resume support.

### Refresh

Uses source watermarks, upstream revision information, and cache validators to retrieve only new or changed information.

### Validate

Runs schema, provenance, deduplication, geographic, licensing, and publication-readiness checks.

### Publish

Generates SQLite, daily pages, weekly packets, machine-readable JSON, and optional DOCX or PDF exports.

## GitHub Copilot Cloud Configuration

Add `.github/workflows/copilot-setup-steps.yml` to the default branch with a single `copilot-setup-steps` job.

The setup should:

- Use an Ubuntu x64 runner.
- Install the pinned Python toolchain and project dependencies.
- Restore test fixtures and development caches.
- Avoid performing live data backfills during agent startup.
- Use least-privilege `contents: read` permissions.

Configure Copilot's integrated firewall to allow only required domains, including MusicBrainz, Wikidata, Wikimedia, Discogs data, setlist.fm, Internet Archive, Library of Congress, and GitHub.

Secrets required by sources should be placed in the repository's restricted `copilot` environment. Public-source connectors should not require secrets unnecessarily.

## GitHub Actions Workflows

### `ci.yml`

- Unit tests
- Recorded connector contract tests
- Schema validation
- Golden-output comparisons
- No live external requests

### `source-smoke.yml`

- Manual and weekly execution
- Runs `doctor`
- At most one request per configured source
- Publishes source health, latency, schema, and authentication results

### `backfill.yml`

- Manual dispatch only
- Inputs for sources, date range, dry-run, runtime, and request budget
- Protected GitHub environment approval
- No concurrent jobs against the same source
- Checkpoint and resume support

### `refresh.yml`

- Scheduled and manually dispatchable
- Workflow concurrency prevents overlap
- Creates a branch and pull request containing data changes
- Includes request counts, cache hits, new candidates, changed assertions, and validation results
- Never writes directly to the default branch

### `publish.yml`

- Builds the SQLite database
- Generates general and PNW daily pages
- Generates KSER and Convergence Zone weekly packets
- Publishes generated artifacts or attaches them to a release

## Refresh Cadence

- **Daily:** recent deaths, corrections, and high-priority PNW candidates.
- **Weekly:** MusicBrainz and Wikidata changes plus the next 30 days of anniversaries.
- **Monthly:** Discogs-derived release updates and broader PNW enrichment.
- **Quarterly:** completeness, stale-source, duplicate, and geographic-coverage audits.

Stable historical facts should not be fetched repeatedly. Refresh changed upstream entities, low-confidence assertions, unavailable sources, and records approaching their publication date.

## Testing Strategy

### Unit Tests

- Date parsing and precision
- February 29 behavior
- Territory-specific release dates
- Entity and event deduplication
- PNW place classification
- Time-bounded entity-to-place relationships
- PNW relevance explanations

### Connector Contract Tests

Use recorded, sanitized HTTP responses for each connector. Validate schema changes without contacting live services during ordinary CI.

### Live Smoke Tests

Live tests must be opt-in and use no more than one request per source. They verify connectivity, authentication, headers, schema compatibility, and rate-limit handling.

### Integration Tests

Run the complete pipeline with synthetic fixtures, including conflicting dates, duplicate entities, unavailable sources, rate limiting, and interrupted runs.

### Golden Dataset

Use the downloaded seven-day KEXP document as the source material for **KSER-week-pilot**. Its 193 entries provide a stable expected dataset for import, reconciliation, geographic enrichment, and generated-document comparisons.

### Budget and Resilience Tests

- Fail a run that exceeds configured requests or concurrency.
- Simulate 429, 503, timeout, and malformed-response conditions.
- Interrupt and resume without duplicate assertions.
- Verify that partial runs are clearly marked incomplete.

### Publication Quality Gates

Every published event must have:

- A valid calendar date or explicit uncertainty
- At least one acceptable source
- A resolved subject identity or documented unresolved state
- No unresolved duplicate
- Original editorial wording
- Review status

Every PNW result must also have:

- A normalized place
- A relationship type
- A source
- A human-readable regional relevance explanation

## Generated Outputs

- General daily music-history page
- PNW-only daily page for KSER
- KSER weekly DJ preparation packet
- Convergence Zone packet with upcoming anniversaries, regional explanations, source links, and potential tracks
- City, label, venue, studio, and scene spotlights
- SQLite database and JSON API payloads
- Optional DOCX and PDF exports

## Delivery Phases

| Phase | Exit gate |
|---|---|
| Source-access spike | Every priority source passes `doctor`; limits, terms, and estimated costs are documented |
| KSER-week-pilot | The 193 source entries are imported, cited, reconciled, PNW-enriched, and published |
| PNW enrichment | KSER filters and Convergence Zone packet are validated by representative DJ workflows |
| Calendar backfill | All 366 dates are populated through resumable, budgeted processing |
| Scheduled refresh | Automated refresh pull requests run without overlapping or exceeding budgets |
| Production publishing | Versioned SQLite and daily or weekly outputs are generated reliably |

Large MusicBrainz or Discogs imports are the primary runner-capacity risk. Benchmark a representative sample before downloading a complete dump. If estimated disk or runtime exceeds a standard GitHub-hosted runner, use a larger runner for the import and retain only a compact normalized snapshot.

## Recommended Next Steps

1. Create a dedicated repository and choose its visibility and license.
2. Scaffold the Python package, schemas, migrations, CLI, and test harness.
3. Implement `doctor` and the shared rate-limited HTTP/cache layer before building source connectors.
4. Add read-only probes for Wikidata, MusicBrainz, Discogs data, Wikimedia, setlist.fm, Internet Archive, and Library of Congress.
5. Run `doctor` and a one-date sample in GitHub Actions to verify firewall and credential behavior.
6. Import the seven-day KEXP source into **KSER-week-pilot** fixtures.
7. Implement the normalized entity, place, entity-place, event, assertion, and review schemas.
8. Generate the first general, PNW-only, KSER, and Convergence Zone outputs from fixtures.
9. Review regional classifications and DJ usability before any broad data acquisition.
10. Run a dry-run backfill plan to estimate network requests, storage, runtime, and expected record counts.
11. Approve and execute a bounded one-month backfill before expanding to all 366 dates.
12. Enable scheduled refreshes only after the one-month run is reproducible and produces reviewable pull requests.
