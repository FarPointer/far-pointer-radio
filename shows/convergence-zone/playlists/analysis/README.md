# Playlist Analysis

Working files produced by reconciling `sources/` against what Spinitron actually
logged. These are worksheets for fixing the Spinitron record, not playlists
themselves — expect them to be superseded once the corrections are applied.

## Files

| File | Contents |
|---|---|
| `cz-missing-spins.xlsx` | Two-sheet reconciliation workbook covering every MichaelG episode |
| `cz-removal-candidates.csv` | Flat export of the removal-candidate sheet, for diffing and scripting |
| `cz-playlist-spinitron-audit.xlsx` | Published/prep set lists vs Spinitron, for the 68 broadcasts where both exist |

## cz-missing-spins.xlsx

Generated — do not hand-edit. `czcache/build_missing_spins.py` writes both sheets and
`czcache/enrich_missing_spins.py` fills the metadata columns and the CSV export. Every
date with a workbook in `../sources/michaelg/` is re-audited on each run, against the
Spinitron export `czcache/paths.py` points at, so a new workbook or a fresh export is
picked up without editing either script.

Suggested times are interpolated across the log gap a run of missing tracks falls into,
where the gap is bounded by the *matched* spins on either side in workbook order. An
unmatched spin does not bound a gap: it is itself under review, and often turns out to be
one of the missing tracks logged under the wrong artist — which is what the amber hints
name.

| Sheet | Contents |
|---|---|
| `Add missing` | Tracks present in MichaelG's workbooks but absent from Spinitron, with a suggested insertion timestamp, `Release` year, `Local` flag, `Duration`, `Label`, confidence rating, and source sheet row. Gray rows sit in tight log windows and may not have actually aired — MichaelG confirms those. |
| `Remove or replace` | Spins logged in Spinitron with no counterpart in the workbooks, plus `Release` year, `Local`, `Duration`, and `Label` for direct Spinitron import prep. Amber rows carry a hint naming a nearby missing track the spin may actually be; those get **edited in place** rather than removed, and the matching row on `Add missing` is skipped. |

`cz-removal-candidates.csv` is the `Remove or replace` sheet as CSV, including
`release` (year), `local`, `duration`, and `label` columns plus the amber hints
in `hint`.

## cz-playlist-spinitron-audit.xlsx

Covers the 68 **broadcasts** that have both a set list and a Spinitron playlist. For 64
the reference is a playlist published at
[convergencezone.fm](https://convergencezone.fm) (archived in
`../sources/convergencezone.fm/`); for the other four it is the OneNote prep note. The
`Summary` sheet names which was used per row.

Rows are broadcasts, not episodes. The show is replayed from automation during vacations
and hiatus, and each replay is logged in Spinitron as its own playlist — so each is
audited separately against the set list of the episode it repeats. Fifteen playlists
account for two or more rows each; episode 021 alone aired four times. The `Airing` and
`Repeat of` columns identify these.

| Sheet | Contents |
|---|---|
| `Summary` | One row per broadcast. `Coverage` is the share of spins the reference accounts for; `Reference logged` is the share of reference tracks that reached Spinitron. High coverage with low `Reference logged` is the actionable case — the set list tracks the show well and Spinitron is short. |
| `Add to Spinitron` | Reference tracks with no matching spin. Amber rows have an unlogged spin by the same artist, so the track was likely swapped rather than dropped — edit that spin instead of adding one. |
| `Check metadata` | Matched spins whose artist, song, or album text disagrees with the reference. |
| `Spins not in notes` | Logged spins absent from the reference. **Not a removal list** — usually just an unfinished reference. |
| `Method` | Scope, matching rules, and known limits. |

A broadcast is identified by its songs, not by any date: a page states the date it was
written for, which for a replay is months before the airing being audited. Distinct
consecutive weeks overlap around 0.00–0.08 and genuine replays 0.6–0.96, so the two are
easy to separate; a replay claim scoring below 0.60 is rejected.

The remaining 96 Spinitron playlists have no set list to check against — most OneNote
files are promo blurbs, 17 of 66 site posts are prose only, and the site archive stops at
the 2024 Summer Solstice special (June 2024).

The published playlist and the OneNote note are the **same document**: identical track
sets on every episode where both exist. The site version wins only on text quality, so it
does not independently confirm that a track aired. Both are plans written before air,
which makes them weaker evidence than MichaelG's workbooks — a listed track may never
have been played. Treat every row as a prompt to check Spinitron, not a correction to
apply blindly.

Replay rows carry an extra caveat: a replay airs the *recording* of the original show, so
its true content is what that episode actually played, which may itself differ from the
published plan. A track missing on a replay row can mean the original never played it.
