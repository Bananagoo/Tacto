"""Write the printable mat (dot grid and corner markers) as a PDF.

Run from the repo root with `make kit`, or from server/ so uv uses the project environment:
    uv run python ../kit/make_kit.py --mat ../kit/mats/circuits-101.yaml --out ../kit/out
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from tacto.mat import MatFileError, load_mat
from tacto.vision.classify import load_colours
from tacto.vision.kit_render import render_mat

KIT_DIR = Path(__file__).resolve().parent
DEFAULT_MAT = KIT_DIR / "mats" / "circuits-101.yaml"
DEFAULT_OUT = KIT_DIR / "out"
PRINT_DPI = 300


def save_pdf(page: np.ndarray, path: Path) -> None:
    """One page whose size on paper comes from its pixel size and PRINT_DPI."""
    Image.fromarray(cv2.cvtColor(page, cv2.COLOR_BGR2RGB)).save(path, "PDF", resolution=PRINT_DPI)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mat", type=Path, default=DEFAULT_MAT, help="the mat file")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="folder for the PDF")
    args = parser.parse_args()

    try:
        mat = load_mat(args.mat)
    except MatFileError as error:
        raise SystemExit(f"make_kit: {error}") from error
    args.out.mkdir(parents=True, exist_ok=True)
    save_pdf(
        render_mat(mat, dpi=PRINT_DPI, colours=load_colours().colours), args.out / "mat.pdf"
    )
    print(f"make_kit: wrote {args.out / 'mat.pdf'}")
    print("make_kit: print at 100% (no 'fit to page') and check the 50 mm bar with a ruler")


if __name__ == "__main__":
    main()
