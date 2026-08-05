// Convergence Zone Playlist Cache — Schema
// Canonical data store for broadcasts and spins, derived from Spinitron
// and other sources (Michael G's spreadsheets, OneNote, WordPress) as useful.

type SourceName = "spinitron" | "michaelg" | "wordpress" | "onenote";

interface Broadcast {
  id: string;                    // derived from full air_datetime, e.g. "2026-04-21T20:30:00-0700"
  air_datetime: string;          // ISO 8601 datetime, includes start time
  show_name: string;             // "Convergence Zone" — constant for this repo,
                                  // kept as a field (not hardcoded) so the schema
                                  // extends cleanly to other shows if ever needed

  episode_number: number | null; // normalized episode number, e.g. 53. Sourced from
                                  // OneNote filenames, WordPress slugs, Michael G's
                                  // filenames, or a Spinitron title suffix — in that
                                  // order of availability. Rarely present in Spinitron
                                  // (96% of spins carry the bare title "Convergence
                                  // Zone"), so this is a cross-source join key that
                                  // cannot be derived from the export alone.
  title: string | null;          // e.g. "Ep. 53" — whatever suffix got concatenated
                                  // onto the show name in source data, verbatim and
                                  // unparsed; null if untitled

  participants: Participant[];   // who actually hosted — NOT derivable from dj_ids

  is_prerecorded: boolean;
  description: string | null;    // the on-air/promo blurb; OneNote notes carry this
                                  // for most of 2023–2025
  description_status: "approved" | "proposed" | null;
                                  // "approved" — a human signed off on this text in
                                  //              overrides/descriptions.yaml
                                  // "proposed" — extracted from OneNote prose by the
                                  //              build and NOT yet reviewed
                                  // null       — description is null
                                  // The prose notes mix genuine promo copy with scratch
                                  // ideas and open questions, so extraction is a guess.
                                  // Without this field a consumer cannot tell reviewed
                                  // text from a guess, and the site would publish
                                  // unreviewed prose. See rationale doc.
  mixcloud_url: string | null;
  webpage_url: string | null;    // WordPress permalink now, future site URL later

  scheduled_duration_minutes: number | null;  // Spinitron's "Playlist Duration"; the
                                               // slot length, not the sum of spins

  dj_ids: string[];              // Spinitron personas logged in during this airing.
                                  // NOT a host indicator — see rationale doc. More
                                  // than one entry where the persona switched
                                  // mid-show. Empty array when unknown.

  spinitron_playlist_ids: string[];  // public Spinitron playlist IDs. Normally one;
                                      // six persona-switch broadcasts have two records
                                      // with the same start datetime, merged here into
                                      // one real-world broadcast. Not a primary key.

  first_broadcast_id: string | null;     // null if this IS the original airing;
                                          // otherwise the id of the ORIGINAL airing —
                                          // always the original, never the previous
                                          // one, so repeat chains never form. Repeats
                                          // are fully self-contained records
                                          // (title/description/etc. copied over, not
                                          // looked up by reference)

  repeat_of_source: "documented" | "inferred" | null;
  repeat_of_confidence: number | null;   // 0.0–1.0, only set when repeat_of_source
                                          // is "inferred"; null for documented repeats
                                          // and for originals

  sources: SourceName[];         // which upstream sources contributed to this record
}

interface Participant {
  name: string;                  // canonical display name — always present
  dj_id: string | null;          // Spinitron persona ID, only if they have one
  coverage: "full" | "partial";  // "partial" for guest hosts joining part of a show
}

interface Spin {
  id: string;                    // opaque and stable, assigned at creation. NOT derived
                                  // from sequence — sequence is mutable (reconciliation
                                  // inserts missing spins and renumbers what follows),
                                  // so a sequence-derived key would break on every fix.
  broadcast_id: string;          // FK — spins belong to a specific airing, not
                                  // to an abstract "episode"

  evidence: "logged" | "planned" | "reconstructed";
                                  // "logged"        — a source recorded this as played
                                  //                   (Spinitron, Michael G's sheets)
                                  // "planned"       — from a pre-air set list only
                                  //                   (WordPress, OneNote); may never
                                  //                   have actually aired
                                  // "reconstructed" — added by reconciliation, not
                                  //                   present verbatim in any one source
                                  // Non-nullable, no default. See rationale doc.

  sequence: number;              // 1-based position within the broadcast. Always
                                  // present. This is the canonical ordering field,
                                  // because not every source records timestamps.
                                  // Mutable — renumbered when spins are inserted.
  logged_at: string | null;      // ISO 8601 datetime — when this spin was logged.
                                  // Spinitron-sourced spins have it; most of
                                  // Michael G's spreadsheets record order only.
  offset_seconds: number | null; // seconds from the start of the broadcast. The
                                  // WordPress playlists record offsets rather than
                                  // clock times, and for the pre-Spinitron episodes
                                  // it is the only timing data that exists. Kept
                                  // separate rather than converted into logged_at,
                                  // which would fabricate absolute precision.

  artist: string;                // always populated across all sources
  artist_key: string | null;     // normalized artist name for grouping; null until the
                                  // normalization pass runs. Held now so that pass
                                  // needs no migration — see rationale doc.
  song: string;                  // always populated across all sources
  release: string | null;        // album/single title; occasionally blank in
                                  // Michael G's spreadsheets

  isrc: string | null;           // identifies the specific recording/version —
                                  // distinguishes a live cut, remaster, etc. from
                                  // the same song title on a different release
                                  // (~91% fill rate in Spinitron data)
  upc: string | null;            // identifies the specific release/album this
                                  // spin came from (~87% fill rate)

  duration_seconds: number | null;  // converted from Spinitron's "M:SS" string at
                                     // ingest; null if source had no duration

  released_date: string | null;     // partial ISO 8601: "2026", "2026-03", or
                                     // "2026-03-17" depending on available precision
  released_precision: "year" | "month" | "day" | null;
                                     // explicit precision marker so downstream code
                                     // never has to infer precision from string shape,
                                     // and unknown day/month is never silently
                                     // defaulted to a fabricated value

  label: string | null;             // blank ~4% of the time in Spinitron data,
                                     // more often in Michael G's spreadsheets

  local: boolean | null;            // resolved locality. null means NOT YET ASSESSED —
                                     // distinct from false ("assessed, not local").
                                     // True if any basis below resolves to the Pacific
                                     // Northwest. See rationale doc for the rule.
  local_basis: LocalBasis[];        // WHY it counts as local — artist and label are
                                     // different claims and are tracked separately.
                                     // Empty when local is false or null.
  artist_origin_raw: string | null; // verbatim location text for the artist, as the
                                     // source wrote it ("Seattle, WA", bare "Seattle",
                                     // "Vancouver BC"). Retained unnormalized so the
                                     // locality rule can be re-run in place when it
                                     // improves, without re-ingesting the workbooks.
  label_origin_raw: string | null;  // same, for the label's location

  request: boolean;                 // true if this spin was a listener request;
                                     // assumed false unless a source says otherwise

  song_note: string | null;         // verbatim from Spinitron; blank ~88% of the
                                     // time in Spinitron data
  publish_note: string | null;      // WordPress-facing note; starts as a copy of
                                     // song_note, Michael G's "Comments/Notes"
                                     // content, or the already-published WordPress
                                     // note, but can diverge — this is the field
                                     // that appears publicly

  sources: SourceName[];            // which upstream sources contributed to this record
}

type LocalBasis =
  | "artist"    // artist is originally from, or currently lives in, the PNW
  | "label"     // the label is in the PNW
  | "dj_flag";  // Spinitron's L flag was set by the DJ in the booth; the underlying
                // basis was not recorded, so it cannot be attributed to artist or label

// Null convention: null means "no value" and is used consistently instead of
// empty string. Empty string is not used as a stand-in for "no data" anywhere
// in this schema. Ingest code reading from raw sources (CSV, spreadsheets, API)
// must convert empty strings to null rather than passing them through as "".
//
// Exceptions:
//   - `request` is a non-nullable boolean; absent source data means false.
//   - `local` is deliberately nullable (three-state) — absent source data means
//     "not assessed," which is not the same as "not local."
//   - `dj_ids`, `spinitron_playlist_ids`, `local_basis`, `participants`, and
//     `sources` are arrays; absence is the empty array, never null.
// See the rationale doc for each.
