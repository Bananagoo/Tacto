"""The pre-demo setup check: is this camera, this mat and this room ready?

The page at /devtools/#setup asks GET /setup/check. For a few seconds the server watches
the camera reader's own reports while automatic brightness settles, then gives a verdict
for each part, with what to do about any that fail. `evaluate` is the judgement, kept
apart from the waiting so it can be tested on made-up reports.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from typing import Literal

Status = Literal["pass", "warn", "fail"]

# TODO(Katie): tune at the venue.
SECONDS = 3.0
# Brightness is given this long to settle before the watching starts.
SETTLE_S = 5.0
SAMPLE_EVERY_S = 0.2
CAMERA_MIN_FPS = 10.0
SPEED_GOOD_FPS = 15.0
SPEED_MIN_FPS = 8.0
CORNERS_GOOD_SHARE = 0.6
CONFIRMED_GOOD_SHARE = 0.8
COLOURS_GOOD_DEGREES = 15.0
COLOURS_MIN_DEGREES = 8.0
MAX_UNSURE = 2


@dataclass(frozen=True)
class Check:
    id: str
    label: str
    status: Status
    detail: str
    fix: str = ""


def _share(samples: list[dict], test: Callable[[dict], bool]) -> float:
    return sum(test(s) for s in samples) / len(samples) if samples else 0.0


def evaluate(samples: list[dict], *, seconds: float, voice: dict | None = None) -> list[Check]:
    """A verdict per check from the camera reader's reports, oldest first."""
    checks: list[Check] = []
    frames = (samples[-1]["frames"] - samples[0]["frames"]) if len(samples) > 1 else 0
    fps = frames / seconds if seconds > 0 else 0.0
    camera_ok = fps >= CAMERA_MIN_FPS
    checks.append(
        Check(
            "camera",
            "Camera",
            "pass" if camera_ok else "fail",
            f"{fps:.0f} frames a second",
            "" if camera_ok else "Check the camera's cable, then restart the lab.",
        )
    )
    if not samples:
        return checks
    last = samples[-1]

    corners = _share(samples, lambda s: len(s["corners_seen"]) == 4)
    checks.append(
        Check(
            "mat",
            "Mat found",
            "pass" if corners >= CORNERS_GOOD_SHARE else "fail",
            f"all four corners in {corners:.0%} of frames",
            ""
            if corners >= CORNERS_GOOD_SHARE
            else "Clear hands off the mat and make sure all four corner squares are in view.",
        )
    )

    confirmed = _share(samples, lambda s: s["position_confirmed"])
    checks.append(
        Check(
            "focus",
            "Sharp picture",
            "pass" if confirmed >= CONFIRMED_GOOD_SHARE else "warn",
            f"readable in {confirmed:.0%} of frames",
            ""
            if confirmed >= CONFIRMED_GOOD_SHARE
            else "Keep hands and the laptop out of the way and wait two seconds for the focus.",
        )
    )

    bright = last["brightness"]
    state = bright.get("state", "off")
    status, fix = {
        "settled": ("pass", ""),
        "adjusting": ("warn", "Still adjusting: run the check again in a moment."),
        "too dark": ("fail", "Too dark even at full gain: add light over the mat."),
        "too bright": ("fail", "Too bright even at the lowest gain: move out of the glare."),
        "unavailable": ("warn", "The camera's gain cannot be set: run `make camera-tool`."),
        "waiting": ("warn", "No paper measured yet: make sure the mat is found."),
        "off": ("warn", "Automatic brightness is off (AUTO_BRIGHTNESS=0)."),
    }.get(state, ("warn", ""))
    paper = bright.get("paper")
    detail = f"{state}; paper at {paper:.0f} of 255, gain {bright.get('gain')}" if paper else state
    checks.append(Check("brightness", "Brightness", status, detail, fix))  # type: ignore[arg-type]

    squares = last["squares_seen"]
    checks.append(
        Check(
            "squares",
            "Colour squares",
            "pass" if squares == 7 else "fail",
            f"{squares} of 7 read",
            "" if squares == 7 else "Uncover the colour squares along the top of the mat.",
        )
    )

    closest = last["closest_colours"]
    gap = closest["degrees"]
    first, second = (name.replace("_", " ") for name in closest["pair"])
    colour_status: Status = (
        "pass" if gap >= COLOURS_GOOD_DEGREES else "warn" if gap >= COLOURS_MIN_DEGREES else "fail"
    )
    checks.append(
        Check(
            "colours",
            "Colours tell apart",
            colour_status,
            f"closest pair {first} and {second}, {gap:.0f}° apart",
            ""
            if colour_status == "pass"
            else "The light is pulling two piece colours together: try whiter light, "
            "or keep those two pieces apart.",
        )
    )

    unsure = max(s["unsure_segments"] for s in samples[-5:])
    checks.append(
        Check(
            "clean",
            "Mat reads cleanly",
            "pass" if unsure <= MAX_UNSURE else "warn",
            f"{last['pieces']} pieces read, {unsure} spots the camera is unsure of",
            ""
            if unsure <= MAX_UNSURE
            else "Something on the mat cannot be read: a hand, a shadow, or a piece half on.",
        )
    )

    frame_ms = sum(last["stage_ms"].values())
    reader_fps = 1000 / frame_ms if frame_ms > 0 else 0.0
    speed_status: Status = (
        "pass"
        if reader_fps >= SPEED_GOOD_FPS
        else "warn"
        if reader_fps >= SPEED_MIN_FPS
        else "fail"
    )
    checks.append(
        Check(
            "speed",
            "Fast enough",
            speed_status,
            f"{frame_ms:.0f} ms a frame, about {reader_fps:.0f} a second",
            "" if speed_status == "pass" else "Close other apps and plug the laptop in.",
        )
    )

    if voice is not None and voice.get("enabled"):
        problems = []
        if not voice.get("key"):
            problems.append(("fail", "No TOGETHER_API_KEY in .env."))
        elif not voice.get("reachable"):
            problems.append(("fail", "Together cannot be reached: check the Wi-Fi."))
        if voice.get("lines_cached", 0) < voice.get("lines", 0):
            problems.append(("warn", "Some lines have no recording: restart the lab online."))
        worst: Status = "pass"
        for level, _ in problems:
            if level == "fail" or (level == "warn" and worst == "pass"):
                worst = level  # type: ignore[assignment]
        checks.append(
            Check(
                "voice",
                "Voice",
                worst,
                f"{voice.get('lines_cached', 0)} of {voice.get('lines', 0)} lines recorded, "
                f"Together {'reachable' if voice.get('reachable') else 'not reachable'}",
                " ".join(text for _, text in problems),
            )
        )
    return checks


async def run(report: Callable[[], dict], voice: Callable[[], dict] | None = None) -> dict:
    """Let brightness settle, watch for SECONDS, and judge. Takes about 3 to 8 seconds."""
    started = time.monotonic()
    while time.monotonic() - started < SETTLE_S:
        if report().get("brightness", {}).get("state") not in ("waiting", "adjusting"):
            break
        await asyncio.sleep(SAMPLE_EVERY_S)
    samples: list[dict] = []
    watch_started = time.monotonic()
    while time.monotonic() - watch_started < SECONDS:
        samples.append(report())
        await asyncio.sleep(SAMPLE_EVERY_S)
    watched = time.monotonic() - watch_started
    voice_state = await asyncio.to_thread(voice) if voice is not None else None
    checks = evaluate(samples, seconds=watched, voice=voice_state)
    return {
        "ok": all(check.status != "fail" for check in checks),
        "seconds": round(time.monotonic() - started, 1),
        "checks": [asdict(check) for check in checks],
    }
