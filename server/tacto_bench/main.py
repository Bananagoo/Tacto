"""The tooling server: the lab on a mat you set by hand, plus the camera bench.

Run with `make manual` and open localhost:8000/manual.

Everything behind the mat is the product's own code: the solver, the touch
logic, the state message. Only the camera is replaced.
"""

from __future__ import annotations

from pathlib import Path

from tacto.app import create_lab_app
from tacto.lab import Lab
from tacto.lesson import LessonRunner, load_lesson
from tacto.mat import load_default_mat
from tacto.pieces import warm_up_solver

from .camera_routes import router as camera_router
from .manual_mat import ManualMat
from .manual_routes import manual_router

GRID = load_default_mat().grid

warm_up_solver()
manual_mat = ManualMat(GRID)
LESSON_FILE = Path(__file__).resolve().parents[2] / "lessons" / "circuits-101.yaml"

lab = Lab(GRID, manual_mat, source_name="manual", lesson=LessonRunner(load_lesson(LESSON_FILE)))
app = create_lab_app(lab, source="manual")
app.include_router(manual_router(manual_mat, lab))
app.include_router(camera_router)
