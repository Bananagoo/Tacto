"""Manual exposure and a focus lock for the LogiInsight camera.

Left on auto, the camera exposes for the whole scene: on a dark desk or floor the white
mat burns out, the dots vanish and the corner markers stop being read. In manual mode
the camera no longer looks at the background at all.

Autofocus has the same kind of trouble: a hand reaching over the desk is nearer than the
paper, the lens follows it and the whole mat goes soft. The camera has no focus distance
to set, only autofocus on or off, so the lock is: wait until the mat is sharp, then turn
autofocus off.

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
    # False holds the lens where it is. On by default: locking is only right once the
    # mat is in focus, which a person has to see (the bench shows a sharpness number).
    autofocus: bool = True


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
    code, output = (run or _run_tool)(
        ["-V", DEVICE, "-g", "auto-exposure-mode", "-g", "gain", "-g", "auto-focus"]
    )
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
            autofocus=values["auto-focus"] != "false",
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
    controls["auto-focus"] = "true" if _wanted.autofocus else "false"
    args = ["-V", DEVICE]
    for name, value in controls.items():
        args += ["-s", f"{name}={value}"]
    code, output = (run or _run_tool)(args)
    if code != 0 and output:
        _tell_once(f"camera exposure not set: {output.strip()}")
    return code == 0


def wanted() -> Exposure:
    return _wanted
