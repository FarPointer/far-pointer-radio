"""Read the Spinitron export into Broadcast skeletons and logged Spins.

This is the spine of the cache: every one of the 164 broadcasts exists here, and the
other loaders only enrich what this produces.

Two things in the export need care.

`DJ ID` distinguishes three personas, two of which display the identical name
"Jim Causey" (173567 is Jim's original account, 174269 a second one he created). The
older export had only `DJ Name`, which made the distinction invisible.

That invisibility hid a real artifact: on six broadcasts the persona switched at show
start and Spinitron logged the same track twice, seconds apart, once under each ID. The
two rows are not identical -- one usually carries a UPC or a Local flag the other
lacks -- so they are merged field by field rather than deduplicated by dropping one.
"""
import csv
import datetime as dt
import re
import sys

from paths import CZAUDIT, DJ_NAMES, SHOW_NAME, SPINS_CSV

sys.path.insert(0, str(CZAUDIT))
from matching import norm  # noqa: E402

# Asserted on load. A re-export with different columns should fail loudly here rather
# than silently dropping fields the cache depends on.
EXPECTED_COLUMNS = [
    "Playlist Date", "Playlist Time", "Playlist Date-time", "Playlist Title",
    "Playlist Category", "Playlist Duration", "DJ ID", "DJ Name",
    "Date", "Time", "Date-time", "Artist", "Song", "Release", "Duration",
    "Request", "ISRC", "Song custom field", "Local", "Released",
    "Artist custom field", "Song note", "Label", "UPC",
]

# Cross-persona duplicates all land within ~2 minutes of each other at show start. The
# widest observed is 110s; 180 leaves headroom without reaching the 3,542s+ gaps that
# are genuine repeat plays within a two-hour show.
DUP_WINDOW_SECONDS = 180


def parse_duration(v):
    """Spinitron writes durations as 'M:SS' or 'H:MM:SS', never as an integer."""
    v = (v or "").strip()
    if not re.fullmatch(r"\d+(:\d{2}){1,2}", v):
        return None
    parts = [int(p) for p in v.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def parse_released(v):
    """Spinitron's Released column is year-only. Returns (date, precision)."""
    v = (v or "").strip()
    if re.fullmatch(r"\d{4}", v) and v != "0000":
        return v, "year"
    return None, None            # includes the two literal '0' values in the export


def _row_spin(r):
    """A neutral dict per CSV row; converted to a schema Spin after merging."""
    released, precision = parse_released(r.get("Released"))
    return {
        "dj_id": (r.get("DJ ID") or "").strip(),
        "logged_at": (r.get("Date-time") or "").strip() or None,
        "artist": (r.get("Artist") or "").strip(),
        "song": (r.get("Song") or "").strip(),
        "release": (r.get("Release") or "").strip(),
        "isrc": (r.get("ISRC") or "").strip(),
        "upc": (r.get("UPC") or "").strip(),
        "label": (r.get("Label") or "").strip(),
        "song_note": (r.get("Song note") or "").strip(),
        "duration_seconds": parse_duration(r.get("Duration")),
        "released_date": released,
        "released_precision": precision,
        # The L flag records that the DJ judged the spin local, but not why -- it could
        # be the artist or the label. That is exactly what local_basis "dj_flag" means.
        "local_flag": (r.get("Local") or "").strip().upper() == "L",
        "request": (r.get("Request") or "").strip() != "",
    }


def _sort_key(s):
    return (s["logged_at"] is None, s["logged_at"] or "")


def _key(s):
    return f"{norm(s['artist'])}|{norm(s['song'])}"


def _gap_seconds(a, b):
    if not a["logged_at"] or not b["logged_at"]:
        return None
    ta = dt.datetime.fromisoformat(a["logged_at"])
    tb = dt.datetime.fromisoformat(b["logged_at"])
    return abs((tb - ta).total_seconds())


# Fields where one row may be populated and the other blank. The populated value wins;
# if both are populated and differ, that is a real conflict and gets reported.
MERGE_FIELDS = ("release", "isrc", "upc", "label", "song_note",
                "duration_seconds", "released_date", "released_precision")


def _forced_keys(forced, broadcast_id):
    """Normalised (artist, song) keys a human has told us to merge on this broadcast."""
    out = set()
    for entry in forced or []:
        bid = str(entry.get("broadcast") or "")
        if bid and bid != broadcast_id and bid != broadcast_id[:10]:
            continue
        out.add((norm(entry.get("artist") or ""),
                 norm(entry.get("song") or "", drop_paren=True)))
    return out


def merge_persona_duplicates(spins, broadcast_id, forced=None):
    """Collapse cross-persona double-logs. Returns (spins, merges, flagged).

    `merges` describes what was combined; `flagged` lists duplicate pairs that were
    deliberately left alone -- same-persona duplicates, which are either a genuine
    repeat play within the show or a double-log only a human can adjudicate.

    `forced` carries that human's answer, from overrides/spins.yaml: pairs listed there
    merge even though they are same-persona. The reverse case needs no switch -- leaving
    a duplicate alone is already the default.
    """
    forced_keys = _forced_keys(forced, broadcast_id)
    groups = {}
    for s in spins:
        groups.setdefault(_key(s), []).append(s)

    merges, flagged, drop = [], [], set()
    for key, rows in groups.items():
        if len(rows) < 2:
            continue
        rows = sorted(rows, key=_sort_key)
        gap = _gap_seconds(rows[0], rows[-1])
        personas = {r["dj_id"] for r in rows}

        # An override matches on the normalised artist and song, so it survives the title
        # drift that usually accompanies a re-log ("Deep Mindset (Original Mix)").
        # drop_paren has to be applied to BOTH sides: _forced_keys strips the parenthetical
        # from the override's bare title, so stripping it here too is what actually makes
        # the drifted title match. On one side only it is a no-op.
        forced_here = len(rows) == 2 and any(
            (norm(rows[0]["artist"]), norm(s, drop_paren=True)) in forced_keys
            for s in (rows[0]["song"], rows[1]["song"]))

        mergeable = forced_here or (len(rows) == 2 and len(personas) == 2
                                    and gap is not None and gap <= DUP_WINDOW_SECONDS)
        if not mergeable:
            flagged.append({
                "broadcast_id": broadcast_id, "key": key,
                "count": len(rows), "gap_seconds": gap,
                "dj_ids": sorted(personas),
                "artist": rows[0]["artist"], "song": rows[0]["song"],
                "reason": ("same persona" if len(personas) == 1 else
                           "more than two rows" if len(rows) > 2 else
                           "outside the duplicate window"),
            })
            continue

        keep, other = rows[0], rows[1]        # keep the earlier logged_at
        conflicts = []
        for f in MERGE_FIELDS:
            if not keep.get(f) and other.get(f):
                keep[f] = other[f]
            elif keep.get(f) and other.get(f) and keep[f] != other[f]:
                conflicts.append({"field": f, "kept": keep[f], "discarded": other[f]})
        keep["local_flag"] = keep["local_flag"] or other["local_flag"]
        keep["request"] = keep["request"] or other["request"]
        drop.add(id(other))
        merges.append({
            "broadcast_id": broadcast_id, "artist": keep["artist"], "song": keep["song"],
            "gap_seconds": gap, "dj_ids": sorted(personas), "conflicts": conflicts,
            "forced": forced_here,
        })

    return [s for s in spins if id(s) not in drop], merges, flagged


def load(forced_merges=None):
    """Returns (broadcasts, merges, flagged).

    `broadcasts` maps broadcast id -> dict with the Spinitron-derived fields and a
    `raw_spins` list, sorted by logged_at. Converting those into schema Spins is
    merge.py's job, because class A and B reorder and annotate them first.
    """
    with open(SPINS_CSV, encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in EXPECTED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(
                f"{SPINS_CSV.name} is missing expected column(s): {missing}\n"
                "The cache depends on the newer export format (DJ ID, Playlist "
                "Date-time, Playlist Duration). Re-export from Spinitron with all "
                "columns enabled."
            )
        rows = list(reader)

    broadcasts = {}
    for r in rows:
        bid = (r.get("Playlist Date-time") or "").strip()
        if not bid:
            raise SystemExit("a row has no Playlist Date-time; cannot key the broadcast")
        b = broadcasts.setdefault(bid, {
            "id": bid,
            "air_datetime": bid,
            "date": bid[:10],
            "show_name": SHOW_NAME,
            "title": None,
            "dj_ids": set(),
            "scheduled_duration_minutes": None,
            "raw_spins": [],
        })
        raw_title = (r.get("Playlist Title") or "").strip()
        # The bare show name is not a title; anything else is kept verbatim, unparsed.
        b["title"] = raw_title if raw_title and raw_title != SHOW_NAME else b["title"]
        b["dj_ids"].add((r.get("DJ ID") or "").strip())
        dur = (r.get("Playlist Duration") or "").strip()
        if dur.isdigit():
            b["scheduled_duration_minutes"] = int(dur)
        b["raw_spins"].append(_row_spin(r))

    all_merges, all_flagged = [], []
    for b in broadcasts.values():
        b["raw_spins"].sort(key=_sort_key)
        b["raw_spins"], merges, flagged = merge_persona_duplicates(
            b["raw_spins"], b["id"], forced_merges)
        b["dj_ids"] = sorted(x for x in b["dj_ids"] if x)
        b["dj_names"] = sorted({DJ_NAMES.get(d, d) for d in b["dj_ids"]})
        all_merges += merges
        all_flagged += flagged

    return broadcasts, all_merges, all_flagged


if __name__ == "__main__":
    bcs, merges, flagged = load()
    spins = sum(len(b["raw_spins"]) for b in bcs.values())
    print(f"broadcasts: {len(bcs)}   spins after merge: {spins}")
    print(f"cross-persona merges: {len(merges)}")
    for m in merges:
        print(f"  {m['broadcast_id'][:10]}  {m['artist']} - {m['song']}  "
              f"gap={m['gap_seconds']:.0f}s  ids={m['dj_ids']}  "
              f"conflicts={[c['field'] for c in m['conflicts']]}")
    print(f"\nflagged duplicates (not merged): {len(flagged)}")
    for f in flagged:
        g = f"{f['gap_seconds']:.0f}s" if f["gap_seconds"] is not None else "?"
        print(f"  {f['broadcast_id'][:10]}  {f['artist']} - {f['song']}  "
              f"gap={g}  {f['reason']}")
