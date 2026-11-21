"""`make kit`: the command line that writes the printable PDFs."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parents[2]
MAKE_KIT = SERVER.parent / "kit" / "make_kit.py"
A4_LANDSCAPE_PT = (841.89, 595.28)


def page_size_pt(pdf: Path) -> tuple[float, float]:
    box = re.search(rb"/MediaBox\s*\[\s*([\d.\s]+)\]", pdf.read_bytes())
    assert box, f"{pdf.name} has no MediaBox"
    left, bottom, right, top = (float(value) for value in box.group(1).split())
    return right - left, top - bottom


def test_make_kit_writes_both_pdfs_at_a4(tmp_path):
    # The same call as the Makefile's `kit` target: run from server/, no --mat.
    subprocess.run(
        [sys.executable, "../kit/make_kit.py", "--out", str(tmp_path / "out")],
        cwd=SERVER,
        check=True,
        capture_output=True,
        timeout=120,
    )
    for name in ("mat.pdf", "tiles.pdf"):
        assert page_size_pt(tmp_path / "out" / name) == pytest.approx(A4_LANDSCAPE_PT, abs=0.5)


def test_make_kit_names_a_mat_file_it_cannot_read(tmp_path):
    result = subprocess.run(
        [sys.executable, str(MAKE_KIT), "--mat", str(tmp_path / "missing.yaml")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode != 0
    assert "missing.yaml" in result.stderr
    assert "Traceback" not in result.stderr
