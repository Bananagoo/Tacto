"""Send ten spoken answers through the real transcriber and grader, and time them.

Each answer is synthesised in a voice that is not the lab's, posted to the same endpoint
the browser's microphone uses, transcribed and graded by Together, and the clock stops
when the lab's next line is in the state: from the end of speech to the start of the reply.

    uv run python ../scripts/speak_answers.py            # from server/

The mat is a stand-in (a solved circuit held in memory), so no camera is needed. It needs
TOGETHER_API_KEY in the repo's .env and the network. This checks everything after the
microphone; the microphone and the voice detector in the browser need a person.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.testclient import TestClient

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "server"))

from tacto import grader, listen, voice_models  # noqa: E402
from tacto.contract import Grid, SetMode, SetVoltage  # noqa: E402
from tacto.lab import Lab, MatView  # noqa: E402
from tacto.lesson import LessonRunner, load_lesson  # noqa: E402
from tacto_mock.scenario import BULB_A, loop  # noqa: E402

LESSON = load_lesson(REPO / "lessons" / "circuits-101.yaml")
SPEAKER = "am_adam"  # not the lab's voice
# What a learner might say to "Why did the pulse get faster when you raised the voltage?",
# and the label a teacher would give it.
ANSWERS = [
    ("Because more voltage pushes more current through the bulb.", "correct"),
    ("The battery is pushing harder, so more electricity flows.", "correct"),
    ("More push, so more flow.", "correct"),
    ("Higher voltage means more current, and the pulse is the current.", "correct"),
    ("Because there's more voltage.", "partial"),
    ("The bulb got brighter.", "partial"),
    ("Um, I don't know.", "partial"),
    ("The pulse is the voltage, so it went up.", "incorrect"),
    ("Less current is flowing, so it speeds up.", "incorrect"),
    ("Can you repeat that?", "unclear"),
]


class Mat:
    """One bulb lit, a finger on it."""

    def __init__(self, closed: bool) -> None:
        self.closed = closed
        self.finger: tuple[float, float] | None = None

    def view(self) -> MatView:
        return MatView(tuple(loop(closed=self.closed)), self.finger)


class Clock:
    """Runs fast until the reflection is reached, then keeps real time."""

    def __init__(self) -> None:
        self.offset = 0.0

    def __call__(self) -> float:
        return time.monotonic() + self.offset


def at_the_first_reflection(records: list) -> Lab:
    clock, mat = Clock(), Mat(closed=False)
    lab = Lab(
        Grid(cols=9, rows=6),
        mat,
        source_name="replay",
        lesson=LessonRunner(LESSON, now=clock, adaptive=True),
        grader=grader.grade,
        ledger=records.append,
        now=clock,
    )
    lab.handle(SetMode(mode="lab"))

    def hold(seconds: float) -> None:
        lab.state()
        clock.offset += seconds
        lab.state()

    hold(0.6)  # open switch
    clock.offset += 6.1
    mat.closed = True
    hold(0.6)  # closed switch
    clock.offset += 6.1
    bulb = next(p for p in mat.view().placed if p.id == BULB_A)
    mat.finger = ((bulb.a[0] + bulb.b[0]) / 16, (bulb.a[1] + bulb.b[1]) / 10)
    hold(0.6)  # finger on the bulb
    clock.offset += 6.1
    lab.handle(SetVoltage(volts=6))
    hold(0.6)  # 6 V
    assert lab.state().lesson.reflection_status == "asking", lab.state().lesson
    return lab


def main() -> None:
    load_dotenv(REPO / ".env")
    together = grader.together_client()
    if together is None:
        raise SystemExit("speak_answers: TOGETHER_API_KEY is not set in .env")
    print(
        f"speaking {len(ANSWERS)} answers as {SPEAKER}; the lab's own voice is "
        f"{voice_models.TTS_VOICE}"
    )
    right = 0
    totals: list[float] = []
    for said, expected in ANSWERS:
        speech = together.post(
            "/audio/speech",
            json={
                "model": voice_models.TTS_MODEL,
                "input": said,
                "voice": SPEAKER,
                "response_format": "wav",
            },
            timeout=30,
        )
        speech.raise_for_status()
        records: list[dict] = []
        lab = at_the_first_reflection(records)
        app = FastAPI()
        app.include_router(listen.answer_router(lab, lambda wav: listen.transcribe(wav, together)))
        before = lab.state().lesson.reflection_line_id
        started = time.perf_counter()
        reply = TestClient(app).post(
            "/voice/answer",
            params={"step_id": "raise_voltage"},
            content=speech.content,
            headers={"content-type": "audio/wav"},
        )
        reply.raise_for_status()
        while lab.state().lesson.reflection_line_id == before:
            if time.perf_counter() - started > 15:
                raise SystemExit(f"speak_answers: no reply to {said!r} within 15 s")
            time.sleep(0.01)
        total = time.perf_counter() - started
        totals.append(total)
        record = records[0] if records else {"label": "?", "grade_ms": 0}
        ok = record["label"] == expected
        right += ok
        lesson = lab.state().lesson
        print(
            f"{'ok  ' if ok else 'MISS'} {total:4.2f} s (transcribe "
            f"{reply.json()['transcribe_ms'] / 1000:.2f}, grade {record['grade_ms'] / 1000:.2f})  "
            f"want {expected:<9} got {record['label']:<9} heard {reply.json()['text']!r} "
            f"-> {lesson.reflection_status}"
        )
    together.close()
    totals.sort()
    print(
        f"\n{len(totals)} of {len(ANSWERS)} answers transcribed and graded; {right} labels as "
        f"expected.\nend of speech to the lab's next line: "
        f"median {totals[len(totals) // 2]:.2f} s, slowest {totals[-1]:.2f} s"
    )


if __name__ == "__main__":
    main()
