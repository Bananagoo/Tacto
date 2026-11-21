"""Record frames of the printed mat for replay mode (TACTO_SOURCE=replay).

Run from server/ so uv uses the project environment:
    uv run python ../scripts/record_frames.py --index 0 --seconds 10

Frames go to server/fixtures/<mat id>/ as numbered PNGs, five a second. Keep faces out
of the picture: these files are committed to a public repository. Replay plays them in
name order, so record the lesson in order: the kit as it ships, then the gap drawn, then
the tile swapped, and so on, holding each state for a second or two.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import cv2

FIXTURES = Path(__file__).resolve().parent.parent / "server" / "fixtures"
FRAMES_PER_SECOND = 5
WARMUP_FRAMES = 15  # let auto-exposure settle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--index", type=int, default=0, help="camera index (see /devtools/#camera)")
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--mat", default="circuits-101", help="mat id; names the output folder")
    args = parser.parse_args()

    out = FIXTURES / args.mat
    out.mkdir(parents=True, exist_ok=True)
    first = len(list(out.glob("*.png")))  # continue numbering after earlier recordings

    cap = cv2.VideoCapture(args.index, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        raise SystemExit(f"could not open camera index {args.index}")
    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        for _ in range(WARMUP_FRAMES):
            cap.read()
        count = round(args.seconds * FRAMES_PER_SECOND)
        for number in range(count):
            started = time.perf_counter()
            ok, frame = cap.read()
            if ok:
                cv2.imwrite(str(out / f"{first + number:05d}.png"), frame)
            time.sleep(max(0.0, 1 / FRAMES_PER_SECOND - (time.perf_counter() - started)))
    finally:
        cap.release()
    print(f"recorded {count} frames into {out}")


if __name__ == "__main__":
    main()
