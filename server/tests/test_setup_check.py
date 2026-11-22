"""The pre-demo setup check: a few seconds of the reader's reports in, a verdict per check out."""

from tacto.setup_check import evaluate


def sample(frames: int, **changes) -> dict:
    """One report from the camera reader, healthy unless told otherwise."""
    base = {
        "frames": frames,
        "mat_visible": True,
        "corners_seen": [0, 1, 2, 3],
        "position_confirmed": True,
        "squares_seen": 7,
        "brightness": {"state": "settled", "gain": 8, "paper": 198.0, "clipped": 0.0},
        "closest_colours": {"pair": ["wire", "switch_open"], "degrees": 21.0},
        "unsure_segments": 0,
        "pieces": 0,
        "stage_ms": {"flatten": 5.0, "hand": 25.0, "read": 11.0, "smooth": 0.1},
    }
    return base | changes


def healthy(n: int = 10, **changes) -> list[dict]:
    return [sample(100 + 6 * i, **changes) for i in range(n)]


def verdicts(samples, seconds=2.0, voice=None) -> dict[str, str]:
    return {check.id: check.status for check in evaluate(samples, seconds=seconds, voice=voice)}


def test_a_healthy_setup_passes_everything():
    result = evaluate(healthy(), seconds=2.0)
    assert all(check.status == "pass" for check in result), [
        c for c in result if c.status != "pass"
    ]
    assert {check.id for check in result} == {
        "camera",
        "mat",
        "focus",
        "brightness",
        "squares",
        "colours",
        "clean",
        "speed",
    }


def test_no_frames_fails_the_camera_and_says_what_to_do():
    stuck = [sample(500) for _ in range(10)]
    (camera,) = [c for c in evaluate(stuck, seconds=2.0) if c.id == "camera"]
    assert camera.status == "fail" and "cable" in camera.fix


def test_corners_covered_most_of_the_time_fails_the_mat():
    samples = healthy(corners_seen=[0, 3])
    assert verdicts(samples)["mat"] == "fail"


def test_a_soft_picture_warns_on_focus():
    samples = healthy(6) + healthy(4, position_confirmed=False)
    assert verdicts(samples)["focus"] == "warn"


def test_brightness_verdicts_follow_the_controller():
    for state, expected in [
        ("settled", "pass"),
        ("adjusting", "warn"),
        ("too dark", "fail"),
        ("too bright", "fail"),
        ("unavailable", "warn"),
        ("off", "warn"),
    ]:
        brightness = {"state": state, "gain": 0, "paper": 150.0, "clipped": 0.0}
        assert verdicts(healthy(brightness=brightness))["brightness"] == expected, state


def test_covered_colour_squares_fail():
    assert verdicts(healthy(squares_seen=5))["squares"] == "fail"


def test_colours_too_close_warn_then_fail():
    def at(degrees: float) -> str:
        close = {"pair": ["wire", "switch_open"], "degrees": degrees}
        return verdicts(healthy(closest_colours=close))["colours"]

    assert (at(21), at(11), at(5)) == ("pass", "warn", "fail")


def test_things_the_camera_cannot_read_warn():
    assert verdicts(healthy(unsure_segments=6))["clean"] == "warn"


def test_a_slow_reader_warns_then_fails():
    slow = {"flatten": 10.0, "hand": 60.0, "read": 30.0, "smooth": 1.0}  # about 10 a second
    crawling = {"flatten": 50.0, "hand": 100.0, "read": 60.0, "smooth": 1.0}
    assert verdicts(healthy(stage_ms=slow))["speed"] == "warn"
    assert verdicts(healthy(stage_ms=crawling))["speed"] == "fail"


def test_voice_is_checked_only_when_it_is_on():
    assert "voice" not in verdicts(healthy())
    good = {"enabled": True, "key": True, "lines": 15, "lines_cached": 15, "reachable": True}
    assert verdicts(healthy(), voice=good)["voice"] == "pass"
    assert verdicts(healthy(), voice=good | {"reachable": False})["voice"] == "fail"
    assert verdicts(healthy(), voice=good | {"lines_cached": 10})["voice"] == "warn"


def test_no_samples_at_all_fails_the_camera_not_everything_else():
    result = verdicts([], seconds=2.0)
    assert result["camera"] == "fail"
