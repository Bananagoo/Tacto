"""Kicking the autofocus when the mat cannot be read. No camera is touched."""

from itertools import pairwise

from tacto.vision.focus import KICK_AFTER_BLIND_S, KICK_EVERY_S, FocusKeeper


class Clock:
    def __init__(self) -> None:
        self.now = 50.0

    def __call__(self) -> float:
        return self.now


def keeper():
    clock, kicked = Clock(), []
    return FocusKeeper(lambda: kicked.append(clock.now) or True, clock=clock), clock, kicked


def run(focus, clock, seconds: float, any_corner: bool) -> None:
    for _ in range(round(seconds * 30)):
        clock.now += 1 / 30
        focus.saw(any_corner)


def test_a_readable_mat_is_left_alone():
    focus, clock, kicked = keeper()
    run(focus, clock, 30, any_corner=True)
    assert kicked == []


def test_a_hand_passing_over_the_markers_does_not_set_off_a_sweep():
    focus, clock, kicked = keeper()
    for _ in range(5):
        run(focus, clock, KICK_AFTER_BLIND_S * 0.8, any_corner=False)
        run(focus, clock, 0.2, any_corner=True)
    assert kicked == []


def test_a_mat_that_stays_unreadable_gets_one_kick_then_time_to_settle():
    focus, clock, kicked = keeper()
    start = clock.now
    run(focus, clock, KICK_AFTER_BLIND_S + 0.5, any_corner=False)
    assert len(kicked) == 1 and kicked[0] - start >= KICK_AFTER_BLIND_S
    run(focus, clock, KICK_EVERY_S - 1.0, any_corner=False)
    assert len(kicked) == 1


def test_it_kicks_again_if_the_first_sweep_did_not_bring_the_mat_back():
    focus, clock, kicked = keeper()
    run(focus, clock, KICK_AFTER_BLIND_S + 2 * KICK_EVERY_S + 1.0, any_corner=False)
    assert len(kicked) == 3 and focus.kicks == 3
    assert all(later - earlier >= KICK_EVERY_S for earlier, later in pairwise(kicked))


def test_the_camera_just_opened_counts_as_unreadable_from_the_first_frame():
    focus, clock, kicked = keeper()
    run(focus, clock, KICK_AFTER_BLIND_S + 0.2, any_corner=False)
    assert len(kicked) == 1
