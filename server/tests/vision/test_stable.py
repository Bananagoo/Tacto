"""A segment changes only after several agreeing frames, and holds under a hand."""

from tacto.vision.classify import Reading
from tacto.vision.stable import FRAMES_TO_CHANGE, StableReadings

WIRE, BULB, EMPTY, UNSURE = (
    Reading("wire", 0.9),
    Reading("bulb", 0.8),
    Reading("empty", 0.0),
    Reading("unsure", 0.3),
)


def feed(stable: StableReadings, reading: Reading, times: int, covered=()) -> Reading | None:
    for _ in range(times):
        stable.update({"0,0-1,0": reading}, covered)
    return stable.current.get("0,0-1,0")


def piece(reading: Reading | None) -> str:
    return "empty" if reading is None else reading.piece


def test_a_piece_appears_only_after_enough_agreeing_frames():
    stable = StableReadings()
    assert piece(feed(stable, WIRE, FRAMES_TO_CHANGE - 1)) == "empty"
    assert piece(feed(stable, WIRE, 1)) == "wire"


def test_one_wrong_frame_changes_nothing():
    stable = StableReadings()
    feed(stable, WIRE, FRAMES_TO_CHANGE)
    assert piece(feed(stable, BULB, 1)) == "wire"
    assert piece(feed(stable, WIRE, 1)) == "wire"
    # The stray frame is forgotten: it does not count towards a later change.
    assert piece(feed(stable, BULB, FRAMES_TO_CHANGE - 1)) == "wire"
    assert piece(feed(stable, BULB, 1)) == "bulb"


def test_frames_must_agree_with_each_other_not_just_differ_from_the_old_answer():
    stable = StableReadings()
    feed(stable, WIRE, FRAMES_TO_CHANGE)
    for _ in range(4):
        feed(stable, BULB, 1)
        feed(stable, EMPTY, 1)
    assert piece(stable.current["0,0-1,0"]) == "wire"


def test_a_piece_taken_away_goes_after_enough_empty_frames():
    stable = StableReadings()
    feed(stable, WIRE, FRAMES_TO_CHANGE)
    assert piece(feed(stable, EMPTY, FRAMES_TO_CHANGE - 1)) == "wire"
    assert piece(feed(stable, EMPTY, 1)) == "empty"


def test_unsure_frames_hold_the_answer_for_as_long_as_they_last():
    stable = StableReadings()
    feed(stable, WIRE, FRAMES_TO_CHANGE)
    assert piece(feed(stable, UNSURE, 200)) == "wire"


def test_a_segment_under_a_hand_holds_whatever_is_read_there():
    stable = StableReadings()
    feed(stable, WIRE, FRAMES_TO_CHANGE)
    assert piece(feed(stable, EMPTY, 50, covered={"0,0-1,0"})) == "wire"
    assert piece(feed(stable, BULB, 50, covered={"0,0-1,0"})) == "wire"
    assert piece(feed(stable, EMPTY, FRAMES_TO_CHANGE)) == "empty"


def test_a_hand_passing_does_not_cancel_a_change_under_way():
    stable = StableReadings()
    feed(stable, WIRE, FRAMES_TO_CHANGE - 1)
    feed(stable, UNSURE, 5)
    assert piece(feed(stable, WIRE, 1)) == "wire"


def test_a_battery_turned_round_is_a_change():
    stable = StableReadings()
    stable_reading = None
    for _ in range(FRAMES_TO_CHANGE):
        stable_reading = feed(stable, Reading("battery", 0.8, "a"), 1)
    assert stable_reading.positive == "a"
    assert feed(stable, Reading("battery", 0.8, "b"), FRAMES_TO_CHANGE - 1).positive == "a"
    assert feed(stable, Reading("battery", 0.8, "b"), 1).positive == "b"


def test_segments_are_independent():
    stable = StableReadings()
    for _ in range(FRAMES_TO_CHANGE):
        stable.update({"0,0-1,0": WIRE, "1,0-2,0": BULB, "2,0-3,0": EMPTY})
    stable.update({"0,0-1,0": EMPTY, "1,0-2,0": BULB, "2,0-3,0": UNSURE})
    assert {s: r.piece for s, r in stable.current.items()} == {
        "0,0-1,0": "wire",
        "1,0-2,0": "bulb",
        "2,0-3,0": "empty",
    }
