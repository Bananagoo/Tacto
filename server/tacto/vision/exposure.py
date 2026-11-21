"""Manual exposure for the LogiInsight camera, and autofocus kept on.

Left on auto, the camera exposes for the whole scene: on a dark desk or floor the white
mat burns out, the dots vanish and the corner markers stop being read. In manual mode
the camera no longer looks at the background at all.

Focus cannot be locked. The camera has no focus distance to set, only autofocus on or
off, and off does not hold the lens: it parks it where the mat is a blur (measured twice
on 21 Nov 2026: sharpness 80 to 95 with autofocus on, 7 within a second of turning it
off). Nothing here touches autofocus when the camera is opened: "autofocus on" sent
before frames are flowing left the lens parked the same way. `refocus` sends it while
frames are flowing, which starts a sweep, and `vision/focus.py` decides when.

OpenCV cannot set either on macOS (every `capture.set` is refused), so the settings go
through the uvc-util command-line tool, built by `make camera-tool`. Without the tool,
or without the camera, everything here does nothing and says so once.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field

# TODO(Katie): measured once, on 21 Nov 2026, with the camera facing the mat at an angle
# under hall lighting: gain 0 put the paper at about 187 of 255 with nothing clipped, and
# gain 60 clipped 17% of the frame. Recheck once the camera is mounted above the mat.
DEFAULT_GAIN = 0
# Exposure time only darkens the picture below about 60; from 60 to 400 it changes nothing.
EXPOSURE_TIME = 156

TOOL = Path(__file__).resolve().parents[2] / "vendor" / "uvc-util" / "uvc-util"
# USB vendor:product of the LogiInsight camera ("LVNext").
DEVICE = "0x046d:0x094f"
MANUAL_MODE = 1
AUTO_MODE = 8
TIMEOUT_S = 3

Runner = Callable[[list[str]], tuple[int, str]]


class Exposure(BaseModel):
    manual: bool = True
    gain: int = Field(DEFAULT_GAIN, ge=0, le=255)


# What the camera should be set to whenever it is opened. The bench changes it.
_wanted = Exposure()
_told: set[str] = set()


def _tell_once(message: str) -> None:
    if message not in _told:
        _told.add(message)
        print(f"vision.exposure: {message}")


def available() -> bool:
    return TOOL.is_file()


def _run_tool(args: list[str]) -> tuple[int, str]:
    if not available():
        _tell_once(f"{TOOL} is missing, so the camera stays on auto. Run: make camera-tool")
        return 127, ""
    try:
        done = subprocess.run(
            [str(TOOL), *args], capture_output=True, text=True, timeout=TIMEOUT_S, check=False
        )
    except (OSError, subprocess.SubprocessError) as error:
        _tell_once(f"could not run uvc-util: {error}")
        return 1, ""
    return done.returncode, done.stdout + done.stderr


def read(run: Runner | None = None) -> Exposure | None:
    """What the camera is set to now. None when the tool or the camera is missing."""
    code, output = (run or _run_tool)(["-V", DEVICE, "-g", "auto-exposure-mode", "-g", "gain"])
    if code != 0:
        return None
    values: dict[str, str] = {}
    for line in output.splitlines():
        name, _, value = line.partition("=")
        values[name.strip()] = value.strip()
    try:
        return Exposure(
            manual=int(values["auto-exposure-mode"]) == MANUAL_MODE,
            gain=int(values["gain"]),
        )
    except (KeyError, ValueError):
        return None


def apply(setting: Exposure | None = None, run: Runner | None = None) -> bool:
    """Set the camera, and remember the setting for the next time it is opened.

    With no setting, the last one asked for is applied again. False when nothing was set.
    """
    global _wanted
    if setting is not None:
        _wanted = setting
    if _wanted.manual:
        # Mode first: the camera refuses an exposure time while it is still on auto.
        controls: dict[str, int | str] = {
            "auto-exposure-mode": MANUAL_MODE,
            "exposure-time-abs": EXPOSURE_TIME,
            "gain": _wanted.gain,
        }
    else:
        controls = {"gain": 0, "auto-exposure-mode": AUTO_MODE}
    args = ["-V", DEVICE]
    for name, value in controls.items():
        args += ["-s", f"{name}={value}"]
    code, output = (run or _run_tool)(args)
    if code != 0 and output:
        _tell_once(f"camera exposure not set: {output.strip()}")
    return code == 0


def refocus(run: Runner | None = None) -> bool:
    """Start an autofocus sweep. Only works while the camera is sending frames."""
    code, _ = (run or _run_tool)(["-V", DEVICE, "-s", "auto-focus=true"])
    return code == 0


def wanted() -> Exposure:
    return _wanted
