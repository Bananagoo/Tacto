"""A record of every graded answer in this run of the server.

One line per answer: which question, what was heard, the label and misconception the
grader gave, and how long grading took. Kept in memory, and appended to a file per run
in `server/data/`, which is not committed. It is for the people running the lab: to see
what learners said and where the grader was slow or wrong. The audio is never kept.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


class AnswerLedger:
    """Call it with a record. Never raises: a full disk must not stop a lesson."""

    def __init__(self, folder: Path = DATA_DIR, *, started: str | None = None) -> None:
        self._file = folder / f"answers-{started or time.strftime('%Y-%m-%dT%H-%M-%S')}.jsonl"
        self.records: list[dict] = []
        self._told = False

    def __call__(self, record: dict) -> None:
        record = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), **record}
        self.records.append(record)
        try:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            with self._file.open("a", encoding="utf-8") as file:
                file.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as error:
            if not self._told:
                self._told = True
                print(f"answers: not written to {self._file}: {error}")
