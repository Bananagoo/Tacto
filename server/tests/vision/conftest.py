"""Shared fixtures for the vision tests: the Circuits 101 mat and its print geometry."""

import pytest

from tacto.mat import Mat, load_default_mat
from tacto.vision.print_geometry import PrintGeometry


@pytest.fixture(scope="session")
def mat() -> Mat:
    return load_default_mat()


@pytest.fixture(scope="session")
def geometry(mat: Mat) -> PrintGeometry:
    return PrintGeometry.for_mat(mat)
