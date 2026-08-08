"""Record constructors for the cache, mirroring playlists/schema.ts.

Every Broadcast and Spin in the cache is built here so the emitted JSON has a stable
key set and key order regardless of which loader produced it. A rebuild that changes
nothing must produce a zero-line diff, and that only holds if absent fields are written
explicitly as null rather than omitted.

The null convention from the schema is enforced in one place: `clean()` turns empty
strings into None, so no loader has to remember to do it.
"""
import hashlib

SOURCE_NAMES = ("spinitron", "michaelg", "wordpress", "onenote")


def clean(v):
    """Empty string -> None, per the schema's null convention. Whitespace-only too."""
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def spin_id(broadcast_id: str, discriminator: str) -> str:
    """Opaque, stable spin key.

    Deliberately NOT derived from sequence: reconciliation inserts spins and renumbers
    everything after them, so a sequence-derived id would change identity on every fix.
    Derived instead from the broadcast plus something intrinsic to the spin, which makes
    it reproducible across rebuilds without storing a counter.
    """
    h = hashlib.sha1(f"{broadcast_id}\x00{discriminator}".encode())
    return f"sp_{h.hexdigest()[:16]}"


def make_broadcast(**kw):
    """A Broadcast with every schema field present. Unspecified fields take their
    documented empty value (null, or [] for the array fields)."""
    b = {
        "id": kw["id"],
        "air_datetime": kw["air_datetime"],
        "show_name": kw.get("show_name"),
        "episode_number": kw.get("episode_number"),
        "title": clean(kw.get("title")),
        "participants": kw.get("participants") or [],
        "is_prerecorded": bool(kw.get("is_prerecorded", False)),
        "description": clean(kw.get("description")),
        "description_status": kw.get("description_status"),
        "mixcloud_url": clean(kw.get("mixcloud_url")),
        "webpage_url": clean(kw.get("webpage_url")),
        "scheduled_duration_minutes": kw.get("scheduled_duration_minutes"),
        "dj_ids": sorted(kw.get("dj_ids") or []),
        "spinitron_playlist_ids": sorted(kw.get("spinitron_playlist_ids") or []),
        "first_broadcast_id": kw.get("first_broadcast_id"),
        "repeat_of_source": kw.get("repeat_of_source"),
        "repeat_of_confidence": kw.get("repeat_of_confidence"),
        "sources": sort_sources(kw.get("sources")),
        "spins": kw.get("spins") or [],
    }
    if b["description"] is None:
        b["description_status"] = None
    return b


def make_participant(name: str, dj_id=None, coverage: str = "full"):
    return {"name": name, "dj_id": dj_id, "coverage": coverage}


def make_spin(**kw):
    """A Spin with every schema field present."""
    return {
        "id": kw["id"],
        "broadcast_id": kw["broadcast_id"],
        "evidence": kw["evidence"],
        "sequence": kw.get("sequence"),
        "logged_at": clean(kw.get("logged_at")),
        "offset_seconds": kw.get("offset_seconds"),
        "artist": kw["artist"],
        "artist_key": kw.get("artist_key"),
        "song": kw["song"],
        "release": clean(kw.get("release")),
        "isrc": clean(kw.get("isrc")),
        "upc": clean(kw.get("upc")),
        "duration_seconds": kw.get("duration_seconds"),
        "released_date": clean(kw.get("released_date")),
        "released_precision": kw.get("released_precision"),
        "label": clean(kw.get("label")),
        "local": kw.get("local"),
        "local_basis": sorted(set(kw.get("local_basis") or [])),
        "artist_origin_raw": clean(kw.get("artist_origin_raw")),
        "label_origin_raw": clean(kw.get("label_origin_raw")),
        "request": bool(kw.get("request", False)),
        "song_note": clean(kw.get("song_note")),
        "publish_note": clean(kw.get("publish_note")),
        "sources": sort_sources(kw.get("sources")),
    }


def sort_sources(names):
    """Sources in a fixed order so the emitted array never churns."""
    s = set(names or [])
    unknown = s - set(SOURCE_NAMES)
    if unknown:
        raise ValueError(f"unknown source name(s): {sorted(unknown)}")
    return [n for n in SOURCE_NAMES if n in s]


def resequence(spins):
    """Renumber `sequence` 1..n in the spins' current list order, in place."""
    for i, s in enumerate(spins, 1):
        s["sequence"] = i
    return spins
