from tacto.taps import DWELL_SECONDS, SwitchTaps

SWITCH = "4,1-4,2"


def test_a_dwell_taps_once():
    taps = SwitchTaps()
    assert taps.update(SWITCH, 0.0) is None
    assert taps.update(SWITCH, DWELL_SECONDS - 0.01) is None
    assert taps.update(SWITCH, DWELL_SECONDS) == SWITCH
    # A finger left resting on the switch does not tap again.
    assert taps.update(SWITCH, 5.0) is None
    assert taps.update(SWITCH, 60.0) is None


def test_the_finger_must_leave_before_it_can_tap_again():
    taps = SwitchTaps()
    taps.update(SWITCH, 0.0)
    assert taps.update(SWITCH, 0.6) == SWITCH
    assert taps.update(None, 1.0) is None
    assert taps.update(SWITCH, 1.1) is None
    assert taps.update(SWITCH, 1.7) == SWITCH


def test_a_hand_passing_over_does_not_tap():
    taps = SwitchTaps()
    assert taps.update(SWITCH, 0.0) is None
    assert taps.update(SWITCH, 0.3) is None
    assert taps.update(None, 0.4) is None
    assert taps.update(SWITCH, 0.5) is None  # the dwell starts again
    assert taps.update(SWITCH, 0.9) is None


def test_moving_to_another_switch_starts_a_new_dwell():
    taps = SwitchTaps()
    taps.update(SWITCH, 0.0)
    assert taps.update("1,1-2,1", 0.4) is None
    assert taps.update("1,1-2,1", 0.8) is None
    assert taps.update("1,1-2,1", 0.95) == "1,1-2,1"
