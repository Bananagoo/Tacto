"""Recorded frames from a folder: the replay seam."""

import cv2
import numpy as np

from tacto.vision.frames import FolderFrames


def test_folder_frames_loops_through_image_files_in_name_order(tmp_path):
    for name, shade in [("b.png", 20), ("a.png", 10), ("c.jpg", 30)]:
        cv2.imwrite(str(tmp_path / name), np.full((40, 40, 3), shade, np.uint8))
    (tmp_path / "notes.txt").write_text("not a frame")
    (tmp_path / "broken.png").write_bytes(b"not a png")
    frames = FolderFrames(tmp_path)
    shades = [round(float(frames.latest_frame().mean()), -1) for _ in range(7)]
    assert shades == [10, 20, 30, 10, 20, 30, 10]


def test_folder_frames_gives_nothing_for_an_empty_or_missing_folder(tmp_path):
    assert FolderFrames(tmp_path).latest_frame() is None
    assert FolderFrames(tmp_path / "missing").latest_frame() is None
    (tmp_path / "broken.png").write_bytes(b"not a png")
    assert FolderFrames(tmp_path).latest_frame() is None
