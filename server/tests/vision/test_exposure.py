"""Camera exposure through uvc-util. The tool is faked: no camera is touched in these tests."""

import pytest

from tacto.vision import exposure


class FakeTool:
    """Stands in for the uvc-util binary: remembers controls and records every call."""

    def __init__(self, controls: dict[str, int] | None = None, code: int = 0) -> None:
        self.controls: dict[str, int | str] = {
            "auto-exposure-mode": 8,
            "exposure-time-abs": 156,
            "gain": 0,
            "auto-focus": "true",
        }
        self.controls.update(controls or {})
        self.code = code
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str]) -> tuple[int, str]:
        self.calls.append(args)
        if self.code:
            return self.code, "ERROR:  no UVC-capable device"
        lines = []
        for flag, value in zip(args[::2], args[1::2], strict=True):
            if flag == "-s":
                name, new = value.split("=")
                self.controls[name] = new if name == "auto-focus" else int(new)
            elif flag == "-g":
                lines.append(f"{value} = {self.controls[value]}")
        return 0, "\n".join(lines)


@pytest.fixture(autouse=True)
def fresh_wanted(monkeypatch):
    monkeypatch.setattr(exposure, "_wanted", exposure.Exposure())


def test_read_reports_auto_and_gain():
    tool = FakeTool({"gain": 12})
    assert exposure.read(tool) == exposure.Exposure(manual=False, gain=12)
    assert tool.calls[0][:2] == ["-V", exposure.DEVICE]


def test_apply_sets_manual_mode_before_the_values_it_unlocks():
    tool = FakeTool()
    assert exposure.apply(exposure.Exposure(manual=True, gain=20), tool) is True
    assert tool.controls == {
        "auto-exposure-mode": exposure.MANUAL_MODE,
        "exposure-time-abs": exposure.EXPOSURE_TIME,
        "gain": 20,
        "auto-focus": "true",
    }
    call = tool.calls[0]
    assert call[call.index("-s") + 1] == f"auto-exposure-mode={exposure.MANUAL_MODE}"
    assert exposure.read(tool) == exposure.Exposure(manual=True, gain=20)


def test_apply_auto_hands_exposure_back_to_the_camera():
    tool = FakeTool({"auto-exposure-mode": 1, "gain": 40})
    assert exposure.apply(exposure.Exposure(manual=False), tool) is True
    assert tool.controls["auto-exposure-mode"] == exposure.AUTO_MODE
    assert tool.controls["gain"] == 0


def test_apply_with_no_setting_reuses_the_last_one_asked_for():
    tool = FakeTool()
    exposure.apply(exposure.Exposure(manual=True, gain=33), tool)
    again = FakeTool()
    assert exposure.apply(run=again) is True
    assert again.controls["gain"] == 33


def test_the_default_is_manual():
    tool = FakeTool()
    exposure.apply(run=tool)
    assert tool.controls["auto-exposure-mode"] == exposure.MANUAL_MODE
    assert tool.controls["gain"] == exposure.DEFAULT_GAIN


def test_a_camera_that_is_not_plugged_in_is_not_an_error():
    tool = FakeTool(code=19)
    assert exposure.read(tool) is None
    assert exposure.apply(run=tool) is False


def test_a_missing_tool_is_not_an_error(monkeypatch, tmp_path):
    monkeypatch.setattr(exposure, "TOOL", tmp_path / "uvc-util")
    assert exposure.available() is False
    assert exposure.read() is None
    assert exposure.apply() is False


@pytest.mark.parametrize("gain", [-1, 256])
def test_gain_outside_the_camera_range_is_refused(gain):
    with pytest.raises(ValueError):
        exposure.Exposure(manual=True, gain=gain)


def test_autofocus_is_switched_back_on_whatever_else_is_set():
    # Off parks the lens where the mat is a blur, so nothing may leave it off.
    for setting in (exposure.Exposure(manual=True, gain=10), exposure.Exposure(manual=False)):
        tool = FakeTool({"auto-focus": "false"})
        exposure.apply(setting, tool)
        assert tool.controls["auto-focus"] == "true"
