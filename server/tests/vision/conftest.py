"""Shared fixtures for the vision tests: the Circuits 101 layout and its print geometry."""

import pytest

from tacto.mat.loader import load_mat
from tacto.mat.models import MatLayout
from tacto.platform import MATS_DIR
from tacto.vision.print_geometry import PrintGeometry


@pytest.fixture(scope="session")
def layout() -> MatLayout:
    return load_mat(MATS_DIR / "circuits-101.yaml")


@pytest.fixture(scope="session")
def geometry(layout: MatLayout) -> PrintGeometry:
    return PrintGeometry.for_layout(layout)
