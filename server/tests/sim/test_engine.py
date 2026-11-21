"""Engine: the one place that talks to ngspice."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from tacto.sim import engine
from tacto.sim.engine import GROUND, NgspiceNotFoundError, Resistor, solve_node_voltages


def test_one_resistor_across_the_source():
    """3 V across 10 ohms: the only node sits at 3 V (and so carries 3 / 10 = 0.3 A)."""
    volts = solve_node_voltages(3.0, "n0", [Resistor("n0", GROUND, 10.0)])
    assert volts["n0"] == pytest.approx(3.0)
    assert volts[GROUND] == 0.0


def test_voltage_divider():
    """6 V across 10 + 10 ohms in series: the midpoint is at 6 * 10 / 20 = 3 V."""
    resistors = [Resistor("top", "mid", 10.0), Resistor("mid", GROUND, 10.0)]
    volts = solve_node_voltages(6.0, "top", resistors)
    assert volts["mid"] == pytest.approx(3.0)


def test_netlist_order_does_not_change_the_answer():
    """The same divider listed backwards gives bit-identical voltages."""
    resistors = [Resistor("top", "mid", 10.0), Resistor("mid", GROUND, 30.0)]
    forwards = solve_node_voltages(6.0, "top", resistors)
    backwards = solve_node_voltages(6.0, "top", resistors[::-1])
    assert forwards == backwards


def test_solves_from_several_threads_do_not_interfere():
    """ngspice is one shared instance. Each thread solves V across a 10 + 30 ohm divider
    and must get back its own midpoint, V * 30 / 40, not another thread's."""
    resistors = [Resistor("top", "mid", 10.0), Resistor("mid", GROUND, 30.0)]
    source_volts = [float(v) for v in range(1, 41)]
    with ThreadPoolExecutor(max_workers=8) as pool:
        midpoints = list(
            pool.map(lambda v: solve_node_voltages(v, "top", resistors)["mid"], source_volts)
        )
    assert midpoints == pytest.approx([v * 0.75 for v in source_volts])


def test_library_from_environment_is_used(tmp_path: Path):
    library = tmp_path / "libngspice.dylib"
    library.touch()
    found = engine.find_ngspice_library({"NGSPICE_LIBRARY_PATH": str(library)})
    assert found == str(library)


def test_library_is_found_in_the_search_list(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    library = tmp_path / "libngspice.dylib"
    library.touch()
    monkeypatch.setattr(engine, "LIBRARY_SEARCH_PATHS", (str(tmp_path / "missing"), str(library)))
    assert engine.find_ngspice_library({}) == str(library)


def test_missing_library_says_how_to_install_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(engine, "LIBRARY_SEARCH_PATHS", (str(tmp_path / "nowhere.dylib"),))
    with pytest.raises(NgspiceNotFoundError, match="brew install libngspice"):
        engine.find_ngspice_library({})


def test_environment_path_that_points_nowhere_is_an_error(tmp_path: Path):
    """A wrong NGSPICE_LIBRARY_PATH must fail loudly, not fall back to another copy."""
    missing = str(tmp_path / "nowhere.dylib")
    with pytest.raises(NgspiceNotFoundError, match="NGSPICE_LIBRARY_PATH"):
        engine.find_ngspice_library({"NGSPICE_LIBRARY_PATH": missing})
