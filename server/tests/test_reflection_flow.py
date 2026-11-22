"""Reflections driven end to end by answers and the mat, with a stand-in grader.

The lesson is the real one (lessons/circuits-101.yaml); the circuits are solved for real;
only the grading is faked: an answer's text is the label it gets.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from tacto.contract import CLIENT_MESSAGE, AnswerReflection, Grid, SetMode, Touch
from tacto.grader import Grade
from tacto.lab import Lab, MatView
from tacto.lesson import CONFIRM_SECONDS, LessonRunner, circuit_summary, load_lesson
from tacto.pieces import solve_pieces
from tacto_mock.scenario import BATTERY, BOTTOM, BRANCH, BULB_A, branch, loop

LESSON = load_lesson(Path(__file__).resolve().parents[2] / "lessons" / "circuits-101.yaml")
GRID = Grid(cols=9, rows=6)
CIRCUITS = {
    "open": loop(closed=False),
    "one_bulb": loop(closed=True),
    "series": loop(closed=True, bottom="bulb"),
    "parallel": loop(closed=True) + branch("bulb"),
}
# What finishes each step: circuit, volts, the piece under the fingertip.
FINISH = {
    "setup": ("open", 3.0, None),
    "close_the_loop": ("one_bulb", 3.0, None),
    "feel_current": ("one_bulb", 3.0, BULB_A),
    "raise_voltage": ("one_bulb", 6.0, BULB_A),
    "series": ("series", 6.0, BULB_A),
    "parallel": ("parallel", 6.0, BATTERY),
}
# What meets each reflection's exit, goal by goal.
EXIT = {
    "raise_voltage": [("one_bulb", 3.0, BULB_A), ("one_bulb", 6.0, BULB_A)],
    "series": [("series", 6.0, BOTTOM)],
    "parallel": [("parallel", 6.0, BRANCH), ("parallel", 6.0, BATTERY)],
}
REFLECTING = ("raise_voltage", "series", "parallel")
STEP_IDS = [step.id for step in LESSON.steps]


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def seen(action):
    name, volts, piece_id = action
    return (
        *solve_pieces(CIRCUITS[name], volts),
        Touch(present=piece_id is not None, piece_id=piece_id),
    )


class Session:
    """One learner at the lesson: a runner, its clock, and what is on the mat."""

    def __init__(self, *, adaptive: bool = True) -> None:
        self.clock = Clock()
        self.runner = LessonRunner(LESSON, now=self.clock, adaptive=adaptive)
        self.action = FINISH["setup"]

    def look(self, seconds: float = 0.0):
        self.clock.t += seconds
        return self.runner.update(*seen(self.action))

    def hold(self, action, seconds: float = 0.6):
        """Put this on the mat and keep it there."""
        self.action = action
        self.look()
        return self.look(seconds)

    def reach(self, step_id: str):
        """Work through the lesson until `step_id` has just been finished."""
        for current in STEP_IDS:
            state = self.hold(FINISH[current])
            assert state.step_id == current and state.step_done, current
            if current == step_id:
                return state
            if state.reflection is None:
                self.look(LESSON.linger_seconds + 0.1)
            else:
                self.runner.continue_step(current)
        raise AssertionError(step_id)

    def say(self, label: str):
        """Answer the question; the stand-in grader gives the answer this label."""
        ticket = self.runner.begin_answer(self.look().step_id, f"i said {label}")
        assert ticket is not None
        self.runner.finish_answer(ticket, label)
        return self.look()


def funnel_of(step_id: str):
    return next(step for step in LESSON.steps if step.id == step_id).funnel


# ---------- off: exactly as before ----------


def test_with_adaptive_off_a_reflection_is_one_question_and_continue():
    session = Session(adaptive=False)
    state = session.reach("raise_voltage")
    assert state.reflection == "Why did the pulse get faster when you raised the voltage?"
    assert (state.reflection_status, state.reflection_level, state.reflection_line) == (
        None,
        None,
        None,
    )
    assert session.runner.begin_answer("raise_voltage", "more current") is None
    assert session.look(120).step_id == "raise_voltage"  # it waits for ever
    session.runner.continue_step("raise_voltage")
    assert session.look().step_id == "series"


# ---------- asking and answering ----------


@pytest.mark.parametrize("step_id", REFLECTING)
def test_finishing_a_reflecting_step_asks_its_opening_question(step_id):
    session = Session()
    state = session.reach(step_id)
    opening = funnel_of(step_id).levels[0].question
    assert (state.reflection_status, state.reflection_level) == ("asking", 0)
    assert state.reflection == state.reflection_line == opening
    assert state.reflection_line_id == 1 and state.reflection_transcript is None


def test_an_answer_is_shown_and_the_lab_thinks_until_it_is_graded():
    session = Session()
    session.reach("raise_voltage")
    ticket = session.runner.begin_answer("raise_voltage", "  more push   so more flow ")
    state = session.look()
    assert state.reflection_status == "thinking"
    assert state.reflection_transcript == "more push so more flow"
    assert session.runner.begin_answer("raise_voltage", "again") is None  # one at a time
    session.runner.finish_answer(ticket, "correct")
    assert session.look().reflection_status == "resolved"


@pytest.mark.parametrize("step_id", REFLECTING)
@pytest.mark.parametrize("misses", [0, 1, 2])
def test_a_correct_answer_at_any_level_confirms_then_moves_on(step_id, misses):
    session = Session()
    session.reach(step_id)
    for _ in range(misses):
        session.say("partial")
    state = session.say("correct")
    assert state.reflection_status == "resolved" and state.reflection_level == misses
    assert state.reflection_line == funnel_of(step_id).confirmation_at(misses)
    # The confirmation stays up long enough to be heard, then the lesson goes on.
    assert session.look(CONFIRM_SECONDS - 0.5).step_id == step_id
    after = session.look(1.0)
    if step_id == "parallel":
        assert after.lesson_done and after.reflection is None
    else:
        assert after.step_id == STEP_IDS[STEP_IDS.index(step_id) + 1]
        assert after.reflection_status is None and after.reflection_line is None


@pytest.mark.parametrize("label", ["partial", "incorrect"])
def test_a_miss_asks_the_narrower_question_as_a_new_line(label):
    session = Session()
    first = session.reach("series")
    state = session.say(label)
    narrower = funnel_of("series").levels[1].question
    assert (state.reflection_status, state.reflection_level) == ("asking", 1)
    assert state.reflection == state.reflection_line == narrower
    assert state.reflection_line_id == first.reflection_line_id + 1


def test_unclear_asks_the_same_question_again_as_a_new_line_then_counts_as_a_miss():
    session = Session()
    first = session.reach("parallel")
    again = session.say("unclear")
    assert again.reflection_level == 0 and again.reflection_line == first.reflection_line
    assert again.reflection_line_id == first.reflection_line_id + 1  # so it is spoken again
    assert session.say("unclear").reflection_level == 1


# ---------- the exit ----------


@pytest.mark.parametrize("step_id", REFLECTING)
def test_three_misses_state_the_idea_and_the_mat_finishes_it(step_id):
    session = Session()
    session.reach(step_id)
    for _ in range(2):
        session.say("incorrect")
    state = session.say("partial")
    assert state.reflection_status == "exit"
    assert state.reflection_line == funnel_of(step_id).exit.line
    for action in EXIT[step_id]:
        assert session.look().step_id == step_id
        state = session.hold(action)
    if step_id == "parallel":
        assert state.lesson_done
    else:
        assert state.step_id == STEP_IDS[STEP_IDS.index(step_id) + 1]


def test_the_exit_moves_on_after_twenty_seconds_if_nothing_is_done():
    session = Session()
    session.reach("raise_voltage")
    for label in ("partial", "partial", "partial"):
        session.say(label)
    assert session.look(19.0).step_id == "raise_voltage"
    assert session.look(1.5).step_id == "series"


def test_the_other_bulb_means_not_the_one_touched_when_the_step_finished():
    session = Session()
    session.reach("series")  # finished with a finger on bulb A
    for label in ("partial", "partial", "partial"):
        session.say(label)
    assert session.hold(("series", 6.0, BULB_A), 2.0).step_id == "series"
    assert session.hold(("series", 6.0, BOTTOM)).step_id == "parallel"


def test_exit_goals_count_only_in_order_and_only_while_the_mat_is_seen():
    session = Session()
    session.reach("raise_voltage")
    for label in ("partial", "partial", "partial"):
        session.say(label)
    # Already at 6 V with a finger on the bulb: that is the second goal, not the first.
    assert session.hold(("one_bulb", 6.0, BULB_A), 2.0).reflection_status == "exit"
    hidden = seen(("one_bulb", 3.0, BULB_A))
    session.runner.update(*hidden, mat_visible=False)
    session.clock.t += 2.0
    assert session.runner.update(*hidden, mat_visible=False).reflection_status == "exit"
    session.hold(("one_bulb", 3.0, BULB_A))
    assert session.hold(("one_bulb", 6.0, BULB_A)).step_id == "series"


def test_an_answer_during_the_exit_is_not_taken():
    session = Session()
    session.reach("series")
    for label in ("partial", "partial", "partial"):
        session.say(label)
    assert session.runner.begin_answer("series", "harder") is None


# ---------- answers that arrive too late or for the wrong thing ----------


def test_a_grade_for_a_question_that_is_no_longer_asked_is_dropped():
    session = Session()
    session.reach("raise_voltage")
    ticket = session.runner.begin_answer("raise_voltage", "more current")
    session.runner.restart()
    session.runner.finish_answer(ticket, "correct")
    assert session.look().step_id == "setup" and session.look().reflection_status is None

    session = Session()
    session.reach("raise_voltage")
    stale = session.runner.begin_answer("raise_voltage", "first try")
    session.runner.continue_step("raise_voltage")  # skipped while it was thinking
    session.runner.finish_answer(stale, "correct")
    assert session.look().step_id == "series" and not session.look().step_done


def test_an_answer_for_another_step_or_before_the_question_is_not_taken():
    session = Session()
    assert session.runner.begin_answer("setup", "hello") is None
    session.reach("raise_voltage")
    assert session.runner.begin_answer("series", "harder") is None
    assert session.runner.begin_answer("raise_voltage", "   ") is not None  # silence is graded


def test_continue_skips_a_funnel_at_any_point():
    session = Session()
    session.reach("raise_voltage")
    session.say("partial")
    session.runner.continue_step("raise_voltage")
    state = session.look()
    assert state.step_id == "series" and state.reflection_status is None


def test_restart_clears_a_reflection_in_progress():
    session = Session()
    session.reach("series")
    session.say("partial")
    session.runner.restart()
    state = session.look()
    assert (state.step_id, state.reflection, state.reflection_line_id) == ("setup", None, 0)


def test_every_reflection_can_be_driven_through_every_path():
    """Each of the three reflections, by each way out: right at each level, and the exit."""
    for step_id in REFLECTING:
        for misses in range(4):
            session = Session()
            session.reach(step_id)
            for _ in range(min(misses, 3)):
                session.say("incorrect")
            if misses < 3:
                session.say("correct")
                state = session.look(CONFIRM_SECONDS + 0.1)
            else:
                for action in EXIT[step_id]:
                    state = session.hold(action)
            assert state.lesson_done or state.step_id != step_id, (step_id, misses)


# ---------- what the grader is told about the mat ----------


def test_the_circuit_is_summed_up_in_a_line_for_the_grader():
    assert circuit_summary(*solve_pieces(CIRCUITS["series"], 6.0)) == (
        "One battery at 6 V. 2 bulbs, 2 lit, in series. 0.30 A at the battery. "
        "The circuit is working."
    )
    assert "in parallel" in circuit_summary(*solve_pieces(CIRCUITS["parallel"], 6.0))
    assert circuit_summary(*solve_pieces(CIRCUITS["open"], 3.0)) == (
        "One battery at 3 V. 1 bulb, 0 lit. 0.00 A at the battery. The circuit is open."
    )


# ---------- through the lab, as the browser drives it ----------


class Mat:
    def __init__(self) -> None:
        self.show(FINISH["setup"])

    def show(self, action) -> None:
        name, _, piece_id = action
        placed = tuple(CIRCUITS[name])
        finger = None
        if piece_id is not None:
            piece = next(p for p in placed if p.id == piece_id)
            finger = ((piece.a[0] + piece.b[0]) / 2 / 8, (piece.a[1] + piece.b[1]) / 2 / 5)
        self.current = MatView(placed, finger)

    def view(self) -> MatView:
        return self.current


class LabSession:
    """A lab in Lab mode at the first reflection, with grading run when the test says."""

    def __init__(self, grader="default", audio_for=None) -> None:
        self.clock, self.mat, self.asked, self.waiting = Clock(), Mat(), [], []

        def grade(transcript, *, funnel, level, circuit):
            self.asked.append((transcript, funnel, level, circuit))
            return Grade(label=transcript)

        self.lab = Lab(
            GRID,
            self.mat,
            source_name="replay",
            lesson=LessonRunner(LESSON, now=self.clock, adaptive=True, audio_for=audio_for),
            grader=grade if grader == "default" else grader,
            background=self.waiting.append,
            now=self.clock,
        )
        self.lab.handle(SetMode(mode="lab"))
        for step_id in ("setup", "close_the_loop", "feel_current", "raise_voltage"):
            name, volts, _ = FINISH[step_id]
            self.lab.handle(CLIENT_MESSAGE.validate_python({"type": "set_voltage", "volts": volts}))
            self.mat.show(FINISH[step_id])
            self.lab.state()
            self.clock.t += 0.6
            state = self.lab.state()
            assert state.lesson.step_id == step_id and state.lesson.step_done, step_id
            if step_id != "raise_voltage":
                self.clock.t += LESSON.linger_seconds + 0.1
                self.lab.state()

    def answer(self, text: str) -> None:
        self.lab.handle(AnswerReflection(step_id="raise_voltage", text=text))

    def grade_now(self) -> None:
        while self.waiting:
            self.waiting.pop(0)()


def test_a_typed_answer_is_graded_off_the_state_loop_and_moves_the_funnel():
    session = LabSession()
    session.answer("partial")
    # Grading has not run yet: the lab keeps sending states and says it is thinking.
    lesson = session.lab.state().lesson
    assert (lesson.reflection_status, lesson.reflection_transcript) == ("thinking", "partial")
    session.grade_now()
    lesson = session.lab.state().lesson
    assert (lesson.reflection_status, lesson.reflection_level) == ("asking", 1)
    transcript, funnel, level, circuit = session.asked[0]
    assert (transcript, level) == ("partial", 0) and funnel is funnel_of("raise_voltage")
    assert circuit.startswith("One battery at 6 V. 1 bulb, 1 lit")


@pytest.mark.parametrize("what", ["no grader", "a grader that raises"])
def test_when_grading_cannot_happen_the_answer_counts_as_partial(what):
    def broken(transcript, *, funnel, level, circuit):
        raise RuntimeError("no network")

    session = LabSession(grader=None if what == "no grader" else broken)
    session.answer("more current")
    session.grade_now()
    lesson = session.lab.state().lesson
    assert (lesson.reflection_status, lesson.reflection_level) == ("asking", 1), what


def test_answers_are_ignored_in_tinker_mode():
    session = LabSession()
    session.lab.handle(SetMode(mode="tinker"))
    session.answer("correct")
    assert session.waiting == [] and session.asked == []


def test_the_answer_message_is_one_of_the_browsers_messages_and_is_bounded():
    message = CLIENT_MESSAGE.validate_json(
        '{"type": "answer_reflection", "step_id": "series", "text": "its harder"}'
    )
    assert isinstance(message, AnswerReflection) and message.text == "its harder"
    with pytest.raises(ValidationError):
        AnswerReflection(step_id="series", text="x" * 2001)
    with pytest.raises(ValidationError):
        CLIENT_MESSAGE.validate_json('{"type": "answer_reflection", "step_id": "series"}')


# ---------- the lab's voice ----------


def spoken_session() -> Session:
    """A session where every line has audio, named after its first word."""
    session = Session()
    session.runner = LessonRunner(
        LESSON,
        now=session.clock,
        adaptive=True,
        audio_for=lambda line: f"/voice/{line.split()[0].lower()}.wav",
    )
    return session


def test_each_line_comes_with_its_audio_when_there_is_some():
    session = spoken_session()
    state = session.reach("raise_voltage")
    assert state.reflection_audio == "/voice/why.wav"
    assert session.say("partial").reflection_audio == "/voice/the.wav"
    assert session.say("correct").reflection_audio == "/voice/yes..wav"


def test_a_line_with_no_audio_is_shown_and_not_named():
    session = Session()
    session.runner = LessonRunner(
        LESSON, now=session.clock, adaptive=True, audio_for=lambda line: None
    )
    state = session.reach("raise_voltage")
    assert state.reflection_line is not None and state.reflection_audio is None
    assert Session(adaptive=False).reach("raise_voltage").reflection_audio is None


def test_a_spoken_confirmation_is_waited_for_then_the_lesson_moves_on():
    from tacto.lesson import AFTER_HEARD_SECONDS, CONFIRM_MAX_SECONDS

    session = spoken_session()
    session.reach("raise_voltage")
    state = session.say("correct")
    # Longer than the silent pause: the line is still being said.
    assert session.look(CONFIRM_SECONDS + 1.0).step_id == "raise_voltage"
    session.runner.line_heard("raise_voltage", state.reflection_line_id)
    assert session.look(AFTER_HEARD_SECONDS - 0.2).step_id == "raise_voltage"
    assert session.look(0.3).step_id == "series"

    # If the browser never says it finished, the lesson still moves on.
    session = spoken_session()
    session.reach("raise_voltage")
    session.say("correct")
    assert session.look(CONFIRM_MAX_SECONDS - 0.5).step_id == "raise_voltage"
    assert session.look(1.0).step_id == "series"


def test_hearing_an_earlier_line_or_another_steps_line_changes_nothing():
    session = spoken_session()
    first = session.reach("raise_voltage")
    session.say("partial")
    state = session.say("correct")
    session.runner.line_heard("raise_voltage", first.reflection_line_id)
    session.runner.line_heard("series", state.reflection_line_id)
    assert session.look(CONFIRM_SECONDS + 1.0).step_id == "raise_voltage"


def test_the_heard_message_reaches_the_lesson_through_the_lab():
    from tacto.contract import ReflectionHeard

    message = CLIENT_MESSAGE.validate_json(
        '{"type": "reflection_heard", "step_id": "raise_voltage", "line_id": 2}'
    )
    assert isinstance(message, ReflectionHeard) and message.line_id == 2

    session = LabSession(audio_for=lambda line: "/voice/x.wav")
    session.answer("correct")
    session.grade_now()
    lesson = session.lab.state().lesson
    assert lesson.reflection_status == "resolved"
    session.clock.t += CONFIRM_SECONDS + 1.0
    assert session.lab.state().lesson.step_id == "raise_voltage"
    session.lab.handle(ReflectionHeard(step_id="raise_voltage", line_id=lesson.reflection_line_id))
    session.clock.t += 1.0
    assert session.lab.state().lesson.step_id == "series"
