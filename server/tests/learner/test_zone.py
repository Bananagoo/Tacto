"""The zone rule: is the lesson too easy, about right, or too hard right now?"""

from tacto.learner.zone import ZoneTracker


def test_a_new_learner_is_productive_with_a_score_of_zero():
    tracker = ZoneTracker()

    assert tracker.score == 0
    assert tracker.zone == "productive"


def test_three_correct_predictions_is_too_easy():
    tracker = ZoneTracker()
    for _ in range(3):
        tracker.record_correct()

    assert tracker.score == 3
    assert tracker.zone == "too_easy"


def test_three_repeated_errors_is_stuck():
    tracker = ZoneTracker()
    for _ in range(3):
        tracker.record_repeated_error()

    assert tracker.score == -3
    assert tracker.zone == "stuck"


def test_idle_periods_count_like_repeated_errors():
    tracker = ZoneTracker()
    for _ in range(3):
        tracker.record_idle()

    assert tracker.score == -3
    assert tracker.zone == "stuck"


def test_a_mixed_run_stays_productive():
    tracker = ZoneTracker()
    tracker.record_correct()
    tracker.record_repeated_error()
    tracker.record_correct()
    tracker.record_idle()
    tracker.record_correct()

    assert tracker.score == 1
    assert tracker.zone == "productive"


def test_the_zone_changes_exactly_at_plus_three():
    tracker = ZoneTracker()
    tracker.record_correct()
    tracker.record_correct()
    assert tracker.zone == "productive"  # +2

    tracker.record_correct()
    assert tracker.zone == "too_easy"  # +3

    tracker.record_correct()
    assert tracker.zone == "too_easy"  # +4


def test_the_zone_changes_exactly_at_minus_three():
    tracker = ZoneTracker()
    tracker.record_idle()
    tracker.record_repeated_error()
    assert tracker.zone == "productive"  # -2

    tracker.record_idle()
    assert tracker.zone == "stuck"  # -3

    tracker.record_repeated_error()
    assert tracker.zone == "stuck"  # -4


def test_the_zone_is_left_again_when_the_score_comes_back():
    tracker = ZoneTracker()
    for _ in range(3):
        tracker.record_idle()
    tracker.record_correct()

    assert tracker.score == -2
    assert tracker.zone == "productive"
