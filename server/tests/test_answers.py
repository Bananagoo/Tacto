"""The answer ledger: one line per graded answer, in memory and in a file."""

import json

from tacto.answers import AnswerLedger


def test_each_record_is_kept_and_appended_as_one_json_line(tmp_path):
    ledger = AnswerLedger(tmp_path, started="2026-11-22T10-00-00")
    ledger({"step": "series", "level": 0, "label": "partial", "transcript": "two bulbs"})
    ledger({"step": "series", "level": 1, "label": "correct", "transcript": "harder"})
    assert [record["label"] for record in ledger.records] == ["partial", "correct"]
    (file,) = tmp_path.iterdir()
    assert file.name == "answers-2026-11-22T10-00-00.jsonl"
    lines = [json.loads(line) for line in file.read_text().splitlines()]
    assert [line["transcript"] for line in lines] == ["two bulbs", "harder"]
    assert all("at" in line for line in lines)  # when it was answered


def test_no_file_is_made_until_there_is_an_answer(tmp_path):
    AnswerLedger(tmp_path / "data")
    assert not (tmp_path / "data").exists()


def test_a_folder_that_cannot_be_written_keeps_the_records_in_memory(tmp_path):
    blocked = tmp_path / "file-not-folder"
    blocked.write_text("x")
    ledger = AnswerLedger(blocked)
    ledger({"step": "series", "label": "correct"})
    assert len(ledger.records) == 1
