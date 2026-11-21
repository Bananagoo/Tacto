"""Track the index fingertip with MediaPipe Hand Landmarker on our own camera frames.

Run from server/ so uv uses the project environment with the mediapipe extra:
    uv run --extra mediapipe python ../scripts/mediapipe_probe.py --index 0 --seconds 10

Needs the model file (about 8 MB, not committed):
    curl -L -o server/vendor/hand_landmarker.task \
      https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task

Prints capture fps, inference time per frame and the fingertip in pixels, and
saves the last frame that had a hand, with the fingertip marked.
"""

from __future__ import annotations

import argparse
import statistics
import time
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

ROOT = Path(__file__).resolve().parent.parent
MODEL = ROOT / "server" / "vendor" / "hand_landmarker.task"
INDEX_TIP = 8  # MediaPipe hand landmark number for the index fingertip
PRINT_EVERY_S = 1.0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--index", type=int, default=0)
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "out")
    args = parser.parse_args()

    if not MODEL.exists():
        raise SystemExit(f"model not found at {MODEL}; see the curl command in this file")

    options = vision.HandLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=str(MODEL)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
    )
    cap = cv2.VideoCapture(args.index, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        raise SystemExit(f"could not open camera index {args.index}")

    frames = 0
    with_hand = 0
    infer_ms: list[float] = []
    marked = None
    last_print = 0.0
    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        with vision.HandLandmarker.create_from_options(options) as landmarker:
            start = time.perf_counter()
            while (now := time.perf_counter()) - start < args.seconds:
                ok, frame = cap.read()
                if not ok:
                    continue
                frames += 1
                height, width = frame.shape[:2]
                image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB),
                )
                before = time.perf_counter()
                result = landmarker.detect_for_video(image, int((now - start) * 1000))
                infer_ms.append((time.perf_counter() - before) * 1000)

                tips = []
                for landmarks, handedness in zip(
                    result.hand_landmarks, result.handedness, strict=False
                ):
                    tip = landmarks[INDEX_TIP]
                    tips.append((handedness[0].category_name, tip.x * width, tip.y * height))
                if tips:
                    with_hand += 1
                    marked = frame.copy()
                    for _, x, y in tips:
                        cv2.circle(marked, (int(x), int(y)), 18, (0, 0, 255), 4)
                if now - last_print >= PRINT_EVERY_S:
                    last_print = now
                    text = ", ".join(
                        f"{name} index_tip=({x:.0f}, {y:.0f}) px" for name, x, y in tips
                    )
                    print(f"t={now - start:5.1f}s  {text or 'no hand'}")
            elapsed = time.perf_counter() - start
    finally:
        cap.release()

    print(f"frames={frames} in {elapsed:.1f}s -> {frames / elapsed:.1f} fps with tracking on")
    print(f"frames_with_hand={with_hand}")
    if infer_ms:
        print(
            f"inference_ms median={statistics.median(infer_ms):.1f} "
            f"p95={sorted(infer_ms)[int(len(infer_ms) * 0.95)]:.1f} max={max(infer_ms):.1f}"
        )
    if marked is not None:
        args.out.mkdir(parents=True, exist_ok=True)
        path = args.out / "mediapipe_hand.png"
        cv2.imwrite(str(path), marked)
        print(f"png={path}")


if __name__ == "__main__":
    main()
