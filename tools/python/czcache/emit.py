"""Write the cache and the review reports.

The cache is meant to be read in a pull request, so output is stable by construction:
fixed key order from model.py, sorted collections, and one file per broadcast. A rebuild
that changes nothing must produce a zero-line diff, otherwise the diff stops being
evidence of anything.

Spins nest inside their broadcast rather than living in a parallel file. They are owned
by a single airing, a broadcast is the natural unit to review, and nesting makes the
schema's `broadcast_id` foreign key implicit rather than something to keep in sync.
"""
import json
import shutil

from paths import BROADCASTS, CACHE, INDEX, REPORTS


def write_cache(broadcasts, root=None):
    """Replace playlists/cache/ wholesale, so a removed broadcast cannot linger.

    `root` redirects the whole cache elsewhere, which is what lets verify.py build twice
    into throwaway directories and compare -- a real determinism check, rather than a
    diff of the working tree against whatever happens to be committed.
    """
    cache = CACHE if root is None else root
    broadcasts_dir = cache / "broadcasts"
    index_path = cache / "index.json"

    if broadcasts_dir.exists():
        shutil.rmtree(broadcasts_dir)
    broadcasts_dir.mkdir(parents=True, exist_ok=True)

    index = []
    for bid in sorted(broadcasts):
        bc = broadcasts[bid]
        # `_class` is a build-time routing decision, not part of the schema. It belongs
        # in the index, where it helps a reader see which merge produced a record, and
        # not in the broadcast file, which should match schema.ts exactly.
        klass = bc.pop("_class", None)
        (broadcasts_dir / f"{bid[:10]}.json").write_text(
            json.dumps(bc, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
            encoding="utf-8")
        index.append({
            "id": bc["id"],
            "date": bid[:10],
            "episode_number": bc["episode_number"],
            "class": klass,
            "spins": len(bc["spins"]),
            "participants": [p["name"] for p in bc["participants"]],
            "first_broadcast_id": bc["first_broadcast_id"],
            "description_status": bc["description_status"],
        })

    cache.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    return index


def _table(rows, columns):
    if not rows:
        return "_None._\n"
    out = ["| " + " | ".join(columns) + " |",
           "|" + "|".join("---" for _ in columns) + "|"]
    for r in rows:
        cells = []
        for c in columns:
            v = r.get(c, "")
            v = "" if v is None else str(v)
            cells.append(v.replace("|", "\\|").replace("\n", " ")[:160])
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def write_reports(ctx):
    REPORTS.mkdir(parents=True, exist_ok=True)
    r = ctx["report"]

    (REPORTS / "discrepancies.md").write_text(f"""# Discrepancies

Field-level disagreements found while merging. Nothing here blocks a build; the cache is
always complete. These are the places where two sources both had an opinion.

## Cross-persona duplicate spins (merged)

The same track logged twice seconds apart under both of Jim's Spinitron personas, at the
start of six broadcasts. Merged field by field, keeping the earlier timestamp. Where both
rows had a value and the values differed, the earlier row's value was kept:

{_table([{'broadcast': m['broadcast_id'][:10], 'artist': m['artist'], 'song': m['song'],
          'gap_s': round(m['gap_seconds']), 'dj_ids': ', '.join(m['dj_ids']),
          'conflicting_fields': ', '.join(c['field'] for c in m['conflicts']) or '-'}
         for m in ctx['merges']],
        ['broadcast', 'artist', 'song', 'gap_s', 'dj_ids', 'conflicting_fields'])}
## Duplicate spins left alone

Same artist and song within one broadcast, but *not* a persona switch. Wide gaps are
almost certainly a genuine repeat play within the two-hour show; short ones may be a
double-log. Merging these is a human call -- use `overrides/spins.yaml`:

{_table([{'broadcast': f['broadcast_id'][:10], 'artist': f['artist'], 'song': f['song'],
          'gap_s': round(f['gap_seconds']) if f['gap_seconds'] is not None else '?',
          'reason': f['reason']} for f in ctx['flagged']],
        ['broadcast', 'artist', 'song', 'gap_s', 'reason'])}
## Set list vs Spinitron, on matched spins

Spinitron wins in the cache -- it was written at air time, the set list beforehand.

{_table(r['field_conflicts'][:200],
        ['broadcast_id', 'field', 'setlist', 'spinitron', 'kept'])}
## Low-confidence workbook matches

Workbook tracks matched to a Spinitron spin by something looser than an exact or
song-exact match. Worth a glance; a wrong match merges two different songs.

{_table(r['weak_matches'][:200],
        ['broadcast_id', 'confidence', 'workbook', 'spinitron', 'basis'])}
""", encoding="utf-8")

    clusters = ctx["clusters"]
    rows = []
    for original, reps in sorted(clusters.items()):
        for rep in reps:
            rows.append({"original": original[:10], "repeat": rep[:10],
                         "confidence": ctx["broadcasts_raw"][rep]["repeat_of_confidence"]})
    band = [{"a": a[:10], "b": b[:10], "score": round(s, 4)}
            for (a, b), s in sorted(ctx["scored"].items(), key=lambda kv: -kv[1])
            if 0.40 <= s <= 0.95]

    (REPORTS / "repeats.md").write_text(f"""# Repeat airings

Detected from track overlap across all {len(ctx['broadcasts_raw'])} broadcasts, before any
per-class merge -- repeats change which class a broadcast belongs to, so this has to run
first.

Clusters are connected components, and the earliest airing in each component is the
original. Every repeat points at that original, never at the airing before it, so no
chain ever forms.

**{len(clusters)} clusters, {len(rows)} repeat airings, {len(ctx['broadcasts_raw']) - len(clusters) - len(rows)} standalone.**

{_table(rows, ['original', 'repeat', 'confidence'])}
## Review band

Pairs scoring between 0.40 and 0.95. The threshold is 0.60; anything here is close enough
to it to be worth a human eye. Force or suppress a pairing in `overrides/repeats.yaml`.

{_table(band, ['a', 'b', 'score'])}
""", encoding="utf-8")

    (REPORTS / "attribution.md").write_text(f"""# Host attribution

`dj_ids` records which Spinitron login was used, **not who hosted**. Two personas display
the identical name "Jim Causey" (173567 is Jim's original account, 174269 a second one),
and 26 of MichaelG's 28 episodes were logged under Jim's original account. So hosts are
derived from workbook presence, with `overrides/participants.yaml` as the authority.

## Persona against workbook presence

{_table(ctx['attribution_rows'], ['dj_ids', 'has_workbook', 'broadcasts'])}
## Broadcasts where the persona breaks the usual alternation

From 2025-07-15 the two personas alternate against MichaelG's weeks. These do not fit,
and are attributed from the workbook regardless:

{_table(ctx['attribution_exceptions'], ['date', 'dj_ids', 'has_workbook', 'attributed_to'])}
""", encoding="utf-8")

    (REPORTS / "unmatched.md").write_text(f"""# Unmatched tracks

## Set-list tracks with no Spinitron spin (`evidence: "planned"`)

These are in the cache but marked as possibly-never-aired. The set list is a plan written
before the show.

{_table(r['planned_only'][:400], ['broadcast_id', 'artist', 'song', 'source'])}
## Workbook tracks with no Spinitron spin

Kept as `logged` -- the workbook is a post-show record, so the gap is Spinitron's.

{_table(r['workbook_only'][:400], ['broadcast_id', 'artist', 'song'])}
## Spinitron spins absent from the workbook

Kept, never dropped: a spin missing from the workbook is usually an unfinished reference
rather than a phantom.

{_table(r['spinitron_only'][:400], ['broadcast_id', 'artist', 'song'])}
""", encoding="utf-8")

    desc_rows = ctx["description_review"]
    body = ["""# Description review

Proposed broadcast descriptions extracted from OneNote prose and Instagram captions, with
the text that was rejected shown alongside so a wrong cut is visible rather than silent.

Nothing here is published as-is. To approve, copy the text into
`overrides/descriptions.yaml` keyed by date; write `skip` to suppress the broadcast
entirely. On the next build an override becomes `description_status: "approved"`.
"""]
    for d in desc_rows:
        src = d.get("source", "unknown")
        body.append(
            f"\n## {d['date']}  [{src}]  (score {d['score']}, {d['status'] or 'not used'})"
        )
        body.append(f"\n_source: `{d['file']}`_\n")
        if d.get("permalink"):
            body.append(f"_permalink: {d['permalink']}_\n")
        body.append("**Proposed:**\n")
        body.append("> " + (d["candidate"] or "_(none -- nothing looked like promo copy)_")
                    .replace("\n", "\n> "))
        if d["rejected"]:
            body.append("\n<details><summary>Rejected remainder</summary>\n\n```\n"
                        + d["rejected"][:1200] + "\n```\n</details>\n")
    (REPORTS / "descriptions-review.md").write_text("\n".join(body) + "\n", encoding="utf-8")

    (REPORTS / "build-summary.md").write_text(ctx["summary"], encoding="utf-8")
