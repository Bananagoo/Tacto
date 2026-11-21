"""The lesson engine walks a learner through a lesson: predict, build, test, explain."""

import ast
from pathlib import Path

import tacto.learner
import tacto.lessons
from tacto.contract import Tutor
from tacto.learner.models import ConceptProgress, Progress
from tacto.lessons.engine import LessonEngine
from tacto.lessons.events import LessonCompleted, PredictionMade, StepCompleted

FIRST_STEP_DONE = Progress(
    concepts={"closed_loop": ConceptProgress(mastery="shaky")},
    completed_steps={"mini": ["close_the_loop"]},
)


def test_a_full_walk_shows_the_right_tutor_at_every_phase(lesson, at, open_loop, one_bulb):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    first = {"lesson_id": "mini", "challenge_id": "close_the_loop", "step_index": 0}
    second = {"lesson_id": "mini", "challenge_id": "series", "step_index": 1}

    # Step one has no prediction, so it opens on the build line.
    assert engine.tutor() == Tutor(
        **first, step_count=2, phase="build", prompt="Draw the missing wire."
    )

    engine.on_circuit(open_loop, now=at(1))
    assert engine.tutor().phase == "build"

    engine.on_circuit(one_bulb, now=at(2))
    assert engine.tutor() == Tutor(
        **first, step_count=2, phase="test", prompt="Rest a finger on any wire."
    )

    engine.on_next(now=at(3))
    assert engine.tutor() == Tutor(
        **first, step_count=2, phase="explain", prompt="Current flows only in a closed loop."
    )

    engine.on_next(now=at(4))
    assert engine.tutor() == Tutor(
        **second,
        step_count=2,
        phase="predict",
        prompt="What will the first bulb do?",
        choices=["dimmer", "same", "brighter"],
    )

    engine.on_answer("I think it gets dimmer", now=at(5))
    assert engine.tutor() == Tutor(
        **second,
        step_count=2,
        phase="build",
        prompt="Place the second bulb on the wire.",
        correct=True,
        score=1,
    )


def test_the_walk_ends_at_done_on_the_last_explanation(lesson, at, two_in_series):
    engine = LessonEngine(lesson, FIRST_STEP_DONE, now=at(0))
    engine.on_answer("dimmer", now=at(1))

    engine.on_circuit(two_in_series, now=at(2))
    assert engine.tutor() == Tutor(
        lesson_id="mini",
        challenge_id="series",
        step_index=1,
        step_count=2,
        phase="test",
        prompt="Slide your finger along the loop.",
        correct=True,
        score=1,
    )

    engine.on_next(now=at(3))
    assert engine.tutor().phase == "explain"
    assert engine.tutor().prompt == "The current is the same all the way round."
    assert engine.tutor().correct is True
    assert engine.tutor().feedback == ""  # nothing to correct after a right prediction

    engine.on_next(now=at(4))
    assert engine.tutor() == Tutor(
        lesson_id="mini",
        challenge_id="series",
        step_index=1,
        step_count=2,
        phase="done",
        prompt="The current is the same all the way round.",
        score=1,
    )


def test_events_come_out_in_order_with_the_times_passed_in(lesson, at, one_bulb, two_in_series):
    engine = LessonEngine(lesson, Progress(), now=at(0))

    engine.on_circuit(one_bulb, now=at(1.5))
    engine.on_next(now=at(2.25))
    engine.on_next(now=at(3.125))
    engine.on_answer("brighter", now=at(4))
    engine.on_circuit(two_in_series, now=at(5))
    engine.on_next(now=at(6))
    engine.on_next(now=at(7.000001))

    assert engine.drain_events() == [
        StepCompleted(
            step_id="close_the_loop", teaches=["closed_loop"], correct=None, at=at(3.125)
        ),
        PredictionMade(step_id="series", choice="brighter", correct=False, at=at(4)),
        StepCompleted(
            step_id="series", teaches=["current", "series"], correct=False, at=at(7.000001)
        ),
        LessonCompleted(lesson_id="mini", at=at(7.000001)),
    ]


def test_draining_events_clears_them(lesson, at, one_bulb):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(one_bulb, now=at(1))
    engine.on_next(now=at(2))
    engine.on_next(now=at(3))

    assert len(engine.drain_events()) == 1
    assert engine.drain_events() == []


def test_a_wrong_answer_still_reaches_explain_and_shows_the_misconception_line(
    lesson, at, two_in_series
):
    engine = LessonEngine(lesson, FIRST_STEP_DONE, now=at(0))

    engine.on_answer("it stays the same", now=at(1))
    assert engine.tutor().phase == "build"
    assert engine.tutor().correct is False
    assert engine.tutor().feedback == ""  # not before the learner has seen the result

    engine.on_circuit(two_in_series, now=at(2))
    assert engine.tutor().feedback == ""

    engine.on_next(now=at(3))
    explain = engine.tutor()
    assert explain.phase == "explain"
    assert explain.prompt == "The current is the same all the way round."
    assert explain.correct is False
    assert explain.feedback == "Feel the pulse: it slowed down, so less current flows."


def test_a_wrong_answer_with_no_misconception_line_has_no_feedback(lesson, at, two_in_series):
    engine = LessonEngine(lesson, FIRST_STEP_DONE, now=at(0))
    engine.on_answer("brighter", now=at(1))
    engine.on_circuit(two_in_series, now=at(2))
    engine.on_next(now=at(3))

    assert engine.tutor().phase == "explain"
    assert engine.tutor().correct is False
    assert engine.tutor().feedback == ""


def test_the_prediction_result_resets_on_the_next_step(two_prediction_lesson, at, two_in_series):
    engine = LessonEngine(two_prediction_lesson, Progress(), now=at(0))
    engine.on_answer("same", now=at(1))
    engine.on_circuit(two_in_series, now=at(2))
    engine.on_next(now=at(3))
    engine.on_next(now=at(4))

    assert engine.tutor().challenge_id == "series_again"
    assert engine.tutor().phase == "predict"
    assert engine.tutor().correct is None
    assert engine.tutor().feedback == ""


def test_predict_ignores_everything_but_an_answer_that_matches(lesson, at, two_in_series):
    engine = LessonEngine(lesson, FIRST_STEP_DONE, now=at(0))
    waiting = engine.tutor()
    assert waiting.phase == "predict"

    engine.on_next(now=at(1))
    engine.on_circuit(two_in_series, now=at(2))  # already built: the prediction still comes first
    engine.on_answer("purple", now=at(3))  # matches no choice
    engine.on_answer("dimmer or brighter", now=at(4))  # matches two
    engine.on_answer("", now=at(5))
    engine.on_tick(now=at(600))

    assert engine.tutor() == waiting
    assert engine.drain_events() == []


def test_build_ignores_answers_and_next(lesson, at, open_loop):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))
    waiting = engine.tutor()
    assert waiting.phase == "build"

    engine.on_answer("dimmer", now=at(1))
    engine.on_next(now=at(2))

    assert engine.tutor() == waiting
    assert engine.drain_events() == []


def test_test_and_explain_ignore_answers_and_the_circuit(lesson, at, open_loop, one_bulb):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(one_bulb, now=at(1))

    for phase in ("test", "explain"):
        waiting = engine.tutor()
        assert waiting.phase == phase

        engine.on_answer("dimmer", now=at(2))
        engine.on_circuit(open_loop, now=at(3))  # taking the circuit apart does not go back
        engine.on_circuit(one_bulb, now=at(4))
        engine.on_tick(now=at(600))

        assert engine.tutor() == waiting
        assert engine.drain_events() == []
        engine.on_next(now=at(5))


def test_done_ignores_everything(prediction_lesson, at, open_loop, two_in_series):
    engine = LessonEngine(prediction_lesson, Progress(), now=at(0))
    engine.on_answer("dimmer", now=at(1))
    engine.on_circuit(two_in_series, now=at(2))
    engine.on_next(now=at(3))
    engine.on_next(now=at(4))
    engine.drain_events()
    finished = engine.tutor()
    progress = engine.progress
    assert finished.phase == "done"

    engine.on_next(now=at(5))
    engine.on_answer("same", now=at(6))
    engine.on_circuit(open_loop, now=at(7))
    engine.on_circuit(two_in_series, now=at(8))
    engine.on_tick(now=at(600))

    assert engine.tutor() == finished
    assert engine.progress == progress
    assert engine.drain_events() == []


def test_a_step_already_built_waits_for_the_next_circuit_before_moving_on(
    lesson, at, two_in_series
):
    engine = LessonEngine(lesson, FIRST_STEP_DONE, now=at(0))
    engine.on_circuit(two_in_series, now=at(1))  # the second bulb is already on the mat

    engine.on_answer("dimmer", now=at(2))
    # The learner must see the build line, even if only until the next camera frame.
    assert engine.tutor().phase == "build"
    assert engine.tutor().prompt == "Place the second bulb on the wire."

    engine.on_circuit(two_in_series, now=at(2.07))
    assert engine.tutor().phase == "test"


def test_resuming_starts_at_the_first_step_not_completed(lesson, at):
    engine = LessonEngine(lesson, FIRST_STEP_DONE, now=at(0))

    tutor = engine.tutor()
    assert (tutor.challenge_id, tutor.step_index, tutor.phase) == ("series", 1, "predict")
    assert engine.drain_events() == []


def test_resuming_a_finished_lesson_is_done(lesson, at):
    finished = Progress(completed_steps={"mini": ["close_the_loop", "series"]})

    engine = LessonEngine(lesson, finished, now=at(0))

    assert engine.tutor() == Tutor(
        lesson_id="mini",
        challenge_id="series",
        step_index=1,
        step_count=2,
        phase="done",
        prompt="The current is the same all the way round.",
    )
    assert engine.drain_events() == []  # nothing happened in this session
    assert engine.progress == finished


def test_steps_completed_in_another_lesson_do_not_count(lesson, at):
    elsewhere = Progress(completed_steps={"other": ["close_the_loop", "series"]})

    engine = LessonEngine(lesson, elsewhere, now=at(0))

    assert engine.tutor().challenge_id == "close_the_loop"


def test_progress_is_updated_at_the_moment_a_step_completes(lesson, at, one_bulb):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(one_bulb, now=at(1))
    engine.on_next(now=at(2))
    assert engine.progress == Progress()  # still in explain

    engine.on_next(now=at(3))

    assert engine.progress == FIRST_STEP_DONE


def test_a_prediction_updates_mastery_when_its_step_completes(lesson, at, two_in_series):
    engine = LessonEngine(lesson, FIRST_STEP_DONE, now=at(0))
    engine.on_answer("same", now=at(1))
    engine.on_circuit(two_in_series, now=at(2))
    engine.on_next(now=at(3))
    engine.on_next(now=at(4))

    assert engine.progress.completed_steps == {"mini": ["close_the_loop", "series"]}
    assert engine.progress.concepts["current"] == ConceptProgress(mastery="shaky", wrong=1)
    assert engine.progress.concepts["series"] == ConceptProgress(mastery="shaky", wrong=1)


def test_the_progress_handed_in_is_never_mutated(lesson, at, one_bulb, two_in_series):
    handed_in = Progress(concepts={"current": ConceptProgress(mastery="solid", correct=1)})
    snapshot = handed_in.model_copy(deep=True)
    engine = LessonEngine(lesson, handed_in, now=at(0))

    engine.on_circuit(one_bulb, now=at(1))
    engine.on_next(now=at(2))
    engine.on_next(now=at(3))
    after_first_step = engine.progress
    after_first_snapshot = after_first_step.model_copy(deep=True)
    engine.on_answer("same", now=at(4))
    engine.on_circuit(two_in_series, now=at(5))
    engine.on_next(now=at(6))
    engine.on_next(now=at(7))

    assert handed_in == snapshot
    # A progress value read earlier is a snapshot too: later steps do not reach into it.
    assert after_first_step == after_first_snapshot
    assert engine.progress != after_first_step


def test_changing_the_progress_handed_in_later_does_not_move_the_engine(lesson, at):
    handed_in = Progress()
    engine = LessonEngine(lesson, handed_in, now=at(0))

    handed_in.completed_steps["mini"] = ["close_the_loop", "series"]

    assert engine.progress == Progress()


def test_the_same_circuit_fifteen_times_a_second_changes_and_emits_nothing(lesson, at, open_loop):
    engine = LessonEngine(lesson, Progress(), now=at(0))
    engine.on_circuit(open_loop, now=at(0))
    waiting = engine.tutor()

    for frame in range(1, 15 * 20):  # twenty seconds of camera frames
        engine.on_circuit(open_loop.model_copy(deep=True), now=at(frame / 15))
        engine.on_tick(now=at(frame / 15))

    assert engine.tutor() == waiting
    assert engine.drain_events() == []
    assert engine.progress == Progress()


def test_a_satisfying_circuit_fed_repeatedly_advances_one_phase_only(lesson, at, one_bulb):
    engine = LessonEngine(lesson, Progress(), now=at(0))

    for frame in range(30):
        engine.on_circuit(one_bulb, now=at(frame / 15))

    assert engine.tutor().phase == "test"
    assert engine.drain_events() == []


def test_a_lesson_with_a_single_step_works(prediction_lesson, at, two_in_series):
    engine = LessonEngine(prediction_lesson, Progress(), now=at(0))
    assert engine.tutor().step_count == 1
    assert engine.tutor().phase == "predict"

    engine.on_answer("darker", now=at(1))
    engine.on_circuit(two_in_series, now=at(2))
    engine.on_next(now=at(3))
    engine.on_next(now=at(4))

    assert engine.tutor().phase == "done"
    assert [type(event) for event in engine.drain_events()] == [
        PredictionMade,
        StepCompleted,
        LessonCompleted,
    ]
    assert engine.progress.completed_steps == {"mini": ["series"]}


def test_an_answer_arriving_twice_counts_once(prediction_lesson, at):
    engine = LessonEngine(prediction_lesson, Progress(), now=at(0))

    engine.on_answer("dimmer", now=at(1))  # the voice
    engine.on_answer("dimmer", now=at(1))  # and the button, together
    engine.on_answer("brighter", now=at(1.2))  # a change of mind is too late

    assert engine.drain_events() == [
        PredictionMade(step_id="series", choice="dimmer", correct=True, at=at(1))
    ]
    assert engine.tutor().score == 1
    assert engine.tutor().correct is True


def test_the_same_inputs_give_the_same_outputs_to_the_microsecond(
    lesson, at, one_bulb, two_in_series
):
    def run() -> tuple[list, Tutor, Progress]:
        engine = LessonEngine(lesson, Progress(), now=at(0))
        engine.on_tick(now=at(31.000001))
        engine.on_circuit(one_bulb, now=at(40.5))
        engine.on_next(now=at(41))
        engine.on_next(now=at(42.999999))
        engine.on_answer("same", now=at(50))
        engine.on_tick(now=at(85))
        engine.on_circuit(two_in_series, now=at(90))
        engine.on_next(now=at(91))
        engine.on_next(now=at(92.000007))
        return engine.drain_events(), engine.tutor(), engine.progress

    first, second = run(), run()

    assert first == second
    assert first[0][-1] == LessonCompleted(lesson_id="mini", at=at(92.000007))


def test_the_engine_and_learner_modules_never_read_a_clock():
    """Time is always passed in, so nothing here may ask the system for it."""
    clock_reads = {"now", "utcnow", "today", "time", "monotonic", "perf_counter"}
    modules = [
        Path(tacto.lessons.__file__).parent / name
        for name in ("conditions.py", "matching.py", "events.py", "engine.py")
    ] + [
        Path(tacto.learner.__file__).parent / name for name in ("mastery.py", "zone.py", "graph.py")
    ]

    for module in modules:
        tree = ast.parse(module.read_text(), filename=str(module))
        called = {
            node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
        }
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import | ast.ImportFrom)
            for alias in node.names
        }
        assert not called & clock_reads, f"{module.name} reads a clock"
        assert "time" not in imported, f"{module.name} imports time"
