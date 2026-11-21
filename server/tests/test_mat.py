import pytest

from tacto.contract import Grid
from tacto.mat import Mat, MatFileError, load_default_mat, load_mat


def test_the_default_mat_loads():
    mat = load_default_mat()
    assert mat.id == "circuits-101"
    assert mat.grid == Grid(cols=mat.cols, rows=mat.rows)
    assert mat.dot_pitch_mm > 0


def test_a_mat_file_with_a_typo_names_the_file(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("id: x\ncols: 9\nrows: 6\ndot_pitch: 28\n")
    with pytest.raises(MatFileError, match="bad.yaml"):
        load_mat(bad)
    with pytest.raises(MatFileError, match="cannot be read"):
        load_mat(tmp_path / "missing.yaml")


def test_a_mat_needs_at_least_two_dots_each_way():
    with pytest.raises(ValueError):
        Mat(id="x", cols=1, rows=6, dot_pitch_mm=28)
