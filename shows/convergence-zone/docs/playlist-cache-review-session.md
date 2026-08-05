# Convergence Zone Playlist Cache — Override Review Session

**Date:** August 5, 2026
**Branch:** `apply-playlist-cache-overrides`
**Purpose:** Record what was decided in the czcache override review, and why —
so the decisions are auditable later without re-deriving them from the evidence,
and so the ones made *against* the evidence stay visible.

---

## 1. Where this picks up

`tools/python/czcache/` builds the canonical playlist cache at
`shows/convergence-zone/playlists/cache/` from four sources of very different
quality: MichaelG's workbooks, the convergencezone.fm set lists, the OneNote
prep notes, and the Spinitron export. That build landed in PR #7 and is on
`main`.

The build was designed so that anything it *cannot* know from the sources is
deferred to a human, via four checked-in override files in
`tools/python/czcache/overrides/`. The build shipped with all four effectively
empty and a set of reports naming what needed a decision. This session was that
review.

## 2. Three bugs found, because the decisions didn't take effect

The review surfaced the bugs rather than the other way round: decisions were
written into the YAML, the cache was rebuilt, and nothing changed.

**PyYAML resolves an unquoted ISO date to `datetime.date`, not `str`.** Every
override file is documented as keyed by air date, and `2026-07-07:` is the
obvious way to write that — but the lookup key on the other side is the string
form of the broadcast id. So every `descriptions.yaml` and `participants.yaml`
entry silently missed. `load_overrides()` now normalises both key forms rather
than making correctness depend on remembering to quote.

The consequence worth stating plainly: **the description review gate had never
worked.** `verify.py` check 9 ("nothing approved with an empty overrides file")
passed the whole time — because the file was empty. The check could not
distinguish "the gate holds" from "the gate is not wired up."

**`spins.yaml merge_duplicates` was parsed and dropped on the floor.** It was
documented, shipped with a worked example, and read by nothing. `forced` is now
threaded through `load()` into `merge_persona_duplicates()`, matched on the
normalised artist and song so an override survives the title drift that usually
accompanies a re-log (`"Deep Mindset (Original Mix)"` vs `"Deep Mindset"`).

**`load_prose` stopped before it started on most notes.** OneNote exports the
note's own title as the first body line (`Convergence Zone.012 - May 30 2023`).
That line is short, so the scratch heuristic read it as working notes and cut
extraction at line one. Fixing that, plus a longest-run fallback for blurbs that
aren't at the top of the note, bullet stripping, and trailing station-boilerplate
trimming, took proposed descriptions from 21 to 35 and notes yielding nothing
from 40 to 5.

One regression along the way, worth remembering: boilerplate trimming initially
ran *before* scoring, which collapsed the confident candidates from 17 to 4 —
naming the station and the air time is the strongest evidence a paragraph is
real promo copy, so scoring the trimmed text penalised every note for exactly
what had just been removed. Scoring now runs on the untrimmed text and only the
emitted candidate is trimmed.

`verify.py` checks 2, 6 and 9 are now override-aware — they derive what to expect
from the override files instead of hardcoding design-time constants, so an
approved human decision no longer reads as a regression. Check 9 additionally
asserts no repeat inherits an approval its own date has no entry for.

## 3. The decisions

### Duplicate spins (`spins.yaml`)

The build merges cross-persona double-logs automatically (7 pairs, both of Jim's
Spinitron personas logging the same track seconds apart at show start). The six
*same-persona* duplicates are a human call, because a wide gap is usually a
genuine repeat play within a two-hour show and a short one is usually a re-log.

| Broadcast | Track | Gap | Decision |
|---|---|---|---|
| 2026-03-17 | yu-more — Deep Mindset | 60s | **Merge** — second row is a bare re-log of the first |
| 2025-05-20 | Fotoform — Skimming the Surface | 125s | **Merge** — second row adds the Tractor Tavern note |
| 2024-04-16 | Suzanne Ciani — Eclipse | 97s | **Merge** — see dissent below |
| 2025-08-19 | Tranquilant | 7254s | Keep both — top and close of the night |
| 2025-02-11 | Always Return to You | 7127s | Keep both |
| 2024-02-20 | Music for the Dome | 3542s | Keep both |

The 2025-08-19 pair is independently confirmed: MichaelG's workbook labels the
second airing `(OUTRO)` in his own hand.

**Dissenting evidence on 2024-04-16, decided against.** The published
convergencezone.fm playlist for Episode 053 "Total Eclipse 2024" independently
lists Eclipse twice, at offsets 30:36 and 32:13 — the *same* 97-second gap
Spinitron shows. Two sources therefore record two plays. Jim's call is that this
is one play double-logged in both, so the merge stands. Side effect: with the
Spinitron pair merged, the set list's second Eclipse entry has no logged
counterpart and now surfaces as a `planned` spin. The airing is still in the
cache, just as a plan rather than a log. Revisit against the Mixcloud audio if
it ever matters.

### Host attribution (`participants.yaml`)

`dj_ids` records which Spinitron *login* was used, never who hosted — both
"Jim Causey" personas are Jim's, and 26 of MichaelG's 28 episodes were logged
under Jim's original account. The build infers MichaelG from the presence of one
of his workbooks. Five dates that rule gets wrong:

- **2026-07-07, 2026-07-21** — MichaelG kept alternating through July 2026 but
  stopped producing workbooks after 2026-06-23, so the rule handed his weeks to
  Jim. Nothing in any source records this. Without these entries the archive
  shows five consecutive Jim weeks and the every-other-week pattern appears to
  end a month before it did.
- **2025-10-14** — MichaelG's fund-drive show with Jim on as a guest. This also
  explains the persona switch mid-show that produced the duplicate Fotoform and
  Beach Vacation spins.
- **2025-10-21** — Jim's ARP fund-drive special, MichaelG co-hosting part of it.
- **2024-10-15** — David Haldeman (host of *Dead Electric*) in the booth for the
  whole show. No Spinitron persona, so `dj_id` is null.

The last two came out of reading the **descriptions**, not the attribution
report — the promo copy names people no structured source records. Worth
knowing for future passes: the blurbs are a real attribution source in their own
right for guest-host cases.

### Repeats (`repeats.yaml`)

Detection found 23 clusters / 31 repeat airings at the 0.60 track-overlap floor.
One addition: **2024-06-18 is a replay of 2024-06-11**, scoring below the floor.
The threshold itself stays at 0.60 — the 0.40–0.95 review band in
`reports/repeats.md` is doing its job, and lowering the floor to catch this one
case would pull in noise.

### Descriptions (`descriptions.yaml`)

All 35 proposed candidates were read in full, in four batches, and approved — so
no broadcast is left carrying unreviewed `proposed` text in a public-facing
field. The entries are the extractor's output plus **only** the corrections
called during review; nothing was rewritten and no new copy was authored:

- Misspelled artist names carried from the original notes — `Public Service
  Beoadcasting`, `Laaraji`, `Erik Wollo`, `Mt Fog`/`Mt, Fog`, a lowercase
  `terminus void`, a duplicated `Bunadox`, and `unsettle and display` for
  *dismay*.
- **2024-09-24** — an unfinished parenthetical, literally `(thanks )`, completed
  with the attribution it had been waiting for: Maggie Molloy, host of KING-FM's
  *Second Inversion*, with a link to her host page.
- **2025-10-21** — the only genuinely bad cut. The extractor swept in the station
  sign-off and, below it, an unrelated paragraph from Norm Chambers' obituary
  sitting further down the note. Both trailing paragraphs removed. Also fixed
  `Convergency Zone` and `from through 1970s`.

The other 129 broadcasts have no approved description. That is not an oversight:
their notes either carry no promo copy or none the extractor could isolate.

## 4. Why review this way

Editing four YAML files by hand against five Markdown reports is the workflow the
build was designed for, and it is genuinely unpleasant — the evidence for any one
decision is spread across the report, the source CSV, and sometimes the published
playlist. Doing it conversationally instead, one flagged item at a time with the
evidence pulled up alongside, is what surfaced the Ciani contradiction and the two
attribution facts hiding in the promo copy. Neither would have come out of reading
the reports alone.

The output is the same either way: checked-in YAML with the reasoning inline. The
files are the record, not the conversation.

## 5. State at the end

```
broadcasts 164   spins 3741   A/B/C 31/70/63
evidence {'planned': 311, 'logged': 3430}
descriptions {'approved': 35, None: 129}
```

`verify.py`: all checks pass, determinism included. A second `build.py` run is
byte-identical, which is the property that makes the cache reviewable in a PR at
all.

## 6. Not done here

- **`schema-rationale.md` is current** as of the cache-build PR and was not
  revisited this session; the override decisions above do not contradict it.
- **Artist name normalisation** — `artist_key` is still emitted null; the ~18
  known variant pairs are a later pass needing no migration.
- **Correcting attribution in Spinitron itself.** The cache now records the truth
  via `participants`. Whether to retroactively re-attribute MichaelG's 26
  episodes upstream is a separate decision.
- **Write-back** to WordPress and Spinitron, and publishing the playlists not yet
  on the site — tracked separately; see `playlist-automation-session-summary.md`.
