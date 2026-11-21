"""During a build, time with nothing changing on the mat brings hints and moves the zone."""

from tacto.contract import Circuit, Part
from tacto.learner.models import ConceptProgress, Progress
from tacto.lessons.engine import IDLE_SECONDS, LessonEngine

FIRST_HINT = "Is there a gap anywhere?"
LAST_HINT = "Follow the wire from the battery with your finger."


def moved(circuit: Circuit) -> Circuit:
    """The same circuit with its first part slid one dot to the right."""
    part = circuit.parts[0]
    slid = part.model_copy(
        update={"a": (part.a[0] + 1, part.a[1]), "b": (part.b[0] + 1, part.b[1])}
    )
    return circuit.model_copy(update={"parts": [slid, *circuit.parts[1:]]})


def test_the_idle_period_is_thirty_seconds():
    assert IDLE_SECONDS == 30.0


def test_hints_appear_one_at_a_time_and_stop_at_the_last(lesson, at, open_loop):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))

    engine.on_tick(now=at(29.999999))
    assert engine.tutor().hint == ""

    engine.on_tick(now=at(30))
    assert engine.tutor().hint == FIRST_HINT

    engine.on_tick(now=at(59.999999))
    assert engine.tutor().hint == FIRST_HINT

    engine.on_tick(now=at(60))
    assert engine.tutor().hint == LAST_HINT

    engine.on_tick(now=at(90))
    engine.on_tick(now=at(120))
    assert engine.tutor().hint == LAST_HINT  # the ladder has no step below the last


def test_each_idle_period_lowers_the_score_and_three_mean_stuck(lesson, at, open_loop):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))

    engine.on_tick(now=at(30))
    engine.on_tick(now=at(60))
    assert (engine.tutor().score, engine.tutor().zone) == (-2, "productive")

    engine.on_tick(now=at(90))  # no hint left to give, but the learner is still idle
    assert (engine.tutor().score, engine.tutor().zone) == (-3, "stuck")


def test_ticking_often_counts_each_idle_period_once(lesson, at, open_loop):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))

    for frame in range(15 * 45):  # 45 s at fifteen ticks a second
        engine.on_tick(now=at(frame / 15))

    assert engine.tutor().hint == FIRST_HINT
    assert engine.tutor().score == -1


def test_one_late_tick_counts_every_idle_period_that_passed(lesson, at, open_loop):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))

    engine.on_tick(now=at(65))

    assert engine.tutor().hint == LAST_HINT
    assert engine.tutor().score == -2


def test_a_circuit_change_restarts_the_idle_timer(lesson, at, open_loop):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))

    engine.on_circuit(moved(open_loop), now=at(20))
    engine.on_tick(now=at(49.999999))
    assert engine.tutor().hint == ""
    assert engine.tutor().score == 0

    engine.on_tick(now=at(50))
    assert engine.tutor().hint == FIRST_HINT


def test_a_circuit_change_keeps_the_hints_already_shown(lesson, at, open_loop):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))
    engine.on_tick(now=at(30))

    engine.on_circuit(moved(open_loop), now=at(40))
    assert engine.tutor().hint == FIRST_HINT

    engine.on_tick(now=at(70))
    assert engine.tutor().hint == LAST_HINT


def test_a_change_in_current_alone_is_not_a_circuit_change(lesson, at, open_loop):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))

    # The wheel was turned: volts and amps differ, but nothing moved on the mat.
    wheel_turned = open_loop.model_copy(
        update={
            "source_voltage": 4.5,
            "total_current": 0.2,
            "parts": [
                p.model_copy(update={"current": 0.2, "voltage": 1.0}) for p in open_loop.parts
            ],
            "wires": [w.model_copy(update={"current": 0.2}) for w in open_loop.wires],
        }
    )
    engine.on_circuit(wheel_turned, now=at(20))
    engine.on_tick(now=at(30))

    assert engine.tutor().hint == FIRST_HINT


def test_a_new_wire_is_a_circuit_change(lesson, at, open_loop):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))

    wire = open_loop.wires[0].model_copy(update={"a": (5, 5), "b": (6, 5)})
    engine.on_circuit(open_loop.model_copy(update={"wires": [*open_loop.wires, wire]}), now=at(20))
    engine.on_tick(now=at(30))

    assert engine.tutor().hint == ""


def test_flipping_a_switch_is_a_circuit_change(lesson, at, open_loop):
    def with_switch(closed: bool) -> Circuit:
        switch = Part(id="switch", kind="switch", a=(5, 0), b=(6, 0), closed=closed)
        return open_loop.model_copy(update={"parts": [*open_loop.parts, switch]})

    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(with_switch(closed=False), now=at(0))

    # Still not a lit bulb, but the learner's hand did something.
    engine.on_circuit(with_switch(closed=True), now=at(20))
    engine.on_tick(now=at(30))

    assert engine.tutor().hint == ""


def test_the_same_parts_listed_in_another_order_are_not_a_change(lesson, at, open_loop):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))

    reordered = open_loop.model_copy(update={"parts": list(reversed(open_loop.parts))})
    engine.on_circuit(reordered, now=at(20))
    engine.on_tick(now=at(30))

    assert engine.tutor().hint == FIRST_HINT


def test_hints_clear_when_the_circuit_satisfies_the_step(lesson, at, open_loop, one_bulb):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))
    engine.on_tick(now=at(30))
    assert engine.tutor().hint == FIRST_HINT

    engine.on_circuit(one_bulb, now=at(31))

    assert engine.tutor().phase == "test"
    assert engine.tutor().hint == ""


def test_the_next_step_starts_its_own_ladder_from_the_top(lesson, at, open_loop, one_bulb):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))
    engine.on_tick(now=at(60))
    engine.on_circuit(one_bulb, now=at(61))
    engine.on_next(now=at(62))
    engine.on_next(now=at(63))

    engine.on_answer("dimmer", now=at(100))
    assert engine.tutor().hint == ""

    engine.on_tick(now=at(129.999999))
    assert engine.tutor().hint == ""  # the timer started when the build phase did

    engine.on_tick(now=at(130))
    assert engine.tutor().hint == "Where could a second bulb go?"


def test_time_outside_the_build_phase_is_never_idle_time(lesson, at, one_bulb):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(one_bulb, now=at(1))

    engine.on_tick(now=at(100))  # test
    engine.on_next(now=at(101))
    engine.on_tick(now=at(200))  # explain
    engine.on_next(now=at(201))
    engine.on_tick(now=at(300))  # predict

    assert engine.tutor().phase == "predict"
    assert engine.tutor().hint == ""
    assert engine.tutor().score == 0


def test_a_step_with_no_hints_still_notices_idle_time(prediction_lesson, at, open_loop):
    engine = LessonEngine(prediction_lesson, Progress(), now=at(0))
    engine.on_answer("dimmer", now=at(0))
    engine.on_circuit(open_loop, now=at(0))

    engine.on_tick(now=at(30))
    engine.on_tick(now=at(60))

    assert engine.tutor().phase == "build"
    assert engine.tutor().hint == ""
    assert engine.tutor().score == -1  # +1 for the prediction, -2 for the idle periods


def test_a_first_wrong_prediction_does_not_move_the_score(prediction_lesson, at):
    engine = LessonEngine(prediction_lesson, Progress(), now=at(0))

    engine.on_answer("brighter", now=at(1))

    assert engine.tutor().score == 0


def test_a_wrong_prediction_on_a_concept_got_wrong_before_is_a_repeated_error(
    prediction_lesson, at
):
    before = Progress(concepts={"series": ConceptProgress(mastery="shaky", wrong=1)})
    engine = LessonEngine(prediction_lesson, before, now=at(0))

    engine.on_answer("brighter", now=at(1))

    assert engine.tutor().score == -1


def test_a_correct_prediction_is_not_an_error_whatever_came_before(prediction_lesson, at):
    before = Progress(concepts={"series": ConceptProgress(mastery="shaky", wrong=2)})
    engine = LessonEngine(prediction_lesson, before, now=at(0))

    engine.on_answer("dimmer", now=at(1))

    assert engine.tutor().score == 1


def test_an_error_repeated_within_one_session_is_noticed(two_prediction_lesson, at, two_in_series):
    engine = LessonEngine(two_prediction_lesson, Progress(), now=at(0))
    engine.on_answer("brighter", now=at(1))
    engine.on_circuit(two_in_series, now=at(2))
    engine.on_next(now=at(3))
    engine.on_next(now=at(4))
    assert engine.tutor().score == 0

    engine.on_answer("same", now=at(5))

    assert engine.tutor().score == -1
