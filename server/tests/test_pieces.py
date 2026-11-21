"""Hand-worked circuits on the segment model. Bulbs are 10 ohms; full brightness is 3.6 W.

All of them use this mat (dots are col,row):

    (1,1)--w--(2,1)--BULB A--(3,1)--w--(4,1)
      |         :              :         |
     BAT+      (2,2). . . . .(3,2)     SWITCH
      |                                  |
    (1,2)                              (4,2)
      |w                                 |w
    (1,3)--w--(2,3)----w-----(3,3)--w--(4,3)
"""

import pytest

from tacto.pieces import Placed, solve_pieces, touch_for, warm_up_solver


def loop(*, switch_closed: bool = True, bottom: str = "wire") -> list[Placed]:
    return [
        Placed("battery", (1, 1), (1, 2)),
        Placed("wire", (1, 1), (2, 1)),
        Placed("bulb", (2, 1), (3, 1)),
        Placed("wire", (3, 1), (4, 1)),
        Placed("switch", (4, 1), (4, 2), closed=switch_closed),
        Placed("wire", (4, 2), (4, 3)),
        Placed("wire", (4, 3), (3, 3)),
        Placed(bottom, (3, 3), (2, 3)),  # type: ignore[arg-type]
        Placed("wire", (2, 3), (1, 3)),
        Placed("wire", (1, 3), (1, 2)),
    ]


def branch(middle: str) -> list[Placed]:
    """A second path from one end of bulb A to the other."""
    return [
        Placed("wire", (2, 1), (2, 2)),
        Placed(middle, (2, 2), (3, 2)),  # type: ignore[arg-type]
        Placed("wire", (3, 2), (3, 1)),
    ]


def by_id(pieces):
    return {piece.id: piece for piece in pieces}


def test_one_bulb():
    """6 V across 10 ohms: 0.6 A everywhere, 3.6 W, full brightness."""
    pieces, circuit = solve_pieces(loop(), 6.0)
    assert circuit.status == "working"
    assert circuit.total_current == pytest.approx(0.6, abs=0.001)
    assert circuit.shorted_path == []
    solved = by_id(pieces)
    assert solved["2,1-3,1"].brightness == pytest.approx(1.0, abs=0.01)
    assert solved["2,1-3,1"].current == pytest.approx(0.6, abs=0.001)
    assert solved["4,1-4,2"].closed is True
    assert abs(solved["4,1-4,2"].current) == pytest.approx(0.6, abs=0.001)
    # Inside the battery the current runs from the negative end to the positive end.
    assert solved["1,1-1,2"].current == pytest.approx(-0.6, abs=0.001)
    assert all(piece.brightness is None for piece in pieces if piece.type != "bulb")


def test_open_switch_breaks_the_loop():
    pieces, circuit = solve_pieces(loop(switch_closed=False), 6.0)
    assert circuit.status == "open"
    assert circuit.total_current == 0
    assert all(piece.current == 0 for piece in pieces)
    assert by_id(pieces)["4,1-4,2"].closed is False


def test_two_bulbs_in_series():
    """6 V across 20 ohms: 0.3 A; each bulb 0.9 W, a quarter of full brightness."""
    pieces, circuit = solve_pieces(loop(bottom="bulb"), 6.0)
    assert circuit.total_current == pytest.approx(0.3, abs=0.001)
    bulbs = [piece for piece in pieces if piece.type == "bulb"]
    assert [b.brightness for b in bulbs] == pytest.approx([0.25, 0.25], abs=0.01)


def test_two_bulbs_in_parallel():
    """Each bulb sees 6 V: 0.6 A and full brightness each, 1.2 A from the battery.

    The solver gives each of the nine wires on the main loop 0.001 ohm, so the exact
    figure is 6 / 5.009 = 1.198 A.
    """
    pieces, circuit = solve_pieces(loop() + branch("bulb"), 6.0)
    assert circuit.status == "working"
    assert circuit.total_current == pytest.approx(1.2, abs=0.005)
    bulbs = [piece for piece in pieces if piece.type == "bulb"]
    assert [abs(b.current) for b in bulbs] == pytest.approx([0.6, 0.6], abs=0.002)
    assert [b.brightness for b in bulbs] == pytest.approx([1.0, 1.0], abs=0.01)


def test_a_wire_across_the_only_bulb_is_a_short():
    """Nothing resists the loop: the bulb is dark, and the loop is named in order."""
    pieces, circuit = solve_pieces(loop() + branch("wire"), 6.0)
    assert circuit.status == "shorted"
    solved = by_id(pieces)
    assert solved["2,1-3,1"].shorted is False
    assert solved["2,1-3,1"].brightness == 0
    assert circuit.shorted_path == [
        "1,1-1,2",  # battery, then round from its positive end
        "1,1-2,1",
        "2,1-2,2",
        "2,2-3,2",
        "3,1-3,2",
        "3,1-4,1",
        "4,1-4,2",  # the closed switch is on the path too
        "4,2-4,3",
        "3,3-4,3",
        "2,3-3,3",
        "1,3-2,3",
        "1,2-1,3",
    ]
    assert {p.id for p in pieces if p.shorted} == set(circuit.shorted_path)


def test_a_wire_across_one_of_two_series_bulbs_is_not_a_short():
    """The bypassed bulb is dark; the other takes the full 6 V: 0.6 A, full brightness."""
    pieces, circuit = solve_pieces(loop(bottom="bulb") + branch("wire"), 6.0)
    assert circuit.status == "working"
    assert circuit.total_current == pytest.approx(0.6, abs=0.002)
    solved = by_id(pieces)
    assert solved["2,1-3,1"].brightness == pytest.approx(0.0, abs=0.01)
    assert solved["2,3-3,3"].brightness == pytest.approx(1.0, abs=0.01)


def test_touch_plays_current_as_pulse_rate():
    pieces, _ = solve_pieces(loop(), 6.0)
    touch = touch_for(pieces, x=0.3, y=0.2, piece_id="2,1-3,1")
    assert touch.pulse_hz == pytest.approx(3.0, abs=0.01)
    assert touch.buzz is False


def test_touch_on_nothing_is_silent():
    pieces, _ = solve_pieces(loop(), 6.0)
    touch = touch_for(pieces, x=0.9, y=0.9, piece_id=None)
    assert touch.present and touch.piece_id is None and touch.pulse_hz == 0


def test_touch_on_a_shorted_piece_buzzes():
    pieces, _ = solve_pieces(loop() + branch("wire"), 6.0)
    touch = touch_for(pieces, x=0.3, y=0.3, piece_id="2,2-3,2")
    assert touch.buzz is True and touch.pulse_hz == 0


# How hard the mouse vibrates follows the current through the touched piece, like the tick
# rate. Hand-worked at 6 V with 10 ohm bulbs; full strength is 1.2 A.


@pytest.mark.parametrize(
    "what, placed, piece_id, amps",
    [
        ("one bulb", loop(), "2,1-3,1", 0.6),
        ("a wire in the same loop carries the same current", loop(), "1,1-2,1", 0.6),
        ("two bulbs in series halve it", loop(bottom="bulb"), "2,1-3,1", 0.3),
        ("one branch of two in parallel", loop() + branch("bulb"), "2,1-3,1", 0.6),
        ("the battery feeds both branches", loop() + branch("bulb"), "1,1-1,2", 1.2),
    ],
)
def test_touch_strength_is_the_current_as_a_share_of_full_strength(what, placed, piece_id, amps):
    pieces, _ = solve_pieces(placed, 6.0)
    touch = touch_for(pieces, x=0.3, y=0.2, piece_id=piece_id)
    assert touch.strength == pytest.approx(amps / 1.2, abs=0.01), what
    assert touch.pulse_hz == pytest.approx(5.0 * amps, abs=0.02), what


def test_more_voltage_is_more_current_and_a_stronger_touch_up_to_full():
    weak = touch_for(solve_pieces(loop(), 3.0)[0], x=0, y=0, piece_id="2,1-3,1")
    strong = touch_for(solve_pieces(loop(), 9.0)[0], x=0, y=0, piece_id="2,1-3,1")
    assert weak.strength == pytest.approx(0.25, abs=0.01)
    assert strong.strength == pytest.approx(0.75, abs=0.01)
    # 9 V across two bulbs in parallel is 1.8 A at the battery: past full, held at 1.
    flat_out = touch_for(
        solve_pieces(loop() + branch("bulb"), 9.0)[0], x=0, y=0, piece_id="1,1-1,2"
    )
    assert flat_out.strength == 1.0


def test_no_current_is_no_strength():
    opened = solve_pieces(loop(switch_closed=False), 6.0)[0]
    assert touch_for(opened, x=0, y=0, piece_id="2,1-3,1").strength == 0.0
    assert touch_for(opened, x=0.9, y=0.9, piece_id=None).strength == 0.0


def test_a_short_buzzes_at_full_strength():
    pieces, _ = solve_pieces(loop() + branch("wire"), 6.0)
    touch = touch_for(pieces, x=0.3, y=0.3, piece_id="2,2-3,2")
    assert touch.buzz is True and touch.strength == 1.0


def test_warm_up_runs_a_real_solve(monkeypatch):
    solved = []
    real = solve_pieces
    monkeypatch.setattr(
        "tacto.pieces.solve_pieces", lambda placed, volts: solved.append(real(placed, volts)[1])
    )
    warm_up_solver()
    assert [circuit.status for circuit in solved] == ["open", "working"]
