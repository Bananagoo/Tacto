"""The lab on a mat you set by hand. Run with `make manual`, open localhost:8000/manual.

Everything behind the mat is the product's own code: the solver, the touch
logic, the state message. Only the camera is replaced.
"""

from __future__ import annotations

from pathlib import Path

from tacto.contract_v2 import Grid
from tacto.lab import Lab
from tacto.lab_app import create_lab_app
from tacto.lab_lesson import LessonRunner, load_lesson
from tacto.pieces import warm_up_solver

from .manual_mat import ManualMat
from .manual_routes import manual_router

# TODO(kit owner): the real grid size is still open; this is the circuits-101 placeholder.
GRID = Grid(cols=9, rows=6)

warm_up_solver()
manual_mat = ManualMat(GRID)
LESSON_FILE = Path(__file__).resolve().parents[2] / "lessons" / "lab" / "circuits-101.yaml"

lab = Lab(GRID, manual_mat, source_name="manual", lesson=LessonRunner(load_lesson(LESSON_FILE)))
app = create_lab_app(lab, source="manual")
app.include_router(manual_router(manual_mat, lab))
