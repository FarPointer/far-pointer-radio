# Convergence Zone Playlist Cache — Schema Rationale

## Purpose

This is the canonical data store for Convergence Zone broadcasts and the songs
played on them. It's derived from Spinitron when Spinitron is accurate and
useful, and from other sources (Michael G's manual spreadsheets, OneNote,
WordPress) when they're more accurate or contain information Spinitron
doesn't capture. It is not a mirror of any single source — it's the repo's own
model of what actually happened on air.

Where the evidence only supports what was *intended* to air — as it does for
the episodes predating Spinitron logging — the record says so rather than
quietly presenting a plan as history. See `evidence` below.

`tools/python/czcache/` builds the cache from every source in one command, and
is the implementation of the decisions in this document. Findings recorded here
that were originally measured by hand are now enforced by its `verify.py`.

## Sources and what each one is good for

| Source | Coverage | Unique value | Known weaknesses |
|---|---|---|---|
| Spinitron CSV export | 164 broadcasts, 3,282 spins (May 2023 – Jul 2026) | Timestamps, ISRC (~91%), UPC (~87%), duration, label, DJ-set local flag, DJ ID, ISO air datetime per playlist | Year-only release dates; playlist ID not exposed in export; episode number effectively absent (96% of spins carry the bare title "Convergence Zone") |
| Michael G's spreadsheets | 28 broadcasts, 661 spins (Apr 2025 – Jun 2026) | Paragraph-length commentary (539 notes, median 426 chars), finer release-date precision (43% better than year-only), artist geographic origin in a `From` column at 98.5% fill | No timestamps (order only, and one file has no ordering column at all); five header layouts; no local column of its own; four files whose title cell disagrees with the filename date |
| WordPress | Episodes 001–059 (Mar 2023 – Jun 2024) | The only record for pre-Spinitron episodes; already-published track notes; playback offsets | Stale since Jun 2024; unreliable post dates; inconsistent naming; a plan, not proof of airing |
| OneNote notes | ~40 notes for 2023, ~31 for 2024, plus 2025 files | Near-complete set-list coverage across three years, and the **only** set-list source for Jul 2024 – Apr 2025. Carries the on-air promo blurb (feeds `description`), release dates, geographic origin, artist death dates, Bandcamp links | Prose and set list mixed in one freeform document; no timestamps; a plan, not proof of airing |
| Email / ad hoc | Occasional | Documented repeat airings | Unstructured |

Two Spinitron exports are archived. Ingest reads
`Spins-search-results-12-5-19-8-4-26-for-KSER.csv`; the older
`Spinssearchresults84208326forKSER.csv` covers the identical 3,282 spins but
lacks `DJ ID`, `Playlist Date-time`, and `Playlist Duration`, and several
findings below are invisible without them.

## Two entities, not three

An earlier draft used three tiers — Show → Episode → Broadcast → Spins — to
distinguish *content* (an episode, which might be prerecorded and reused) from
*airing* (a specific broadcast event). That was collapsed to two entities:
**Broadcast** and **Spin**.

Reasoning: every broadcast, repeat or not, needs its own independently-logged
spin data anyway — Spinitron does not reuse a shared tracklist for repeat
airings. Confirmed directly: a Dec 23, 2025 airing and a Jun 9, 2026 airing
have identical 19-track tracklists but are two fully separate spin logs. (That
pair turns out to be one of Michael G's prerecorded episodes being re-aired —
exactly the case this design is meant to handle.) A separate "episode" entity
with its own spin list would either duplicate data or require every read to
resolve through a layer of indirection for no practical benefit.

Instead, a repeat broadcast is a normal Broadcast record with
`first_broadcast_id` pointing at the original airing, and all content fields
(title, description, mixcloud_url, etc.) are copied over at creation time
rather than looked up by reference. This keeps every record self-contained and
avoids two copies drifting out of sync if a description is edited later.

`first_broadcast_id` always points at the *original* airing, never at the
previous one, so repeat chains never form. Episode 021 aired four times; the
second, third, and fourth airings all point at the first.

### Repeats are pervasive, not exceptional

The Dec 23 / Jun 9 pair above is one confirmed case, but it is not the shape of
the problem. Scoring track overlap across all 164 broadcasts finds **23 clusters
covering 54 broadcasts — 31 of them repeat airings** needing a
`first_broadcast_id`; 110 broadcasts are standalone. Seven clusters are chains of
three or four airings, which is what makes the "always point at the original"
rule structural rather than a nicety: a nearest-match pass would build chains.

Two consequences for ingest:

- **Repeat detection is archive-wide and runs first**, before any per-source
  merge. It is not a property of set-list-bearing broadcasts, and it cannot be
  found from set lists at all — it is visible in the spin data itself.
- **It changes which source is canonical.** Three repeats re-air one of Michael
  G's workbook episodes (2026-02-17 ← 2025-09-02, 2026-03-31 ← 2026-03-03,
  2026-06-09 ← 2025-12-23) and have no workbook of their own. Without the repeat
  pass they look like ordinary Spinitron-only broadcasts and silently lose
  `artist_origin_raw`, `publish_note`, ordering, and Michael G as participant.

## `evidence` — what we know actually aired

Every Spin carries a non-nullable `evidence` value, because the sources are not
equally good at answering "did this track play?"

- **`logged`** — a source recorded it as played. Spinitron logs at air time;
  Michael G's workbooks are filled in around the show and reconcile closely
  against it.
- **`planned`** — it appears only in a pre-air set list. The WordPress
  playlists and the OneNote notes are both plans written before the broadcast,
  and a listed track may never have been played.
- **`reconstructed`** — added by reconciliation rather than read verbatim from
  any single source.

Without this field the schema has one Spin type and no way to express the
distinction, which matters most exactly where the archive is thinnest:
episodes 001–011 predate Spinitron logging entirely, so *every* spin the cache
can hold for them is a plan. Merged into an undifferentiated store, those
tracks would silently inflate play counts, local-artist share, and
"most played" figures with intent rather than fact. `evidence != "planned"` is
the query that keeps derived statistics honest.

This also formalizes a caution the analysis workbooks already state in prose:
replay rows are weaker still, since a replay airs the recording of the original
show, whose true content may itself differ from the published plan.

## `sources` — minimal ingest provenance

Both Broadcast and Spin carry a `sources` array naming which upstream systems
contributed to the record.

This cache exists *because* the sources disagree, and several of its resolution
rules are explicit multi-source merges — `local` is an OR across sources, and
release dates prefer whichever source is most precise. Without recording which
sources were involved, a resolved value can't be explained after the fact, and
correcting an upstream source means re-running the whole ingest including the
expensive spin-matching step.

A flat array rather than per-field attribution is a deliberate floor: it
answers most of the practical questions ("where did this broadcast come from?",
"which spins depend on the workbooks?") for one field per entity. Per-field
attribution can be added later if a real need appears.

Note this is *ingest* provenance, and is separate from the sync/write-back
provenance deferred below.

## Primary key: derived from air_datetime, not Spinitron's playlist ID

**Update (2026-08-05):** the access finding below is superseded. Playlist IDs
are available without an API key from the public Convergence Zone show-history
page. `czcache/fetch_spinitron_playlists.py` snapshots that paginated index into
`sources/spinitron/convergence-zone-playlists.json`. The identity argument
remains valid because six real broadcasts map to two Spinitron playlist records.

`spinitron_playlist_id` was the original candidate for primary key, since it's
Spinitron's own unique identifier for a broadcast. Two problems ruled it out:

1. **No reliable access.** Getting it requires the Spinitron v2 API with a
   station Bearer token, which requires station rights that aren't available.
   It's retained as a best-effort field when known, but the schema can't
   depend on it being populated.

2. **It records Spinitron's view of a broadcast, including its artifacts.** Six
   broadcasts show the DJ persona switching mid-show. Keying on Spinitron's ID
   would make the archive's identity depend on how Spinitron happened to record
   a session, rather than on when the show aired.

   **Mechanism, corrected against the public playlist index:** each switch
   produces **two playlist records with the same start datetime**, one per
   persona. The spin-search export omits Playlist ID, so it flattens both
   records together under the same `Playlist Date-time`; this made the two
   records look like one playlist until the public index was joined back in.
   The six broadcasts are 2025-07-01, 2025-09-09, 2025-10-14, 2025-10-21,
   2026-03-10, and 2026-04-21.

   The duplicate playlist records also produce duplicate spins in the merged
   export: the same track logged twice, 2–110 seconds apart, once under each DJ
   ID, always at or near show start. There are seven duplicate-spin pairs
   because 2025-10-14 contains two affected tracks.

   The duplicate-spin pattern is detectable from spin data alone, but the fact
   that it came from two playlist records is not: that requires the public
   playlist index (or the Spinitron API). The older export had `DJ Name` only,
   where both of Jim's personas render as the identical string "Jim Causey",
   making even the persona switch invisible.

   The paired rows are **not** redundant — they disagree on `UPC`, `Local`,
   `Song note`, `Release`, `Released`, and `Duration`, with one side usually
   the fuller record. So ingest merges them field by field, keeping the
   earlier timestamp, rather than discarding either. See
   `czcache/load_spinitron.merge_persona_duplicates`.

   Twelve dates carry a duplicate artist+song pair; only these seven are
   cross-persona. The other six are same-persona and are **not** merged —
   three have gaps of an hour or more and are genuine repeat plays within the
   two-hour show (the 2025-08-19 workbook explicitly labels its second airing
   "(OUTRO)"), and three are close enough together to be double-logs. That
   distinction needs a human, so they are reported rather than resolved.

`id` is instead derived from the full `air_datetime` (not just the date),
because the same person may host or guest-host more than one show on the same
day — date alone isn't unique, but a show's start time reliably is. In practice
no derivation is needed: the current export's `Playlist Date-time` column
already carries the ISO air datetime with a correct per-date offset
(`2026-07-28T20:30:00-0700`), so `id` is that string verbatim and there is no
DST handling to get wrong. All 164 broadcasts resolve to a unique value.

`dj_ids` is an array rather than a single value, because the mid-show persona
switches described above genuinely produce two logins for one real broadcast —
a singular field could not represent a case the data is already known to
contain. `spinitron_playlist_ids` is also necessarily an array: 158 broadcasts
have one playlist ID and the six persona-switch broadcasts have two.

## `Spin.id` is opaque, because `sequence` is mutable

`Spin.id` is assigned at creation and carries no meaning. The obvious
alternative — deriving it from `broadcast_id` plus `sequence` — is unusable
here, because the reconciliation workflow in `analysis/` is specifically about
*inserting missing tracks into existing broadcasts*. Every insertion renumbers
the spins after it, which under a sequence-derived key would silently
invalidate every identifier downstream of the fix. `sequence` is the ordering
field; it is not an identity.

## `episode_number` as a first-class field

`title` holds whatever suffix the source concatenated onto the show name,
verbatim and unparsed. `episode_number` holds the number pulled out of it.

Keeping only `title` was the earlier plan, on the grounds that the suffix is
too inconsistently formatted to parse. That reasoning holds for the *text* but
throws away the number with it, and the number turns out to be the archive's
natural join key. Spinitron barely carries it — 3,160 of 3,282 exported spins
have the bare title "Convergence Zone", with only five distinct suffixed titles
in the entire export — so `title` is null for roughly 96% of the archive and
cannot identify an episode.

Every other source *is* organized by episode number: OneNote filenames
(`Convergence Zone.029 - 10.17.23.md`), WordPress slugs (`episode-052`),
Michael G's workbook filenames, and the reconciliation analysis itself
("episode 021 alone aired four times"). Normalizing it into its own integer
field makes cross-source joins and the most common human question ("what aired
on episode 53, and how many times did it air?") direct, while `title` still
preserves the raw string.

## `show_name` as a field, not an assumption

Even though this repo currently only tracks Convergence Zone, `show_name` is
stored explicitly rather than hardcoded. This makes "is this actually a
Convergence Zone record" a direct queryable check instead of something trusted
from an upstream export's pre-filtering, and it means the schema extends to
other shows (e.g. guest-hosted appearances on other KSER programs) with no
structural change — just more rows with a different `show_name`.

`show_name` and `title` are kept separate rather than parsed out of one messy
string, because the program is always "Convergence Zone" — what varies is an
inconsistently-formatted suffix ("Ep. 053", "Ep. 55", a date). Keeping the show
name constant and the suffix in its own nullable `title` field avoids fighting
that inconsistency inside a single field — with the episode number lifted out
into `episode_number` as described above.

## `participants` vs. `dj_ids` — these are not the same thing

**`dj_ids` records who was logged into Spinitron. It is not a host indicator,
and using it as one would misattribute a significant part of the archive.**

All 28 of Michael G's hosted episodes are present in Spinitron — every one of
his workbook dates matches a broadcast — but they are logged under Jim's DJ ID
(173567), not Michael's. Across the whole 3,282-spin export the DJ name is
"Jim Causey" 3,260 times and "Michael G." just 22. Host identity therefore has to come
from elsewhere (spreadsheet filenames and title cells, WordPress, direct
knowledge) and is stored in `participants`.

`participants` is a list rather than a single field because:

- Some broadcasts involve more than one person: regular co-hosting, guest
  hosts joining for part or all of a show, and fund-drive shows where one
  person hosts live in the booth while the other runs the controls.
- The host/producer distinction doesn't meaningfully apply in practice — it
  was considered and dropped.
- Not everyone who appears has a Spinitron account. `name` is the required,
  always-present identifier; `dj_id` is optional metadata attached only when
  that person happens to have a Spinitron persona.
- `coverage: "full" | "partial"` captures guest hosts present for only part of
  a broadcast without needing timestamped segment data.

Note also that the display name "Jim Causey" maps to two distinct Spinitron
IDs. **Both are Jim's** — 173567 is his original account, used across the whole
archive (139 broadcasts), and 174269 is a second account of his, first seen
2024-10-08 and used regularly from 2025-07-15 (24 broadcasts). A third ID,
189849 ("Michael G."), appears on exactly one broadcast. Storing the raw ID
keeps that distinction rather than collapsing it into an ambiguous name.

The current export — `Spins-search-results-12-5-19-8-4-26-for-KSER.csv` —
carries a `DJ ID` column, so `dj_ids` **is** derivable from the CSV. (The older
`Spinssearchresults84208326forKSER.csv` had `DJ Name` only, where both of Jim's
personas render as the identical string, which is why several of the findings
in this document were originally invisible.)

Deriving it does not make it host attribution. From 2025-07-15 the two personas
alternate against Michael G's weeks — 173567 on his (26 of 28), 174269 on Jim's
(22 of 24) — but 2026-03-17 and 2025-10-14 break the pattern outright, so
persona alone cannot drive `participants`. **Attribution comes from workbook
presence plus `czcache/overrides/participants.yaml`, never from `dj_ids`.**

### The export is complete; Michael G's absence is an attribution artifact

This is worth stating plainly because it looks like a coverage gap and is not.
All 164 broadcasts are Tuesdays spanning 2023-05-30 → 2026-07-28, with only two
missing Tuesdays in three years (2024-11-19 and 2025-02-25 — no source material
exists for either). Michael G's era holds 61 broadcasts against 61 calendar
Tuesdays, every one of his 28 workbook dates included, on a clean every-other-week
alternation (24 × 14-day intervals; the three 28-day gaps are repeat airings).

He is invisible in the export only because Spinitron records the login used
rather than the host. No alternate export can recover this — which is precisely
why `participants` exists separately from `dj_ids`, and why the participants
override file is load-bearing rather than a convenience.

## `description_status` — because extracted prose is a guess

`description` is the one public-facing free-text field on a Broadcast, and its
only source is the OneNote notes, which interleave the on-air promo blurb with
show-prep scratch (`"Shows:"`, bare artist names, `"Destroyer?"`, Bandcamp
URLs) in a single freeform document with nothing to key on. Any extraction rule
is a heuristic, and a wrong cut publishes scratch to the website.

So `description_status` records how the text got there, in three states:

| Value | Meaning |
|---|---|
| `"approved"` | A human signed the text off in `czcache/overrides/descriptions.yaml` |
| `"proposed"` | The build extracted it from OneNote prose and **nobody has reviewed it** |
| `null` | `description` is null |

Without this field a consumer cannot tell reviewed text from a guess, and the
only safe options are publishing everything or publishing nothing. With it, the
website can render `"approved"` and hold the rest. The build writes each
proposed description alongside *the text it rejected* to a review report, so a
bad cut is visible rather than silent; approving is a one-line edit to the
overrides file, and nothing reaches `"approved"` any other way.

## `sequence` is the ordering field, not `logged_at`

Spins are ordered by `sequence` (1-based position within the broadcast), which
is always present. `logged_at` is nullable.

Reasoning: Spinitron records a real timestamp per spin, but 26 of Michael G's
28 spreadsheets record an `Order` column only. Of the two exceptions,
2025-08-19 has a `Time` column that is both partial and time-only with no
date, and 2025-10-14 has **no ordering column whatsoever** — its sequence has
to come from row position in the sheet. Ordering is the only property every
source can supply, so it's the one the schema depends on; timestamps are
retained where they exist because they're useful for runtime totals and gap
detection, but nothing structural relies on them.

`offset_seconds` is a third, separate timing field: the WordPress playlists
record an offset from the start of the show rather than a clock time, and for
the pre-Spinitron episodes that offset is the only timing data that exists
anywhere. It is kept as its own field rather than folded into `logged_at` by
adding it to `air_datetime` — that conversion would manufacture absolute
precision out of a relative figure, which is the same failure mode
`released_precision` exists to prevent.

## Spin-level fields

- **`isrc` / `upc`** — added specifically to distinguish spins of the same song
  title from different recordings or releases (a live version vs. studio vs.
  remaster). ISRC identifies the specific recording; UPC identifies the
  specific release. High real-world fill rates (~91% and ~87%) justify keeping
  both.

- **`duration_seconds`** — stored as an integer rather than the source's raw
  `"M:SS"` string, converted once at ingest so downstream consumers (runtime
  totals, gap detection against `logged_at`) use it directly without
  re-parsing. Source data contains no hour-component durations.

- **`released_date` / `released_precision`** — Spinitron's own `Released`
  field is year-only (99.3% populated, always a bare year), but Michael G's
  spreadsheets, OneNote notes, and WordPress often carry month or full-date
  precision. Measured across his 650 populated release cells: **349 year-only,
  251 month ("October 2011"), 31 full-date, 10 year-plus-reissue-text, 9
  unparsed** — so 43% are finer than what Spinitron can offer, which is the
  whole reason the field exists. `released_date` holds the release at whatever precision is
  known, and `released_precision` marks that precision explicitly so an
  unknown day is never silently defaulted to a fabricated value. Where sources
  disagree in precision, ingest should prefer the most precise value rather
  than defaulting to Spinitron's year-only figure.

  Reissue and remaster years are **not** tracked. Where a source records both,
  the original release date is kept and the reissue year is discarded at
  ingest. Ten cells take this shape, including genuinely two-line values like
  `"1996 (original on Relic)\n1998 (Reissue)"`, so the parser must handle an
  embedded newline, not just a parenthetical.

- **`local` / `local_basis`** — **three-state, and the basis is tracked.**

  A song counts as local if the *artist* is originally from the Pacific
  Northwest or currently lives there, **or** if the *label* is there. Pacific
  Northwest is defined as: WA, OR, AK, MT, ID, BC.

  Those are two different claims about two different entities, and collapsing
  them loses real information — a Seattle artist on a London label and a
  Portland label releasing a Berlin artist are both "local" under the rule but
  are not the same fact, and only one of them is the thing a listener usually
  means. `local_basis` records which applied, as an array because both can:

  - `"artist"` — artist origin or current residence resolves to the PNW
  - `"label"` — the label's location resolves to the PNW
  - `"dj_flag"` — Spinitron's `L` flag was set in the booth. It is a deliberate
    call by the DJ, but Spinitron records no reason, so it cannot honestly be
    attributed to artist or label and gets its own basis value.

  `local` itself resolves to true if any basis applies — still an OR across
  sources — but it is **nullable**, and null means *not yet assessed*, which is
  not the same as false ("assessed, not local"). This is the correction to an
  earlier draft that made it a non-nullable boolean: the data does not support
  that assertion. **25 of the 28 broadcasts Michael G hosted have zero local
  flags set in Spinitron** — 33 of 567 of his spins carry the flag (5.8%) vs.
  505 of 2,715 (18.6%) on the rest — and on those episodes an empty flag means
  the question was never asked. Defaulting that to false would understate
  local-artist share, a number a community station actually reports on, by
  asserting something no source ever checked.

  Note that the workbooks contain **no local column of their own**. The only
  locality signal they carry is the `From` column, so on Michael G's episodes
  the `"artist"` basis is the only one available and `"dj_flag"` is nearly
  always absent.

- **`artist_origin_raw` / `label_origin_raw`** — the source's location text,
  kept verbatim rather than evaluated and discarded.

  An earlier draft dropped these strings once the boolean was computed. That
  makes the locality rule a one-way door. Michael G's `From` column holds
  **254 distinct values across 651 populated cells (98.5% fill)**, with real
  variants ("Seattle, WA" vs. bare "Seattle", "Vancouver, BC, Canada" vs.
  "Vancouver BC") and plenty that resolve to no clean region at all
  ("Romania - Germany", "German-born British", "Scottland"). The first
  normalization pass will certainly be imperfect and will want improving —
  and once the input text is gone, improving it means re-ingesting the
  workbooks and redoing the spin matching, which is the expensive part.
  Retaining the strings costs two nullable fields and makes the rule
  re-runnable in place.

  `From` describes the **artist**, not the label. No source currently
  populates `label_origin_raw`; it is carried because the locality rule
  explicitly admits a label basis, and because Spinitron's `L` flag may itself
  have been set on label grounds that were never written down.

- **`artist_key`** — normalized artist name for grouping, null until the
  normalization pass runs. Name normalization is deferred (see below), but a
  purely verbatim store pushes the ~18 known variant pairs onto every consumer
  forever. Carrying the field now means that pass lands without a migration.

- **`request`** — non-nullable boolean, assumed false unless a source
  indicates otherwise. Currently 0% fill in the Spinitron export sample, but
  listener requests do occur and the field costs nothing to carry.

- **`song_note` vs. `publish_note`** — `song_note` is a verbatim mirror of
  Spinitron's own note field (blank ~88% of the time). `publish_note` is the
  public-facing field: it starts as a copy of `song_note`, of Michael G's
  richer "Comments/Notes" content, or of the note already published on
  WordPress, at publish time, but is expected to diverge
  over time. He wrote 539 notes across 661 spins, running to a median of 426
  characters and a maximum of 3,052 — substantially more than anything in
  Spinitron, whose own note field is populated on just 11.5% of spins — and
  ranging from short identifications ("aka Sascha Ring") to full
  paragraph-length commentary.
  The two fields have different audiences and different editing lifecycles,
  which is why they're separate. The WordPress source matters here beyond
  being one more input: for episodes 001–059 it is the only note source, and
  its notes are already published text ("1993 live concert at the Mayfair
  Theatre in Santa Monica, CA"), so they arrive fit for `publish_note` as-is.

- **Scripts were considered and dropped.** An earlier draft included an
  episode-level `scripts` array for private on-air talking points. Cut
  entirely — script content is not part of what this cache retains.

## Null convention

`null` means "no value" and is used consistently instead of empty string.
Empty string is never a stand-in for missing data — that would conflate "we
checked, there's genuinely nothing here" with "this hasn't been populated
yet," which matters for a schema merging sources of differing completeness.
Ingest code reading raw sources must convert empty strings to `null`.

Nullability is set from observed fill rates across *both* major sources, not
Spinitron alone. `artist` and `song` are non-nullable because they're
populated everywhere; `release` is nullable because it's occasionally blank in
Michael G's spreadsheets even though it's 100% populated in Spinitron.

`request` is the one deliberate exception: a non-nullable boolean where absent
source data genuinely does mean false. `local` was originally paired with it
and is not — it is nullable precisely because absent source data there means
"not assessed." See the resolution rules above.

Arrays (`participants`, `dj_ids`, `spinitron_playlist_ids`, `local_basis`,
`sources`) express absence as the empty array and are never null, so consumers
need one check rather than two.

## Ingest notes

- Michael G's 28 spreadsheets use five header layouts. The dominant one, in 24
  files, is `Order | Artist | Song | From | Album | Released | Label |
  Comments/Notes`. The four exceptions are one file each:
  - `2025-08-19` — `Time | Artist | Song | From | Album/Single | Year | Label`
    (no `Order`, no notes; `Album/Single` and `Year` are this one file, not
    two separate variants)
  - `2025-10-14` — `Artist | Song | From | Album | Released | Label` (no
    ordering column, no notes)
  - `2026-03-17` — the standard layout plus a stray `Verify Clean` column
  - `2026-06-23` — the standard layout with `Comments/Notes` replaced by
    `Mic Summary`

  Parsing must be header-driven rather than positional, and must locate the
  header row rather than assume row 1 — every file opens with a title row like
  `"September 2, 2025 (Michael G)"` above the headers.
- The workbook title cell is **not** a reliable air date. Four files disagree
  with their filename: `2026.04.14` says "March 31, 2025", `2026.04.28` says
  "April 28, 2025", `2026.05.26` says "May 26, 2025", and `2026.06.23` says
  "June 26, 2026". The filename is authoritative — all 28 filename dates match
  a Spinitron broadcast exactly, and none of the title-cell dates do.
- Every workbook carries empty `Sheet2` and `Sheet3` alongside `Sheet1`.
  Ignore them; no file has data outside `Sheet1`.
- Mid-show persona switches produce **duplicate spins inside one playlist, not
  stub playlists**. Merge the pair field by field, keeping the earlier
  timestamp — neither row is redundant. Detection needs `DJ ID`: group by
  normalized `(artist, song)` within a broadcast, and merge only a group of
  exactly two rows ≤180 seconds apart under *distinct* DJ IDs. Same-persona
  duplicates are reported, never merged. See the primary-key section above.
- Location strings in Michael G's sheets need normalization before the `local`
  rule can be applied reliably — 247 distinct values with real variants
  ("Seattle, WA" vs. bare "Seattle", "Vancouver, BC, Canada" vs. "Vancouver
  BC"), so a bare state-code match will miss city-only entries. Store the raw
  string regardless of whether the rule resolves it; an unresolved string
  leaves `local` null, not false.
- `evidence` must be set from the source, never defaulted. Spinitron and
  Michael G's workbooks yield `"logged"`; WordPress and OneNote yield
  `"planned"` unless a logged source corroborates the same track on the same
  broadcast, in which case the record is `"logged"` and lists both sources.
- OneNote notes interleave promo prose, show-prep scratch, and the set list in
  one freeform document, with no header row to key on. The blurb paragraphs
  feed `Broadcast.description`; the track lines are loosely delimited (dashes
  are the common case, but line shape varies) and carry release dates, origin
  text, and commentary inline.

## Explicitly deferred, not forgotten

- **Sync/write-back provenance** (`origin`, `synced_at`, `local_dirty`,
  `conflict` fields) for two-way syncing between this cache and Spinitron or
  WordPress. Deferred because the editing surface (Sveltia CMS, WordPress,
  something else) isn't decided, and this metadata can be added later without
  migrating existing data. Distinct from the `sources` array, which is ingest
  provenance and is not deferred.
- **Per-field source attribution**, including `released_source` — which
  upstream source supplied a given release date. The record-level `sources`
  array covers the practical cases; per-field attribution is more tracking
  than currently needed and can be layered on without restructuring.
- **Artist and participant name normalization** — ~18 known artist-name
  variant pairs, plus the same drift risk for participant names. The
  `artist_key` field is carried now (null-valued) so this pass needs no
  migration when it happens.
- **Location-string normalization** — the rule that turns
  `artist_origin_raw` / `label_origin_raw` into `local` and `local_basis`.
  Both raw strings are retained, so this can be improved and re-run against
  stored data at any point.

Two items this list previously carried are now resolved and have moved into the
body of this document: **the identity of Spinitron DJ ID 174269** (a second
account of Jim's — see the `participants` section) and **systematic
repeat-broadcast detection**, which has now been run across the full archive
(23 clusters, 31 repeat airings — see "Repeats are pervasive, not exceptional").
