"""Turn the loaded sources into finished Broadcast and Spin records.

Each broadcast falls into exactly one class with a different canonical source, and the
merge strategy differs accordingly:

  A  MichaelG's workbook is the truth about what played and in what order; Spinitron
     fills in the machine-readable metadata the workbook has no column for.
  B  A set list and a Spinitron log, neither authoritative. The set list is a plan
     written before air and may list tracks that never played; Spinitron is the as-aired
     log but is demonstrably incomplete. Emit the union and let `evidence` say which.
  C  Spinitron alone. Direct projection.

Class A takes precedence over B: three of MichaelG's episodes were re-aired on weeks with
no workbook of their own, and demoting them would strip his attribution, his artist
origins, and his notes.
"""
import sys

import locality
from model import make_broadcast, make_participant, make_spin, resequence, spin_id
from paths import CZAUDIT, HOST_JIM, HOST_MICHAELG, SHOW_NAME
from rules import RULES

sys.path.insert(0, str(CZAUDIT))
from build_audit import match_episode  # noqa: E402

# MichaelG has a Spinitron persona even though almost none of his shows were logged under
# it; the participant record names the person, so the ID belongs here regardless.
PARTICIPANT_DJ_IDS = {HOST_MICHAELG: "189849", HOST_JIM: "173567"}
DESCRIPTION_PROPOSED_SCORE_FLOOR = float(
    RULES["description_gate"]["proposed_score_floor"]
)


def classify(broadcasts, workbooks, bindings, clusters):
    """Assign each broadcast to class A, B, or C.

    A broadcast is class A if it has a workbook OR repeats one. That second condition is
    the whole reason repeat detection runs before this.
    """
    wb_dates = set(workbooks)
    a = {bid for bid, b in broadcasts.items() if b["date"] in wb_dates}
    for original, repeats in clusters.items():
        if broadcasts[original]["date"] in wb_dates:
            a |= set(repeats)
    b = {bid for bid in bindings if bid not in a}
    c = set(broadcasts) - a - b
    return {**{k: "A" for k in a}, **{k: "B" for k in b}, **{k: "C" for k in c}}


# ------------------------------------------------------------------ spin builders

def _spinitron_spin(bid, raw, sources=("spinitron",), evidence="logged", extra=None):
    local, basis, label_origin = locality.resolve(
        artist_origin_raw=(extra or {}).get("origin"),
        label_raw=(extra or {}).get("label") or raw.get("label"),
        dj_flag=raw.get("local_flag", False),
    )
    e = extra or {}
    return make_spin(
        id=spin_id(bid, f"spinitron:{raw['logged_at']}:{raw['artist']}|{raw['song']}"),
        broadcast_id=bid,
        evidence=evidence,
        logged_at=raw["logged_at"],
        offset_seconds=e.get("offset_seconds"),
        artist=e.get("artist") or raw["artist"],
        song=e.get("song") or raw["song"],
        # The workbook names releases and labels more carefully than the booth does,
        # so where it has a value it wins; Spinitron fills the blanks.
        release=e.get("release") or raw["release"],
        label=e.get("label") or raw["label"],
        isrc=raw["isrc"],
        upc=raw["upc"],
        duration_seconds=raw["duration_seconds"],
        released_date=e.get("released_date") or raw["released_date"],
        released_precision=e.get("released_precision") or raw["released_precision"],
        local=local,
        local_basis=basis,
        artist_origin_raw=e.get("origin"),
        label_origin_raw=label_origin,
        request=raw["request"],
        song_note=raw["song_note"],
        publish_note=e.get("notes") or raw["song_note"],
        sources=sources,
    )


def _source_only_spin(bid, track, source, evidence, discriminator):
    local, basis, label_origin = locality.resolve(
        artist_origin_raw=track.get("origin"),
        label_raw=track.get("label"),
    )
    return make_spin(
        id=spin_id(bid, discriminator),
        broadcast_id=bid,
        evidence=evidence,
        logged_at=None,
        offset_seconds=track.get("offset_seconds"),
        artist=track["artist"],
        song=track["song"],
        release=track.get("release") or track.get("album"),
        label=track.get("label"),
        released_date=track.get("released_date"),
        released_precision=track.get("released_precision"),
        local=local,
        local_basis=basis,
        artist_origin_raw=track.get("origin"),
        label_origin_raw=label_origin,
        publish_note=track.get("notes"),
        sources=[source],
    )


def _splice_by_time(primary, extras):
    """Place time-stamped extras among an ordered primary list.

    `primary` is [(order_key, spin)] in canonical order; `extras` are spins carrying a
    logged_at but no position. Each extra lands after the last primary spin logged before
    it, which keeps a Spinitron-only track next to the tracks it actually played beside
    rather than dumped at the end.
    """
    anchors = [(s["logged_at"], k) for k, s in primary if s.get("logged_at")]
    anchors.sort()
    placed = []
    for s in extras:
        key = -1.0
        if s.get("logged_at"):
            before = [k for t, k in anchors if t <= s["logged_at"]]
            key = before[-1] if before else -1.0
        placed.append((key + 0.5, s))
    return placed


def _ordered(items):
    return [s for _, s in sorted(items, key=lambda kv: (kv[0], kv[1].get("logged_at") or ""))]


# ------------------------------------------------------------------ per-class merges

def merge_class_a(bid, broadcast, workbook, report):
    """Workbook canonical; Spinitron fills metadata."""
    tracks = [dict(t) for t in workbook["tracks"]]
    spins = broadcast["raw_spins"]
    matches, wb_only, spin_only = match_episode(tracks, spins)

    by_track = {id(m["track"]): m for m in matches}
    primary, out_spins = [], []
    for t in tracks:
        m = by_track.get(id(t))
        if m:
            s = _spinitron_spin(bid, m["spin"], sources=("spinitron", "michaelg"),
                                extra=t)
            if m["confidence"] not in ("exact", "strong"):
                report["weak_matches"].append({
                    "broadcast_id": bid, "confidence": m["confidence"],
                    "basis": m["basis"], "workbook": f"{t['artist']} - {t['song']}",
                    "spinitron": f"{m['spin']['artist']} - {m['spin']['song']}"})
        else:
            s = _source_only_spin(bid, t, "michaelg", "logged",
                                  f"michaelg:{t['seq']}:{t['artist']}|{t['song']}")
            report["workbook_only"].append({
                "broadcast_id": bid, "artist": t["artist"], "song": t["song"]})
        primary.append((float(t["seq"]), s))
        out_spins.append(s)

    # A spin absent from the workbook is usually an unfinished reference rather than a
    # phantom, so it is kept and reported -- never dropped.
    extras = []
    for raw in spin_only:
        s = _spinitron_spin(bid, raw)
        extras.append(s)
        report["spinitron_only"].append({
            "broadcast_id": bid, "artist": raw["artist"], "song": raw["song"]})

    return _ordered(primary + _splice_by_time(primary, extras))


def merge_class_b(bid, broadcast, setlist, report):
    """Set list and Spinitron merged; disagreements reported, union emitted."""
    tracks = [dict(t) for t in setlist["tracks"]]
    spins = broadcast["raw_spins"]
    matches, list_only, spin_only = match_episode(tracks, spins)
    source = setlist["source"]

    by_spin = {id(m["spin"]): m for m in matches}
    primary = []
    for i, raw in enumerate(spins):
        m = by_spin.get(id(raw))
        if m:
            t = m["track"]
            # Spinitron was written at air time, so it wins on the fields both carry;
            # the set list contributes only what Spinitron has no column for.
            s = _spinitron_spin(bid, raw, sources=("spinitron", source), extra={
                "offset_seconds": t.get("offset_seconds"),
                "notes": t.get("notes") or raw.get("song_note"),
            })
            for field, a, b in (("artist", t["artist"], raw["artist"]),
                                ("song", t["song"], raw["song"]),
                                ("release", t.get("album"), raw["release"])):
                if a and b and a.strip().lower() != (b or "").strip().lower():
                    report["field_conflicts"].append({
                        "broadcast_id": bid, "field": field,
                        "setlist": a, "spinitron": b, "kept": "spinitron"})
        else:
            s = _spinitron_spin(bid, raw)
        primary.append((float(i + 1), s))

    # Set-list-only tracks may never have aired. This is what `evidence` exists for.
    matched_seqs = {m["track"]["seq"]: m["spin"] for m in matches}
    planned = []
    for t in list_only:
        s = _source_only_spin(bid, t, source, "planned",
                              f"{source}:{t['seq']}:{t['artist']}|{t['song']}")
        # Position it after whichever set-list neighbour did get logged.
        before = [sq for sq in matched_seqs if sq < t["seq"]]
        anchor = 0.0
        if before:
            nb = matched_seqs[max(before)]
            anchor = next((k for k, sp in primary if sp["logged_at"] == nb["logged_at"]), 0.0)
        planned.append((anchor + 0.5, s))
        report["planned_only"].append({
            "broadcast_id": bid, "artist": t["artist"], "song": t["song"],
            "source": source})

    return _ordered(primary + planned)


def merge_class_c(bid, broadcast):
    """Spinitron alone."""
    return [_spinitron_spin(bid, raw) for raw in broadcast["raw_spins"]]


# ------------------------------------------------------------------ attribution

def derive_participants(broadcast, klass, overrides):
    """Who actually hosted -- deliberately not read from dj_ids.

    Both "Jim Causey" personas are Jim's, and 26 of MichaelG's 28 episodes were logged
    under Jim's original account, so the login says nothing about the host. Workbook
    presence does: a MichaelG workbook exists only for shows he hosted. An override wins
    over both, for genuinely co-hosted shows and for the exceptions.
    """
    override = overrides.get(broadcast["date"]) or overrides.get(broadcast["id"])
    if override:
        return [make_participant(p["name"], PARTICIPANT_DJ_IDS.get(p["name"]),
                                 p.get("coverage", "full"))
                for p in override]
    name = HOST_MICHAELG if klass == "A" else HOST_JIM
    return [make_participant(name, PARTICIPANT_DJ_IDS.get(name), "full")]


def apply_description(bc, prose, overrides):
    """Three-state description gate.

    An unreviewed guess must never be indistinguishable from approved copy, because the
    website reads this field. So: an override is "approved", a confident extraction is
    "proposed", and anything weaker leaves the field null.
    """
    override = overrides.get(bc["air_datetime"]) or overrides.get(bc["air_datetime"][:10])
    if override is not None:
        if str(override).strip().lower() == "skip":
            return None, None
        return str(override).strip(), "approved"
    if prose and prose.get("candidate") and prose["score"] >= DESCRIPTION_PROPOSED_SCORE_FLOOR:
        return prose["candidate"], "proposed"
    return None, None


# ------------------------------------------------------------------ top level

def build_broadcast(bid, broadcast, klass, workbook, setlist, prose, ov, report):
    if klass == "A":
        spins = merge_class_a(bid, broadcast, workbook, report)
        sources = {"spinitron", "michaelg"}
    elif klass == "B":
        spins = merge_class_b(bid, broadcast, setlist, report)
        sources = {"spinitron", setlist["source"]}
    else:
        spins = merge_class_c(bid, broadcast)
        sources = {"spinitron"}

    resequence(spins)

    # Episode numbers survive only where a set list names one: workbook filenames carry
    # none and 96% of Spinitron titles are the bare show name.
    episode = setlist.get("episode_number") if setlist else None

    bc = make_broadcast(
        id=bid,
        air_datetime=broadcast["air_datetime"],
        show_name=SHOW_NAME,
        episode_number=episode,
        title=broadcast["title"],
        scheduled_duration_minutes=broadcast["scheduled_duration_minutes"],
        dj_ids=broadcast["dj_ids"],
        spinitron_playlist_ids=broadcast["spinitron_playlist_ids"],
        mixcloud_url=(ov["publication_links"].get(broadcast["date"]) or {}).get(
            "mixcloud_url"
        ),
        webpage_url=(ov["publication_links"].get(broadcast["date"]) or {}).get(
            "webpage_url"
        ),
        first_broadcast_id=broadcast.get("first_broadcast_id"),
        repeat_of_source=broadcast.get("repeat_of_source"),
        repeat_of_confidence=broadcast.get("repeat_of_confidence"),
        participants=derive_participants(broadcast, klass, ov["participants"]),
        sources=sources | ({"onenote"} if prose and prose.get("candidate") else set()),
        spins=spins,
    )
    desc, status = apply_description(bc, prose, ov["descriptions"])
    bc["description"], bc["description_status"] = desc, status
    if desc is None:
        bc["description_status"] = None
    return bc
