---
name: episode-prep
description: Assemble the show-night packet for an upcoming Convergence Zone episode — repeat avoidance, local-artist coverage, and outstanding data gaps. Use when asked to "prep this week's show", "have we played this before?", or "what's my local count?".
---

# Preparing an episode

Convergence Zone airs Tuesday nights at 8:30 PM PT on 90.7 KSER-FM and 89.9 KXIR-FM. The
show spotlights Pacific Northwest artists alongside the contemporary and legendary
musicians who inspire them, so two questions come up every week: **have we played this
recently**, and **is there enough local content**.

Everything you need is already in `shows/convergence-zone/playlists/cache/` — 165
broadcasts and every spin, with `local` and `local_basis` resolved. Query it; do not
re-derive anything from the raw sources, and do not ask Spinitron.

## Reading the cache

- `cache/index.json` — one row per broadcast: `id`, `date`, `episode_number`, `class`,
  `spins`, `participants`, `first_broadcast_id`, `description_status`.
- `cache/broadcasts/YYYY-MM-DD.json` — the full broadcast, including every spin.

Useful spin fields: `artist`, `song`, `release`, `label`, `local`, `local_basis`,
`released_date`, `evidence` (`logged` = Spinitron actually logged it; `planned` = it was
on a set list only), `sequence`.

## What to produce

Ask what the user is planning before assembling anything — a themed show, a fund drive, and
an ordinary week need different packets. Then, from the candidate tracks or artists:

1. **Repeat avoidance.** For each candidate artist and track, the last air date and how
   many times it has aired. Match on the artist and a normalised title — a re-log often
   drifts the title (`"Deep Mindset (Original Mix)"` vs `"Deep Mindset"`), and matching the
   raw string will tell you a track is new when it is not.

2. **Local coverage.** Count and share of candidates with `local: true`, and the
   `local_basis` for each — `artist`, `label`, or `dj_flag`. `dj_flag` means the DJ marked
   it local at log time without recording why; it is the weakest basis and worth a second
   look for a show that leans on the local claim.

3. **Balance.** Contemporary vs legendary, using `released_date` where present. Artists
   already heavy in the recent archive.

4. **Gaps worth knowing about.** From the last few broadcasts:
   - Missing or unapproved descriptions (`description_status` `proposed` or `null`) — these
     block publishing.
   - Entries in `analysis/cz-missing-spins.xlsx` for recent dates: tracks that were played
     but never logged in Spinitron, which is a station-facing problem, not a data one.

## Rules

- **Read-only.** This skill never writes to the cache, the sources, or the overrides.
- Present a `proposed` description as a draft that still needs approval — never as copy.
- If the cache looks stale relative to the last aired date, say so and point at the
  `cz-cache-rebuild` skill rather than rebuilding as a side effect.
- Keep the packet short enough to read on show night.
