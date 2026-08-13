"""Regression tests for the three bugs that let a human decision silently do nothing.

Every one of these shipped documented, with a worked example, and had no effect. They are
the reason the description review gate reported PASS for weeks while not being wired up at
all. Each test asserts the wiring, not the outcome — a check that only looks at the built
cache cannot tell "the gate holds" from "the gate is not connected".
"""
import datetime as dt

import build
import load_prose
import load_spinitron
import merge
import pytest


def _write(overrides_dir, name, text):
    (overrides_dir / name).write_text(text, encoding="utf-8")


def test_unquoted_iso_date_override_key_reaches_the_lookup(tmp_path, monkeypatch):
    """PyYAML resolves `2026-07-07:` to datetime.date, not str.

    The lookup on the other side uses the string form of the broadcast id, so every
    unquoted entry — the obvious way to write a date — missed silently.
    """
    monkeypatch.setattr(build, "OVERRIDES", tmp_path)
    _write(tmp_path, "descriptions.yaml", "2026-07-07: an approved blurb\n")
    _write(tmp_path, "participants.yaml", '2026-07-07:\n  - "MichaelG"\n')

    overrides = build.load_overrides()

    assert overrides["descriptions"]["2026-07-07"] == "an approved blurb"
    assert overrides["participants"]["2026-07-07"] == ["MichaelG"]
    assert not any(isinstance(k, dt.date) for k in overrides["descriptions"])


def test_quoted_and_unquoted_date_keys_normalise_alike(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OVERRIDES", tmp_path)
    _write(tmp_path, "descriptions.yaml", '"2026-07-07": quoted\n2026-07-14: unquoted\n')

    descriptions = build.load_overrides()["descriptions"]

    assert descriptions == {"2026-07-07": "quoted", "2026-07-14": "unquoted"}


def test_absent_override_files_are_not_an_error(tmp_path, monkeypatch):
    monkeypatch.setattr(build, "OVERRIDES", tmp_path)

    overrides = build.load_overrides()

    assert overrides["descriptions"] == {}
    assert overrides["participants"] == {}
    assert overrides["repeats"] == {}
    assert overrides["spins"] == {}


def _spin(dj_id, song, logged_at, artist="Steve Roach"):
    return {
        "dj_id": dj_id,
        "logged_at": logged_at,
        "artist": artist,
        "song": song,
        "release": "",
        "isrc": "",
        "upc": "",
        "label": "",
        "song_note": "",
        "duration_seconds": None,
        "released_date": None,
        "released_precision": None,
        "local_flag": False,
        "request": False,
    }


def test_same_persona_duplicate_is_left_alone_without_an_override():
    """The default, and the behaviour the override exists to opt out of."""
    spins = [
        _spin("173567", "Deep Mindset", "2026-07-07T20:40:00-07:00"),
        _spin("173567", "Deep Mindset", "2026-07-07T20:44:00-07:00"),
    ]

    kept, merges, flagged = load_spinitron.merge_persona_duplicates(spins, "2026-07-07")

    assert len(kept) == 2
    assert not merges
    assert flagged and flagged[0]["reason"] == "same persona"


def test_forced_merge_survives_the_title_drift_that_accompanies_a_relog():
    """`spins.yaml merge_duplicates` was parsed and dropped on the floor.

    It has to match on the normalised artist and song, because a re-log almost always
    drifts the title — "Deep Mindset (Original Mix)" vs "Deep Mindset". Grouping alone
    puts those in two singleton groups, where no override is ever consulted.
    """
    spins = [
        _spin("173567", "Deep Mindset", "2026-07-07T20:40:00-07:00"),
        _spin("173567", "Deep Mindset (Original Mix)", "2026-07-07T21:55:00-07:00"),
    ]
    forced = [{"broadcast": "2026-07-07", "artist": "Steve Roach", "song": "Deep Mindset"}]
    applied = set()

    kept, merges, flagged = load_spinitron.merge_persona_duplicates(
        spins, "2026-07-07", forced=forced, applied=applied)

    assert len(kept) == 1, "the override did not fire"
    assert merges
    assert not flagged
    assert applied == {0}, "an override that fires must report that it fired"


def test_forced_merge_naming_a_pair_that_does_not_exist_reports_nothing_applied():
    """An inert override must be visible, not silent — that is the whole failure mode."""
    spins = [
        _spin("173567", "Structures from Silence", "2026-07-07T20:40:00-07:00"),
    ]
    forced = [{"broadcast": "2026-07-07", "artist": "Steve Roach", "song": "Deep Mindset"}]
    applied = set()

    load_spinitron.merge_persona_duplicates(spins, "2026-07-07", forced=forced, applied=applied)

    assert applied == set()


NOTE = """Convergence Zone.012 - May 30 2023
Tuesday, May 30, 2023
8:30 PM

Tonight on Convergence Zone we drift through the long ambient tail of the Pacific
Northwest spring, with new work from Seattle artists alongside the records that taught
them how to hold a drone.

Tracks:
Steve Roach - Structures from Silence
"""


def test_prose_extraction_does_not_stop_on_the_exported_title_line():
    """OneNote writes the note's own title as the first body line.

    That line is short, so the scratch heuristic read it as working notes and cut
    extraction at line one. Fixing it took proposed descriptions from 21 to 35 and notes
    yielding nothing from 40 to 5.
    """
    candidate, rejected, score = load_prose.extract(NOTE)

    assert candidate, "extraction stopped before it started"
    assert "Convergence Zone.012" not in candidate, "the exported title is not promo copy"
    assert "drift through the long ambient tail" in candidate
    assert "Structures from Silence" in rejected, (
        "the track listing must land in `rejected`, not vanish")
    assert score > 0


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Convergence Zone.012 - May 30 2023", None),
        ("Episode 049 - 03.19.2024 - Spring Equinox", "Spring Equinox"),
        ("Episode.048 - 03.12.2024 - 1 Yr Anniversary", "Anniversary"),
        ("Episode 059 - 06.20.2024 - Summer Solstice 2024", "Summer Solstice"),
        ("Episode 062 - 07.23.24 - video games pledge drive", "Video Games Pledge Drive"),
        ("03.18.2025 - Spring Fund Drive Pt2", "Spring Fund Drive"),
        ("07.15.2025 - heat advisory", "Heat Advisory"),
        ("09.09.2025 - End of Summer 2025", "End of Summer"),
        ("07.29.25", None),
        ("2025.11.04", None),
        ("Feb 2025", None),
    ],
)
def test_onenote_episode_titles_keep_only_meaningful_words(title, expected):
    raw = f"---\ntitle: {title}\n---\n"

    assert load_prose.extract_episode_title(raw) == expected


@pytest.mark.parametrize(
    ("onenote_title", "expected"),
    [("Spring Equinox", "Spring Equinox"), (None, None)],
)
def test_matching_onenote_note_replaces_spinitron_title(onenote_title, expected):
    bid = "2024-03-19T22:30:00-0700"
    broadcast = {
        "id": bid,
        "date": "2024-03-19",
        "air_datetime": bid,
        "title": "03.19.2024 - Jim Causey",
        "scheduled_duration_minutes": 120,
        "dj_ids": ["173567"],
        "spinitron_playlist_ids": [],
        "raw_spins": [],
    }
    overrides = {
        "descriptions": {},
        "participants": {},
        "publication_links": {},
    }

    result = merge.build_broadcast(
        bid,
        broadcast,
        "C",
        None,
        None,
        None,
        {"episode_title": onenote_title},
        overrides,
        {},
    )

    assert result["title"] == expected
    assert "onenote" in result["sources"]


def test_onenote_collection_page_is_not_linked_as_an_episode(tmp_path, monkeypatch):
    monkeypatch.setattr(load_prose, "ONENOTE_DIR", tmp_path)
    (tmp_path / "2023 Playlists - Convergence Zone.md").write_text(
        "---\n"
        "title: 2023 Playlists - Convergence Zone\n"
        "created: 2023-12-20\n"
        "---\n",
        encoding="utf-8",
    )

    assert load_prose.load({"2023-12-26"}) == {}
