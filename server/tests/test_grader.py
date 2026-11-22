"""The answer grader against a fake Together: what it sends, and that every failure is 'partial'."""

import json

import httpx
import pytest

from tacto import grader, voice_models
from tacto.grader import Grade, grade
from tacto.lesson import Funnel

FUNNEL = Funnel.model_validate(
    {
        "target_idea": "A higher voltage pushes more current through the bulb.",
        "confirmation": "Yes.",
        "misconceptions": [
            {"tag": "pulse_is_voltage", "description": "Thinks the pulse is the voltage itself."},
            {"tag": "brightness_only", "description": "Only says the bulb got brighter."},
        ],
        "levels": [
            {
                "question": "Why did the pulse get faster?",
                "correct_examples": ["more voltage pushes more current", "more push more flow"],
            },
            {
                "question": "More current, or less?",
                "correct_examples": ["more", "more current"],
            },
        ],
        "exit": {"line": "x", "then": [{"touching": "bulb"}]},
    }
)
PARTIAL = Grade(label="partial")


class FakeTogether:
    """Answers every chat request with `reply`, and keeps what it was sent."""

    def __init__(self, reply=None, *, status=200, raises=None, finish="stop") -> None:
        self.reply = {"label": "correct", "misconception": None, "ideas_matched": ["more current"]}
        if reply is not None:
            self.reply = reply
        self.status, self.raises, self.finish = status, raises, finish
        self.requests: list[httpx.Request] = []

    def client(self) -> httpx.Client:
        return httpx.Client(
            base_url=voice_models.BASE_URL,
            transport=httpx.MockTransport(self._handle),
            headers={"Authorization": "Bearer test-key"},
        )

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.raises is not None:
            raise self.raises
        content = self.reply if isinstance(self.reply, str) else json.dumps(self.reply)
        body = {"choices": [{"finish_reason": self.finish, "message": {"content": content}}]}
        return httpx.Response(self.status, json=body)

    @property
    def sent(self) -> dict:
        return json.loads(self.requests[-1].content)


def ask(fake: FakeTogether, transcript: str = "more push so more flow", level: int = 0) -> Grade:
    return grade(
        transcript,
        funnel=FUNNEL,
        level=level,
        circuit="One bulb lit at 6 V, 0.6 A through it.",
        client=fake.client(),
    )


# ---------- what it sends ----------


def test_a_good_reply_comes_back_as_the_grade():
    fake = FakeTogether()
    assert ask(fake) == Grade(label="correct", misconception=None, ideas_matched=["more current"])
    assert len(fake.requests) == 1
    assert fake.requests[0].url.path.endswith("/chat/completions")


def test_it_asks_for_a_fixed_shape_at_temperature_zero_with_reasoning_off():
    fake = FakeTogether()
    ask(fake)
    sent = fake.sent
    assert sent["model"] == voice_models.GRADER_MODEL
    assert sent["temperature"] == 0 and sent["reasoning"] == {"enabled": False}
    schema = sent["response_format"]["json_schema"]["schema"]
    assert sent["response_format"]["type"] == "json_schema"
    assert schema["properties"]["label"]["enum"] == ["correct", "partial", "incorrect", "unclear"]
    # Only this question's tags may come back, or none.
    assert schema["properties"]["misconception"]["enum"] == [
        "pulse_is_voltage",
        "brightness_only",
        None,
    ]
    assert schema["additionalProperties"] is False


def test_the_model_is_given_the_question_the_rubric_the_circuit_and_the_answer():
    fake = FakeTogether()
    ask(fake, "it pushes more", level=1)
    text = json.dumps(fake.sent["messages"])
    for needed in (
        "More current, or less?",  # the question at this level, not the opening one
        "A higher voltage pushes more current through the bulb.",
        "more current",  # this level's example answers
        "pulse_is_voltage",
        "Thinks the pulse is the voltage itself.",
        "One bulb lit at 6 V, 0.6 A through it.",
        "it pushes more",
    ):
        assert needed in text, needed
    assert "Why did the pulse get faster?" not in text


def test_the_reply_is_told_to_be_json_in_words_as_well_as_by_schema():
    fake = FakeTogether()
    ask(fake)
    system = fake.sent["messages"][0]
    assert system["role"] == "system" and "JSON" in system["content"]


# ---------- an answer that is not one ----------


@pytest.mark.parametrize("transcript", ["", "   ", "\n"])
def test_silence_is_unclear_and_the_model_is_not_asked(transcript):
    fake = FakeTogether()
    assert ask(fake, transcript) == Grade(label="unclear")
    assert fake.requests == []


# ---------- fail towards more help ----------


@pytest.mark.parametrize(
    "what, fake",
    [
        ("a timeout", FakeTogether(raises=httpx.ReadTimeout("slow"))),
        ("no connection", FakeTogether(raises=httpx.ConnectError("offline"))),
        ("a server error", FakeTogether(status=500)),
        ("too many requests", FakeTogether(status=429)),
        ("a reply that is not JSON", FakeTogether("the student is right")),
        ("a reply cut off", FakeTogether(finish="length")),
        ("a label outside the set", FakeTogether({"label": "excellent", "misconception": None})),
        ("no label at all", FakeTogether({"misconception": None})),
        ("a reply that is a list", FakeTogether([1, 2, 3])),
    ],
)
def test_every_failure_is_partial_never_an_error_and_never_correct(what, fake):
    assert ask(fake) == PARTIAL, what


def test_a_response_with_no_choices_is_partial():
    client = httpx.Client(
        base_url=voice_models.BASE_URL,
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"choices": []})),
    )
    assert grade("x", funnel=FUNNEL, level=0, circuit="", client=client) == PARTIAL


def test_a_misconception_that_is_not_one_of_this_questions_tags_is_dropped():
    fake = FakeTogether({"label": "incorrect", "misconception": "made_up", "ideas_matched": []})
    assert ask(fake) == Grade(label="incorrect", misconception=None)


def test_without_a_key_it_is_partial_and_nothing_is_sent(monkeypatch):
    monkeypatch.delenv("TOGETHER_API_KEY", raising=False)
    assert grade("more current", funnel=FUNNEL, level=0, circuit="") == PARTIAL


def test_the_call_is_given_four_seconds():
    assert grader.TIMEOUT_S == 4.0


def test_a_very_long_answer_is_cut_before_it_is_sent():
    fake = FakeTogether()
    ask(fake, "more current " * 2000)
    assert len(json.dumps(fake.sent["messages"])) < 8000


# ---------- the fixture answers the real model is scored on ----------
# The scoring itself is scripts/grade_fixtures.py: it calls the real model, so it is not
# a test. This only checks the file is complete and matches the lesson.


def test_the_fixture_file_covers_every_question_with_all_four_labels():
    from pathlib import Path

    import yaml

    from tacto.lesson import load_lesson

    lessons = Path(__file__).resolve().parents[2] / "lessons"
    graded = yaml.safe_load((lessons / "circuits-101.grading.yaml").read_text())
    funnels = {
        step.id: step.funnel
        for step in load_lesson(lessons / f"{graded['lesson']}.yaml").steps
        if step.funnel
    }
    fixtures = graded["steps"]
    assert set(fixtures) == set(funnels)
    for step_id, levels in fixtures.items():
        tags = {m.tag for m in funnels[step_id].misconceptions}
        assert [entry["level"] for entry in levels] == list(range(len(funnels[step_id].levels)))
        for entry in levels:
            answers = entry["answers"]
            where = f"{step_id} level {entry['level']}"
            assert len(answers) >= 10, where
            assert {answer[0] for answer in answers} == {
                "correct",
                "partial",
                "incorrect",
                "unclear",
            }, where
            assert all(len(answer) == 2 or answer[2] in tags for answer in answers), where
            assert len({answer[1] for answer in answers}) == len(answers), where
