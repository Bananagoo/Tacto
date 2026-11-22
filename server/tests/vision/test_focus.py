"""Kicking the autofocus when the mat cannot be read. No camera is touched."""

from itertools import pairwise

from tacto.vision.focus import KICK_AFTER_BLIND_S, KICK_EVERY_S, OFF_FOR_S, FocusKeeper


class Clock:
    def __init__(self) -> None:
        self.now = 50.0

    def __call__(self) -> float:
        return self.now


def keeper():
    """A keeper, its clock, and everything it sent: (time, autofocus on or off)."""
    clock, sent = Clock(), []
    return FocusKeeper(lambda on: sent.append((clock.now, on)) or True, clock=clock), clock, sent


def run(focus, clock, seconds: float, any_corner: bool) -> None:
    for _ in range(round(seconds * 30)):
        clock.now += 1 / 30
        focus.saw(any_corner)


def test_a_readable_mat_is_left_alone():
    focus, clock, sent = keeper()
    run(focus, clock, 30, any_corner=True)
    assert sent == []


def test_a_hand_passing_over_the_markers_does_not_set_off_a_sweep():
    focus, clock, sent = keeper()
    for _ in range(5):
        run(focus, clock, KICK_AFTER_BLIND_S * 0.8, any_corner=False)
        run(focus, clock, 0.2, any_corner=True)
    assert sent == []


def test_a_kick_is_off_then_on_a_moment_later():
    focus, clock, sent = keeper()
    start = clock.now
    run(focus, clock, KICK_AFTER_BLIND_S + OFF_FOR_S + 0.5, any_corner=False)
    assert [on for _, on in sent] == [False, True]
    (off_at, _), (on_at, _) = sent
    assert off_at - start >= KICK_AFTER_BLIND_S
    assert on_at - off_at >= OFF_FOR_S


def test_autofocus_comes_back_on_even_if_the_mat_shows_up_mid_kick():
    focus, clock, sent = keeper()
    run(focus, clock, KICK_AFTER_BLIND_S + 0.2, any_corner=False)
    assert [on for _, on in sent] == [False]
    run(focus, clock, OFF_FOR_S + 0.2, any_corner=True)
    assert [on for _, on in sent] == [False, True]


def test_closing_mid_kick_switches_autofocus_back_on():
    focus, clock, sent = keeper()
    run(focus, clock, KICK_AFTER_BLIND_S + 0.2, any_corner=False)
    focus.close()
    assert [on for _, on in sent] == [False, True]
    focus.close()
    assert len(sent) == 2


def test_after_a_kick_the_sweep_gets_time_to_finish():
    focus, clock, sent = keeper()
    run(focus, clock, KICK_AFTER_BLIND_S + KICK_EVERY_S - 0.5, any_corner=False)
    assert [on for _, on in sent] == [False, True] and focus.kicks == 1


def test_it_kicks_again_if_the_first_sweep_did_not_bring_the_mat_back():
    focus, clock, sent = keeper()
    run(focus, clock, KICK_AFTER_BLIND_S + 2 * KICK_EVERY_S + OFF_FOR_S + 0.5, any_corner=False)
    assert [on for _, on in sent] == [False, True] * 3 and focus.kicks == 3
    offs = [at for at, on in sent if not on]
    assert all(later - earlier >= KICK_EVERY_S for earlier, later in pairwise(offs))
