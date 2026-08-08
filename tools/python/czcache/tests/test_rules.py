import merge
import repeats
from rules import RULES, RULES_PATH


def test_rule_thresholds_are_loaded_from_yaml():
    assert RULES_PATH.exists()
    assert repeats.REPLAY_FLOOR == float(RULES["repeat_detection"]["replay_floor"])
    assert merge.DESCRIPTION_PROPOSED_SCORE_FLOOR == float(
        RULES["description_gate"]["proposed_score_floor"]
    )


def test_apply_description_uses_configurable_score_floor(monkeypatch):
    monkeypatch.setattr(merge, "DESCRIPTION_PROPOSED_SCORE_FLOOR", 0.80)

    desc, status = merge.apply_description(
        {"air_datetime": "2026-07-07T20:30:00-07:00"},
        {"candidate": "candidate text", "score": 0.75},
        {},
    )

    assert desc is None
    assert status is None


def test_repeat_assignment_uses_configurable_replay_floor(monkeypatch):
    first = "2026-01-01T20:30:00-08:00"
    second = "2026-01-08T20:30:00-08:00"
    broadcasts = {first: {"raw_spins": []}, second: {"raw_spins": []}}

    monkeypatch.setattr(repeats, "score_pairs", lambda _: {(first, second): 0.65})
    monkeypatch.setattr(repeats, "REPLAY_FLOOR", 0.70)

    _, clusters = repeats.assign(broadcasts)

    assert clusters == {}
    assert broadcasts[second].get("first_broadcast_id") is None
