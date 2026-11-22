"""Every move the funnel can make. No clock, no network, no lesson file: the rules alone."""

import itertools

import pytest

from tacto.funnel import FunnelState, answer, on_mat, start
from tacto.lesson import Funnel

FUNNEL = Funnel.model_validate(
    {
        "target_idea": "More voltage, more current.",
        "confirmation": "Yes, more current.",
        "levels": [
            {"question": "Q0 why?", "correct_examples": ["a", "b"]},
            {"question": "Q1 what does it do?", "correct_examples": ["a", "b"]},
            {
                "question": "Q2 more or less?",
                "correct_examples": ["a", "b"],
                "confirmation": "More, exactly.",
            },
        ],
        "exit": {
            "line": "It is the current. Turn it down, then up.",
            "then": [{"max_voltage": 3}, {"min_voltage": 6}],
            "timeout_seconds": 20,
        },
    }
)
ONE_LEVEL = Funnel.model_validate(
    {
        "target_idea": "t",
        "confirmation": "Yes.",
        "levels": [{"question": "Only question?", "correct_examples": ["a", "b"]}],
        "exit": {"line": "Here is the idea. Touch it.", "then": [{"touching": "bulb"}]},
    }
)
LABELS = ("correct", "partial", "incorrect", "unclear")


def play(funnel: Funnel, *labels: str, now: float = 100.0):
    """Start a funnel and give it these answers. Returns the state and every line spoken."""
    state, line = start(funnel)
    lines = [line]
    for label in labels:
        state, line = answer(funnel, state, label, now)
        lines.append(line)
    return state, lines


# ---------- asking ----------


def test_it_opens_with_the_first_question():
    state, line = start(FUNNEL)
    assert line == "Q0 why?"
    assert (state.status, state.level, state.repeated) == ("asking", 0, False)


@pytest.mark.parametrize("level", [0, 1, 2])
def test_correct_at_any_level_confirms_and_resolves(level):
    state, lines = play(FUNNEL, *(["partial"] * level), "correct")
    assert state.status == "resolved" and state.outcome == "correct" and state.level == level
    assert lines[-1] == ("More, exactly." if level == 2 else "Yes, more current.")


@pytest.mark.parametrize("label", ["partial", "incorrect"])
def test_a_miss_goes_down_one_level_and_asks_the_narrower_question(label):
    state, lines = play(FUNNEL, label)
    assert (state.status, state.level) == ("asking", 1) and lines[-1] == "Q1 what does it do?"
    state, lines = play(FUNNEL, label, label)
    assert (state.status, state.level) == ("asking", 2) and lines[-1] == "Q2 more or less?"


@pytest.mark.parametrize("label", ["partial", "incorrect"])
def test_a_miss_at_the_last_level_goes_to_the_exit_and_states_the_idea(label):
    state, lines = play(FUNNEL, "partial", "incorrect", label, now=50.0)
    assert state.status == "exit" and state.exit_goal == 0 and state.exit_started_s == 50.0
    assert lines[-1] == "It is the current. Turn it down, then up."


def test_a_funnel_with_one_question_goes_straight_from_a_miss_to_the_exit():
    state, lines = play(ONE_LEVEL, "incorrect")
    assert state.status == "exit" and lines[-1] == "Here is the idea. Touch it."


# ---------- unclear ----------


def test_unclear_repeats_the_same_question_once_without_using_a_level():
    state, lines = play(FUNNEL, "unclear")
    assert (state.status, state.level, state.repeated) == ("asking", 0, True)
    assert lines[-1] == "Q0 why?"


def test_a_second_unclear_in_a_row_counts_as_partial():
    state, lines = play(FUNNEL, "unclear", "unclear")
    assert (state.status, state.level, state.repeated) == ("asking", 1, False)
    assert lines[-1] == "Q1 what does it do?"


def test_each_question_gets_its_own_one_repeat():
    state, lines = play(FUNNEL, "unclear", "partial", "unclear")
    assert (state.level, state.repeated) == (1, True) and lines[-1] == "Q1 what does it do?"
    state, lines = play(FUNNEL, "unclear", "partial", "unclear", "unclear")
    assert (state.level, state.repeated) == (2, False)


def test_a_repeated_question_can_still_be_answered_correctly():
    state, lines = play(FUNNEL, "unclear", "correct")
    assert state.status == "resolved" and state.level == 0 and lines[-1] == "Yes, more current."


def test_two_unclear_at_the_last_level_go_to_the_exit():
    state, _ = play(FUNNEL, "partial", "partial", "unclear", "unclear")
    assert state.status == "exit"


# ---------- the exit ----------


def at_exit(funnel: Funnel = FUNNEL, started: float = 50.0) -> FunnelState:
    state, _ = play(funnel, *(["partial"] * len(funnel.levels)), now=started)
    assert state.status == "exit"
    return state


def test_exit_goals_are_met_one_after_another_and_the_last_one_resolves():
    state = at_exit()
    state, line = on_mat(FUNNEL, state, goal_met=False, now=51.0)
    assert state.status == "exit" and state.exit_goal == 0 and line is None
    state, line = on_mat(FUNNEL, state, goal_met=True, now=52.0)
    assert state.status == "exit" and state.exit_goal == 1 and line is None
    state, line = on_mat(FUNNEL, state, goal_met=True, now=53.0)
    assert state.status == "resolved" and state.outcome == "exit_done" and line is None


def test_the_exit_gives_up_waiting_after_its_timeout():
    state = at_exit(started=50.0)
    state, _ = on_mat(FUNNEL, state, goal_met=False, now=69.9)
    assert state.status == "exit"
    state, line = on_mat(FUNNEL, state, goal_met=False, now=70.0)
    assert state.status == "resolved" and state.outcome == "exit_timeout" and line is None


def test_the_timeout_runs_from_the_start_of_the_exit_not_from_each_goal():
    state = at_exit(started=50.0)
    state, _ = on_mat(FUNNEL, state, goal_met=True, now=65.0)
    state, _ = on_mat(FUNNEL, state, goal_met=False, now=70.5)
    assert state.outcome == "exit_timeout"


def test_a_goal_met_on_the_same_look_that_times_out_still_counts():
    state = at_exit(ONE_LEVEL, started=50.0)
    state, _ = on_mat(ONE_LEVEL, state, goal_met=True, now=75.0)
    assert state.outcome == "exit_done"


# ---------- things that must not happen ----------


def test_the_mat_cannot_end_a_question():
    state, _ = start(FUNNEL)
    after, line = on_mat(FUNNEL, state, goal_met=True, now=9999.0)
    assert after == state and line is None


@pytest.mark.parametrize("label", LABELS)
def test_an_answer_during_the_exit_or_after_the_end_changes_nothing(label):
    exiting = at_exit()
    assert answer(FUNNEL, exiting, label, 60.0) == (exiting, None)
    done, _ = play(FUNNEL, "correct")
    assert answer(FUNNEL, done, label, 60.0) == (done, None)
    assert on_mat(FUNNEL, done, goal_met=True, now=60.0) == (done, None)


def test_an_unknown_label_is_treated_as_partial():
    state, _ = start(FUNNEL)
    state, line = answer(FUNNEL, state, "banana", 1.0)
    assert (state.level, line) == (1, "Q1 what does it do?")


def test_no_run_of_answers_can_loop_or_ask_more_than_three_graded_questions():
    """Every sequence of labels: at most three questions graded, and it always ends."""
    longest = 0
    for labels in itertools.product(LABELS, repeat=6):
        state, _ = start(FUNNEL)
        for count, label in enumerate(labels, start=1):
            state, _ = answer(FUNNEL, state, label, 1.0)
            if state.status != "asking":
                longest = max(longest, count)
                break
        else:
            pytest.fail(f"still asking after six answers: {labels}")
        assert state.graded <= 3, labels
    # Three questions, each repeated once: six answers at most.
    assert longest == 6


def test_what_was_graded_is_counted_and_a_first_unclear_is_not():
    assert play(FUNNEL, "unclear")[0].graded == 0
    assert play(FUNNEL, "unclear", "unclear")[0].graded == 1
    assert play(FUNNEL, "partial", "incorrect", "partial")[0].graded == 3
