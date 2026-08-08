"""Find repeat airings across the whole archive and point each at its original.

This runs before any per-class merge, for two reasons.

Repeats are visible in the spin data itself, not just in set lists, so restricting
detection to the 68 broadcasts that have a set list would miss the rest. Three of
MichaelG's episodes were re-aired on weeks that have no workbook of their own; without
this pass they would look like ordinary Spinitron-only broadcasts and lose his
attribution, his artist-origin notes, and his comments.

And repeats form chains. Episode 021 aired four times; a nearest-match pass would point
each airing at the one before it, which is exactly what the schema forbids -- every
repeat must point at the ORIGINAL so no chain ever forms. Connected components make
that unambiguous: cluster on any pairing above the threshold, then take the earliest
date in each component as the original.
"""
import sys

from paths import CZAUDIT
from rules import RULES

sys.path.insert(0, str(CZAUDIT))
from matching import overlap  # noqa: E402

# Inherited from czaudit.scrape_site.bind_broadcasts, which uses 0.60 to decide a
# published page describes a replay rather than the week it was posted. `overlap` is
# deliberately strict (exact normalised artist+song), and neighbouring weeks share very
# few exact pairs, so this does not fire on merely similar programming.
REPLAY_FLOOR = float(RULES["repeat_detection"]["replay_floor"])

# Pairs in this band are written to the review report. Below it, nothing interesting;
# above it, not worth a human's attention.
REVIEW_BAND = tuple(RULES["repeat_detection"]["review_band"])


def _find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _union(parent, a, b):
    ra, rb = _find(parent, a), _find(parent, b)
    if ra != rb:
        parent[max(ra, rb)] = min(ra, rb)


def score_pairs(broadcasts):
    """Every broadcast pair with a non-zero track overlap, as {(a, b): score}."""
    ids = sorted(broadcasts)
    scored = {}
    for i, a in enumerate(ids):
        ta = broadcasts[a]["raw_spins"]
        for b in ids[i + 1:]:
            s = overlap(ta, broadcasts[b]["raw_spins"])
            if s > 0:
                scored[(a, b)] = s
    return scored


def assign(broadcasts, forced=(), suppressed=()):
    """Cluster repeats and stamp the repeat fields onto each broadcast.

    `forced` and `suppressed` are (id, id) pairs from overrides/repeats.yaml that add or
    remove a pairing regardless of score, for the cases where the track list changed
    enough between airings that overlap alone gets it wrong.

    Returns (scored_pairs, clusters) for reporting; broadcasts are mutated in place.
    """
    scored = score_pairs(broadcasts)
    suppressed = {tuple(sorted(p)) for p in suppressed}
    forced = {tuple(sorted(p)) for p in forced}

    linked = {p for p, s in scored.items() if s >= REPLAY_FLOOR}
    linked = (linked | forced) - suppressed

    parent = {b: b for b in broadcasts}
    for a, b in linked:
        _union(parent, a, b)

    components = {}
    for b in broadcasts:
        components.setdefault(_find(parent, b), []).append(b)

    clusters = {}
    for members in components.values():
        if len(members) < 2:
            continue
        members.sort()                      # ids are ISO datetimes, so this is oldest-first
        original, repeats = members[0], members[1:]
        clusters[original] = repeats
        for r in repeats:
            key = tuple(sorted((original, r)))
            # Score against the original, not against whatever linked it into the
            # cluster -- that is the relationship the field actually records.
            conf = scored.get(key)
            broadcasts[r]["first_broadcast_id"] = original
            broadcasts[r]["repeat_of_source"] = "inferred"
            broadcasts[r]["repeat_of_confidence"] = round(conf, 4) if conf is not None else None

    return scored, clusters


def mark_documented(broadcast, original_id):
    """Promote a repeat to 'documented' when a source states it outright.

    Documented beats inferred, and confidence goes null: a stated repeat is not a
    similarity measurement and should not carry one.
    """
    broadcast["first_broadcast_id"] = original_id
    broadcast["repeat_of_source"] = "documented"
    broadcast["repeat_of_confidence"] = None


if __name__ == "__main__":
    import load_spinitron

    bcs, _, _ = load_spinitron.load()
    scored, clusters = assign(bcs)
    total = sum(len(v) for v in clusters.values())
    print(f"clusters: {len(clusters)}   repeat airings: {total}   "
          f"standalone: {len(bcs) - len(clusters) - total}")
    for orig, reps in sorted(clusters.items()):
        print(f"\n  original {orig[:10]}")
        for r in reps:
            print(f"    repeat {r[:10]}  confidence "
                  f"{bcs[r]['repeat_of_confidence']}")
