"""Grade one spoken answer into a fixed label. The model grades; it decides nothing.

In: what the learner said, the question they were asked, what a right answer sounds
like, the wrong ideas worth naming, and a line about the circuit in front of them.
Out: one of four labels, at most one misconception tag from that question's list, and
the ideas that matched. What happens next is `funnel.py`'s business, not the model's.

Any failure (no key, no network, a slow or malformed reply) comes back as "partial",
which moves the learner one question down the funnel: when the grader cannot be
trusted, the learner gets more help, never less (docs/voice-reflections-plan.md).
"""

from __future__ import annotations

import json
import os
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from tacto import voice_models
from tacto.lesson import Funnel

Label = Literal["correct", "partial", "incorrect", "unclear"]
LABELS: tuple[Label, ...] = ("correct", "partial", "incorrect", "unclear")

# The whole call, connecting included. Past this the answer counts as partial.
TIMEOUT_S = 4.0
MAX_REPLY_TOKENS = 120
# A spoken answer is a sentence or two. Anything far longer is a stuck microphone.
MAX_TRANSCRIPT_CHARS = 600

_SYSTEM = """\
You grade a student's spoken answer to one question in a hands-on electric circuits lab.
The student is a beginner, about 12 years old. Their answer was transcribed by a speech
recogniser: it has no punctuation, and a word may be misheard.

Grade the idea, not the vocabulary. Everyday words count: "more push so more flow" is a
correct way to say that more voltage drives more current. Grade only against the question
asked: a short answer that settles that question is correct, even one word.

Labels:
- correct: the answer gives the idea the question is after, in any words.
- partial: on topic and not wrong, but it does not get there: it only repeats what was
  seen ("the bulb got brighter", "because there are two bulbs"), gives half the idea, is
  too vague to tell, or says they do not know.
- incorrect: the answer says something that is physically wrong, shows one of the listed
  misconceptions that contradicts the target idea, or picks the wrong option.
- unclear: not an answer to the question at all: unintelligible, off topic, a bare "yes"
  or "no" to an either-or question, a question back, or a request to repeat.

When in doubt between correct and anything else, do not choose correct.
"misconception" is the tag of the one listed misconception the answer shows, or null.
"ideas_matched" lists, in a few words each, the parts of the target idea the answer got.

Reply only in JSON matching this schema, with nothing before or after it:
{schema}"""

_USER = """\
Question asked: {question}
Target idea: {target}
Answers that are correct for this question:
{examples}
Misconceptions to tag:
{misconceptions}
The circuit in front of the student: {circuit}

Student's answer: {transcript}"""


class Grade(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: Label
    misconception: str | None = None
    ideas_matched: list[str] = Field(default_factory=list)


_PARTIAL = Grade(label="partial")
_told: set[str] = set()


def _tell_once(message: str) -> None:
    if message not in _told:
        _told.add(message)
        print(f"grader: {message}")


def schema_for(funnel: Funnel) -> dict:
    """The exact shape the model must reply in: this question's tags and no others."""
    tags = [misconception.tag for misconception in funnel.misconceptions]
    return {
        "type": "object",
        "properties": {
            "label": {"type": "string", "enum": list(LABELS)},
            "misconception": {"type": ["string", "null"], "enum": [*tags, None]},
            "ideas_matched": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        },
        "required": ["label", "misconception", "ideas_matched"],
        "additionalProperties": False,
    }


def _request(transcript: str, funnel: Funnel, level: int, circuit: str) -> dict:
    schema = schema_for(funnel)
    asked = funnel.levels[level]
    misconceptions = (
        "\n".join(f"- {m.tag}: {m.description}" for m in funnel.misconceptions) or "- (none)"
    )
    return {
        "model": voice_models.GRADER_MODEL,
        "temperature": 0,
        "max_tokens": MAX_REPLY_TOKENS,
        "reasoning": {"enabled": False},
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "grade", "schema": schema},
        },
        "messages": [
            {"role": "system", "content": _SYSTEM.format(schema=json.dumps(schema))},
            {
                "role": "user",
                "content": _USER.format(
                    question=asked.question,
                    target=funnel.target_idea,
                    examples="\n".join(f"- {example}" for example in asked.correct_examples),
                    misconceptions=misconceptions,
                    circuit=circuit or "(not known)",
                    transcript=transcript,
                ),
            },
        ],
    }


def together_client() -> httpx.Client | None:
    """A client for Together with the server's key, or None when there is no key."""
    key = os.getenv("TOGETHER_API_KEY", "").strip()
    if not key:
        return None
    return httpx.Client(
        base_url=voice_models.BASE_URL,
        headers={"Authorization": f"Bearer {key}", "User-Agent": "tacto/0.1"},
        timeout=TIMEOUT_S,
    )


def grade(
    transcript: str,
    *,
    funnel: Funnel,
    level: int,
    circuit: str,
    client: httpx.Client | None = None,
) -> Grade:
    """Grade what the learner said to the question at `level` of `funnel`. Never raises."""
    transcript = " ".join(transcript.split())[:MAX_TRANSCRIPT_CHARS]
    if not transcript:
        return Grade(label="unclear")  # silence: nothing to send, and nothing to grade
    owned = client is None
    if client is None:
        client = together_client()
        if client is None:
            _tell_once("TOGETHER_API_KEY is not set, so every answer is graded partial")
            return _PARTIAL
    try:
        response = client.post(
            "/chat/completions",
            json=_request(transcript, funnel, level, circuit),
            timeout=TIMEOUT_S,
        )
        response.raise_for_status()
        choice = response.json()["choices"][0]
        if choice.get("finish_reason") == "length":
            return _PARTIAL
        found = Grade.model_validate(json.loads(choice["message"]["content"]))
    except (httpx.HTTPError, ValidationError, ValueError, KeyError, IndexError, TypeError) as error:
        _tell_once(f"an answer could not be graded and counted as partial: {type(error).__name__}")
        return _PARTIAL
    finally:
        if owned:
            client.close()
    tags = {misconception.tag for misconception in funnel.misconceptions}
    if found.misconception not in tags:
        found = found.model_copy(update={"misconception": None})
    return found
