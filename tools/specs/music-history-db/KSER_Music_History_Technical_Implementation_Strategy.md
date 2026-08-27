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

Wikidata structured data, MusicBrainz core data, and Discogs monthly dumps are
available under CC0. That statement does not extend to MusicBrainz supplementary
data, non-Wikidata content retrieved through Wikimedia APIs, or Discogs Restricted Data.
MusicBrainz API clients must use a meaningful User-Agent and remain at or below one
request per second. The source-specific boundaries are defined below.

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

## Source Licensing and Redistribution Policy

This policy was checked against the linked official source terms on **2026-08-27**.
Terms can change, and an API is a delivery mechanism rather than a license. Recheck
the terms at the source-access exit gate and before enabling a new field, endpoint,
collection, or publication use.

“Raw” means an unmodified dump, API response, web page, document, image, audio file,
or other source object. A “normalized fact” is a factual assertion expressed in the
project’s own schema and wording, with provenance and a license or usage
classification. Extracting facts does not override contract terms, database rights,
privacy rights, or copyright in the source’s selection or expression.

### Material-handling profiles

| Profile | Acquisition | Raw retention | Normalized facts | Quotations | Public repository | Generated artifacts |
|---|---|---|---|---|---|---|
| **CC0** | Use the named official API or dump and obey its access rules. | Raw data may be retained privately. Bulk raw data stays out of Git as a project policy. | May be stored with source URL, retrieval date, and `CC0-1.0`; use original editorial wording. | Avoid unnecessary source prose; material within the defined CC0 scope may be quoted. | Normalized facts and provenance may be committed; bulk raw data may not. | Normalized facts may be redistributed. Attribution is encouraged even when CC0 does not require it. |
| **ITEM** | Use only an approved API, download, or ordinary manual access. Check the license or rights statement for each item or collection. | Keep the minimum raw material privately only when its terms permit; record any retention limit. | Factual assertions in original wording may be stored with the item-level rights classification. | Only under the recorded open license, permission, or a documented legal exception; keep the quotation no longer than needed and attribute it. | Commit facts, citations, and rights metadata. Commit source content only when its license permits repository redistribution and all attribution/share-alike duties are met. | Publish facts and citations. Publish source content only when the item-level license or permission covers the artifact and its distribution. |
| **RESEARCH** | Manual research only; do not scrape, crawl, or bulk-extract. | Retain only private research notes and the minimum source excerpt allowed by the terms; never retain credentials or personal data. | Store only discrete facts in original wording after human review, with a citation; do not reproduce the source’s compilation or expression. | Only with permission or a documented legal exception, with attribution. | Do not commit raw responses, documents, media, or copied prose. Reviewed facts and citations may be committed. | Redistribute only reviewed facts, citations, and original summaries; no source media or prose. |
| **BLOCKED** | A terms-compliant `doctor` probe may test access, but production acquisition is disabled. | No production raw retention. | No source-derived assertion enters the durable store. | None. | None. | None until a new licensing decision is recorded. |

Private retention is not a fallback license. If a source forbids storage, imposes a
time limit, or requires deletion, those terms override the general profile. Every
connector must keep the source and field classifications separate so that restricted
content cannot inherit a more permissive license from another source.

### Structured, API, and institutional sources

| Source and verified terms | Planned material | Profile and decision |
|---|---|---|
| [Wikidata licensing](https://www.wikidata.org/wiki/Wikidata:Licensing) | Structured data in Wikidata’s main and property namespaces is CC0. | **CC0 — GO.** |
| [MusicBrainz data license](https://musicbrainz.org/doc/About/Data_License) | Core data is CC0; supplementary data is CC BY-NC-SA 3.0. | **CC0 — GO for an allowlist of core fields only. BLOCKED for supplementary fields** until their attribution, noncommercial, and share-alike requirements are approved for the intended outputs. |
| [Discogs monthly dumps](https://data.discogs.com/) and [API Terms of Use](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use) | The dump site labels the monthly XML dumps CC0, and the API terms define release, artist, and label catalog metadata as CC0 Data. | **CC0 — GO for monthly dumps only**, subject to the Discogs decision below. |
| [Discogs API Terms of Use](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use) | The live API mixes CC0 Data with non-transferable Restricted Data such as user, marketplace, and image content. Its terms also impose freshness, storage, and public attribution rules. | **BLOCKED for ingestion and publication.** Use the dumps instead. A future live-API connector requires a separate field-level decision. |
| [Wikimedia API licensing](https://www.mediawiki.org/wiki/API:Licensing) | API content retains the license shown by its source wiki or item; Wikipedia text is generally CC BY-SA, while Commons media licenses vary. | **ITEM — GO for discovery.** Do not ingest text or media without recording and satisfying its specific license. |
| [setlist.fm API](https://api.setlist.fm/docs/1.0/index.html) and [terms](https://www.setlist.fm/help/terms) | Free API use is limited to noncommercial projects; public use requires attribution and data is supplied “as is.” No blanket license for durable normalized redistribution is stated. | **BLOCKED for durable ingestion and publication** unless setlist.fm gives permission covering the project’s storage and outputs. |
| [Internet Archive terms](https://archive.org/about/terms.php) | Some metadata is designated CC0; uploaded items and other metadata can carry item- or collection-specific rights. | **ITEM — GO only when the record’s license is captured.** Media is never assumed to share its metadata’s license. |
| [Library of Congress APIs](https://www.loc.gov/apis/) and [legal notices](https://www.loc.gov/legal/) | API access is public, but collection items and some third-party material have source-specific rights and restrictions. | **ITEM — GO only after checking the record’s rights fields and linked restrictions.** |

Artist, label, venue, festival, chart, award, and other institutional sites do
not form one licensed dataset. Each is **RESEARCH** until it has its own ledger
entry with an official terms URL, allowed acquisition method, and rights
classification. This applies separately to artist sites, label sites and catalogs,
venue sites, festival sites, chart sites, award sites, and institutional sites.

### Pacific Northwest sources

None of the planned regional sources grants a verified blanket license over all
of its holdings. Aggregators do not grant rights held by their contributors.

| Source and verified terms | Profile and decision |
|---|---|
| [Northwest Music Archives](https://nwmusicarchives.com/contact-us/) | **RESEARCH.** No blanket reuse license is stated on the official site. |
| [Northwest Digital Heritage policies](https://www.northwestdigitalheritage.org/s/nwdh/page/policies) | **ITEM.** Follow the contributing institution’s item-level rights statement. |
| [University of Washington Digital Collections use terms](https://content.lib.washington.edu/ordering.html) | **ITEM.** Check each item and obtain any permission required for publication. |
| [University of Washington Special Collections rights](https://www.lib.washington.edu/specialcollections/services/photoduplication/rights) | **ITEM.** Reproduction access is not a blanket publication license. |
| [University of Washington Ethnomusicology Archives](https://guides.lib.uw.edu/research/ethnomusicology/archives) | **ITEM.** Collection and donor restrictions require item-level review. |
| [Northwest Folklife Archive](https://nwfolklife.org/archive/) | **RESEARCH.** The archive page states no blanket reuse license; obtain a rights decision for each item. |
| [Archives West copyright guidance](https://www.orbiscascade.org/programs/osdc/archives-and-manuscripts-collections/ead/copyright-in-finding-aids/) | **ITEM.** Finding-aid licenses and collection rights vary by contributing institution. |
| [Oregon Historical Society collection use](https://www.ohs.org/research-and-library/about-the-library/using-ohs-research-library-collections.cfm) | **ITEM.** Researchers must resolve copyright and other restrictions for the intended use. |
| [BC Archives reproduction terms](https://bcarchives.ca/reproductions/) | **ITEM.** Copyright, donor, and other restrictions are item-specific; obtain authorization when required. |
| [MemoryBC](https://www.memorybc.ca/about) | **ITEM.** It is an aggregator; rights remain source- and repository-specific. |
| [Everett Public Library digital collections](https://cdm16742.contentdm.oclc.org/digital/custom/collection/p16742coll1/id/20) | **ITEM.** Research access does not establish blanket publication rights; check the item and partner institution. |
| Other municipal, university, state, provincial, or community archives | **BLOCKED for automation; RESEARCH manually.** Name the source and record its official rights policy before retaining or publishing material. |

### Editorial and pilot sources

The reviewed terms for [AllMusic](https://www.allmusic.com/copyright-policy),
[Pitchfork](https://pitchfork.com/legal/terms/),
[Rolling Stone](https://www.rollingstone.com/legal/),
[NPR](https://www.npr.org/about-npr/179876898/terms-of-use),
[BBC](https://www.bbc.com/usingthebbc/terms/),
[Stereogum](https://www.stereogum.com/terms/),
[NME](https://www.nme.com/terms-conditions), and
[The Guardian](https://www.theguardian.com/help/terms-of-service) do not provide
a blanket license to republish their editorial content. Each source is
**RESEARCH**: use it for manual discovery and discrete factual corroboration,
write an original summary, and do not commit or redistribute its articles,
reviews, ratings, images, or audio. The same profile applies to local
publications. Oral histories are **ITEM** and require the recording’s rights and
consent terms; label catalogs are **RESEARCH** unless a specific catalog carries
an approved open license.

The downloaded KEXP pilot documents have no recorded redistribution license.
Their existing presence in this planning repository does not establish one.
Treat them as **RESEARCH**: do not copy them into the implementation repository
or generated artifacts, do not quote them, and independently verify their
candidate facts before committing normalized assertions.

### Discogs go/no-go decision

**GO** for acquisition, private raw retention, normalization, repository
inclusion, and publication using the **monthly CC0 dumps only**:

- acquire only the official artist, label, master, and release dump files;
- keep raw compressed/XML dumps in private working storage, not Git;
- tag every assertion with the dump month, Discogs identifier, source URL, and
  `CC0-1.0`;
- commit and redistribute normalized catalog facts and independently written
  summaries; and
- credit Discogs and link to the source record as a project convention, even
  though CC0 does not require attribution.

**NO-GO** for user data, marketplace data, images, or any unclassified content,
and for using the live API as an ingestion or publication source. The API terms
require content displayed from the API to be no more than six hours older than
Discogs, prohibit caching or storage longer than necessary to provide the
application service, restrict transfer and commercial use of Restricted Data,
and require prescribed notices and a followed link beside public API data.
These obligations are incompatible with the proposed durable, redistributable
history database. Any future API use must be approved as a separate design and
must not be mixed with dump provenance.

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
- Source-specific response caching, retention, and deletion limits
- Hard request, byte, and runtime budgets
- Resumable checkpoints
- Approved-domain allowlists
- Source terms and robots-policy documentation

Recommended defaults:

| Source | Default policy |
|---|---|
| MusicBrainz | Maximum one request per second and one concurrent request |
| Wikidata SPARQL | One query at a time; small paginated queries |
| Discogs | Monthly CC0 dumps only; live API ingestion disabled |
| Wikimedia APIs | Cached pagination with low concurrency |
| setlist.fm | Access probe only; durable ingestion disabled pending permission |
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
Ensure `.github/workflows/copilot-setup-steps.yml` exists on the default branch with a single `copilot-setup-steps` job (this repository already includes this workflow; extend it as needed for music-history work).
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
- **Monthly:** CC0 Discogs-dump release updates and broader PNW enrichment.
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

Use the downloaded seven-day KEXP document as discovery-only input for **KSER-week-pilot**. Its 193 entries provide stable candidates for import and reconciliation. Independently source and clear each fact before geographic enrichment or generated-document comparisons, and do not copy KEXP wording into golden outputs.

### Budget and Resilience Tests

- Fail a run that exceeds configured requests or concurrency.
- Simulate 429, 503, timeout, and malformed-response conditions.
- Interrupt and resume without duplicate assertions.
- Verify that partial runs are clearly marked incomplete.

### Source-Access Licensing Exit Gate

Before production acquisition is enabled, every source must have a reviewed ledger
entry that records:

- the official terms or license URL and the date it was checked;
- the exact delivery channel, endpoint, collection, and field allowlist;
- an explicit GO or NO-GO for acquisition and publication;
- raw-retention location, time limit, and deletion rule;
- the license or usage classification for normalized facts;
- the permitted quotation basis and required attribution;
- what may enter Git and each generated artifact; and
- any noncommercial, share-alike, privacy, or downstream redistribution constraint.

`doctor` must fail closed when this entry is absent, more than 90 days old, known to
have changed, or inconsistent with the connector configuration. Contract tests must
prove that blocked fields cannot enter raw caches, normalized assertions, Git
fixtures, or generated outputs. A successful network probe alone never authorizes
ingestion.

### Publication Quality Gates

Every published event must have:

- A valid calendar date or explicit uncertainty
- At least one acceptable source
- A current license or usage classification permitting the generated artifact
- A resolved subject identity or documented unresolved state
- No unresolved duplicate
- Original editorial wording
- A documented permission, open license, or legal-exception basis for every quotation
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
| Source-access spike | Every priority source has an explicit GO/NO-GO; each GO source passes `doctor` and the licensing exit gate; limits, terms, and estimated costs are documented |
| KSER-week-pilot | The 193 candidates are imported and reconciled; only independently verified, licensing-cleared facts are PNW-enriched and published |
| PNW enrichment | KSER filters and Convergence Zone packet are validated by representative DJ workflows |
| Calendar backfill | All 366 dates are populated through resumable, budgeted processing |
| Scheduled refresh | Automated refresh pull requests run without overlapping or exceeding budgets |
| Production publishing | Versioned SQLite and daily or weekly outputs are generated reliably |

Large MusicBrainz or Discogs imports are the primary runner-capacity risk. Benchmark a representative sample before downloading a complete dump. If estimated disk or runtime exceeds a standard GitHub-hosted runner, use a larger runner for the import and retain only a compact normalized snapshot.

## Recommended Next Steps

1. Create a dedicated repository and choose its visibility and license.
2. Scaffold the Python package, schemas, migrations, CLI, and test harness.
3. Implement `doctor` and the shared rate-limited HTTP/cache layer before building source connectors.
4. Add read-only probes for Wikidata, MusicBrainz, Discogs monthly-dump access, Wikimedia, setlist.fm, Internet Archive, and Library of Congress; probes must not bypass a source’s NO-GO.
5. Run `doctor` and a one-date sample in GitHub Actions to verify firewall and credential behavior.
6. Import the seven-day KEXP source into research-only **KSER-week-pilot** candidate fixtures; do not publish from it directly.
7. Implement the normalized entity, place, entity-place, event, assertion, and review schemas.
8. Generate the first general, PNW-only, KSER, and Convergence Zone outputs from fixtures.
9. Review regional classifications and DJ usability before any broad data acquisition.
10. Run a dry-run backfill plan to estimate network requests, storage, runtime, and expected record counts.
11. Approve and execute a bounded one-month backfill before expanding to all 366 dates.
12. Enable scheduled refreshes only after the one-month run is reproducible and produces reviewable pull requests.
