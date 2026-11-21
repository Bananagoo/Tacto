"""Desk check: print a four-marker test sheet, then look for it with the camera.

Run from server/ so uv uses the project environment:
    uv run python ../scripts/aruco_probe.py sheet            # writes scripts/out/marker_sheet.pdf
    uv run python ../scripts/aruco_probe.py detect --index 0 # grabs frames and reports markers

The sheet is A4 with DICT_4X4_50 markers 0-3 in the corners (0 top-left, then
clockwise). It is a stand-in until kit/make_kit.py renders the real mat.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

OUT = Path(__file__).parent / "out"
DICTIONARY = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
CORNER_IDS = (0, 1, 2, 3)  # top-left, top-right, bottom-right, bottom-left

DPI = 300
A4_MM = (210, 297)
MARKER_MM = 30
MARGIN_MM = 15
WARMUP_FRAMES = 15  # let auto-exposure settle before judging a frame
FRAMES_TO_TRY = 10


def mm(value: float) -> int:
    return round(value / 25.4 * DPI)


def render_sheet() -> np.ndarray:
    width, height = mm(A4_MM[0]), mm(A4_MM[1])
    page = np.full((height, width), 255, dtype=np.uint8)
    side, margin = mm(MARKER_MM), mm(MARGIN_MM)
    positions = [
        (margin, margin),
        (width - margin - side, margin),
        (width - margin - side, height - margin - side),
        (margin, height - margin - side),
    ]
    for marker_id, (x, y) in zip(CORNER_IDS, positions, strict=True):
        page[y : y + side, x : x + side] = cv2.aruco.generateImageMarker(
            DICTIONARY, marker_id, side
        )
    cv2.putText(
        page,
        f"Tacto test sheet - print at 100% - markers are {MARKER_MM} mm",
        (margin, height // 2),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.6,
        0,
        3,
    )
    return page


def detect(image: np.ndarray) -> tuple[list[int], tuple]:
    detector = cv2.aruco.ArucoDetector(DICTIONARY, cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(image)
    return ([] if ids is None else [int(i) for i in ids.flatten()]), corners


def cmd_sheet(_: argparse.Namespace) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    page = render_sheet()
    found, _ = detect(page)
    path = OUT / "marker_sheet.pdf"
    Image.fromarray(page).save(path, "PDF", resolution=DPI)
    print(f"wrote {path}; self-check found markers {sorted(found)}")


def cmd_detect(args: argparse.Namespace) -> None:
    cap = cv2.VideoCapture(args.index, cv2.CAP_AVFOUNDATION)
    if not cap.isOpened():
        raise SystemExit(f"could not open camera index {args.index}")
    best_ids: list[int] = []
    best_frame = None
    best_corners: tuple = ()
    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        for _ in range(WARMUP_FRAMES):
            cap.read()
        for _ in range(FRAMES_TO_TRY):
            ok, frame = cap.read()
            if not ok:
                continue
            ids, corners = detect(frame)
            if best_frame is None or len(ids) > len(best_ids):
                best_ids, best_frame, best_corners = ids, frame, corners
    finally:
        cap.release()

    if best_frame is None:
        raise SystemExit("no frames from the camera")
    height, width = best_frame.shape[:2]
    print(f"frame={width}x{height} mean_brightness={best_frame.mean():.1f}")
    print(f"markers_found={len(best_ids)} ids={sorted(best_ids)}")
    missing = sorted(set(CORNER_IDS) - set(best_ids))
    print("all four corners visible" if not missing else f"missing corner ids: {missing}")
    for marker_id, quad in zip(best_ids, best_corners, strict=False):
        side_px = float(np.linalg.norm(quad[0][0] - quad[0][1]))
        print(f"  id {marker_id}: about {side_px:.0f} px per side")

    OUT.mkdir(parents=True, exist_ok=True)
    marked = best_frame.copy()
    if best_ids:
        cv2.aruco.drawDetectedMarkers(marked, best_corners, np.array(best_ids))
    path = OUT / "desk_check.png"
    cv2.imwrite(str(path), marked)
    print(f"png={path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sheet", help="write the printable test sheet").set_defaults(run=cmd_sheet)
    detect_parser = commands.add_parser("detect", help="look for the sheet with the camera")
    detect_parser.add_argument("--index", type=int, default=0)
    detect_parser.set_defaults(run=cmd_detect)
    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
