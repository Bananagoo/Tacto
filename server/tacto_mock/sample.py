"""Write the scripted run to `contract/sample-states.jsonl`. Run with `make sample`."""

from __future__ import annotations

from pathlib import Path

from tacto.contract_export import CONTRACT_DIR

from .scenario import states

SAMPLE_PATH: Path = CONTRACT_DIR / "sample-states.jsonl"


def sample_text() -> str:
    return "".join(state.model_dump_json() + "\n" for state in states())


def main() -> None:
    text = sample_text()
    SAMPLE_PATH.write_text(text)
    print(f"sample: wrote {text.count(chr(10))} states to {SAMPLE_PATH}")


if __name__ == "__main__":
    main()
