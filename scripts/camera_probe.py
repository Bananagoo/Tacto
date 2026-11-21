"""Probe the cameras OpenCV can open: resolution, pixel format, measured fps, one PNG each.

Run from server/ so uv uses the project environment:
    uv run python ../scripts/camera_probe.py                     # every index, 3 s each
    uv run python ../scripts/camera_probe.py --index 0 --seconds 20 --fourcc NV12

The camera is released as soon as the measurement ends; the docs warn it can overheat.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

MAX_INDEX = 6
WARMUP_FRAMES = 5


def fourcc_text(value: float) -> str:
    code = int(value)
    if code <= 0:
        # AVFoundation picks the format itself and OpenCV cannot read it back.
        return "not reported"
    text = "".join(chr((code >> (8 * i)) & 0xFF) for i in range(4))
    return text if text.isascii() and text.isprintable() else f"raw:{code}"


def probe(index: int, seconds: float, width: int, height: int, fourcc: str | None, out: Path):
    cap = cv2.VideoCapture(index, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        return None
    try:
        # Size before format: the LogiInsight docs say the order matters.
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if fourcc:
            cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))

        for _ in range(WARMUP_FRAMES):
            cap.read()

        frames = 0
        failed = 0
        last = None
        start = time.perf_counter()
        while time.perf_counter() - start < seconds:
            ok, frame = cap.read()
            if ok and frame is not None:
                frames += 1
                last = frame
            else:
                failed += 1
                if failed > 50:
                    break
        elapsed = time.perf_counter() - start

        result = {
            "index": index,
            "reported": f"{int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
            f"{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}",
            "reported_fps": round(cap.get(cv2.CAP_PROP_FPS), 1),
            "fourcc": fourcc_text(cap.get(cv2.CAP_PROP_FOURCC)),
            "frames": frames,
            "failed_reads": failed,
            "measured_fps": round(frames / elapsed, 1) if elapsed > 0 else 0.0,
        }
        if last is not None:
            result["frame_shape"] = "x".join(str(n) for n in last.shape)
            result["mean_brightness"] = round(float(last.mean()), 1)
            out.mkdir(parents=True, exist_ok=True)
            path = out / f"camera_{index}.png"
            cv2.imwrite(str(path), last)
            result["png"] = str(path)
        return result
    finally:
        cap.release()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--index", type=int, help="probe only this camera index")
    parser.add_argument("--seconds", type=float, default=3.0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--fourcc", help="ask for a pixel format, e.g. MJPG, YUY2, NV12")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "out")
    args = parser.parse_args()

    indices = [args.index] if args.index is not None else range(MAX_INDEX)
    for index in indices:
        result = probe(index, args.seconds, args.width, args.height, args.fourcc, args.out)
        if result is None:
            print(f"index {index}: could not open")
            continue
        print(" | ".join(f"{key}={value}" for key, value in result.items()))


if __name__ == "__main__":
    main()
