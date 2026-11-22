"""Score the answer grader against the fixture answers, using the real model.

    uv run python ../scripts/grade_fixtures.py            # from server/
    uv run python ../scripts/grade_fixtures.py --step series --show all

It passes when at least 90% of the fixtures get the label a teacher would give, and no
answer marked incorrect is ever graded correct. It needs TOGETHER_API_KEY in the repo's
.env and the network, and costs a fraction of a cent. This is a script and not a test:
the project's tests never call a real provider.

When it fails, change the grader's prompt (server/tacto/grader.py), not the fixtures.
"""

from __future__ import annotations

import argparse
import collections
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yaml
from dotenv import load_dotenv

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "server"))

from tacto.grader import LABELS, grade, together_client  # noqa: E402
from tacto.lesson import load_lesson  # noqa: E402

FIXTURES = REPO / "lessons" / "circuits-101.grading.yaml"
PASS_FRACTION = 0.9
# What the grader is told about the mat for each step, as the lab would say it.
CIRCUIT = {
    "raise_voltage": "One battery at 6 V, one bulb lit, 0.6 A through it. It was 3 V and 0.3 A.",
    "series": "One battery at 6 V, two bulbs lit in series, 0.3 A through each.",
    "parallel": "One battery at 6 V, two bulbs lit in parallel, 0.6 A each, 1.2 A at the battery.",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--step", help="only this step id")
    parser.add_argument("--show", choices=["misses", "all"], default="misses")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--lesson",
        help="grade against this lesson's questions (a file name in lessons/, no .yaml); "
        "by default the one the fixture file names",
    )
    args = parser.parse_args()

    load_dotenv(REPO / ".env")
    client = together_client()
    if client is None:
        raise SystemExit("grade_fixtures: TOGETHER_API_KEY is not set in .env")
    fixtures = yaml.safe_load(FIXTURES.read_text())
    lesson_file = REPO / "lessons" / f"{args.lesson or fixtures['lesson']}.yaml"
    funnels = {step.id: step.funnel for step in load_lesson(lesson_file).steps if step.funnel}
    print(f"grading against {lesson_file.name}")
    cases = []
    for step_id, levels in fixtures["steps"].items():
        if args.step and step_id != args.step:
            continue
        if step_id not in funnels:
            continue  # a question the chosen lesson does not ask
        for entry in levels:
            for answer in entry["answers"]:
                expected, text, *tag = answer
                cases.append((step_id, entry["level"], expected, text, tag[0] if tag else None))

    def run(case):
        step_id, level, _, text, _ = case
        started = time.perf_counter()
        found = grade(
            text, funnel=funnels[step_id], level=level, circuit=CIRCUIT[step_id], client=client
        )
        return found, time.perf_counter() - started

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(run, cases))
    client.close()

    right = dangerous = tags_right = tags_expected = 0
    confusion: dict[tuple[str, str], int] = collections.Counter()
    seconds = sorted(taken for _, taken in results)
    for (step_id, level, expected, text, tag), (found, _) in zip(cases, results, strict=True):
        ok = found.label == expected
        right += ok
        confusion[(expected, found.label)] += 1
        unsafe = expected == "incorrect" and found.label == "correct"
        dangerous += unsafe
        if tag is not None:
            tags_expected += 1
            tags_right += found.misconception == tag
        if args.show == "all" or not ok:
            mark = "ok  " if ok else ("BAD " if unsafe else "miss")
            print(
                f"{mark} {step_id}/{level} want {expected:<9} got {found.label:<9} "
                f"tag {found.misconception or '-':<20} {text!r}"
            )
    total = len(cases)
    print(f"\n{right} of {total} labels right ({right / total:.0%}); need {PASS_FRACTION:.0%}")
    print(f"incorrect answers graded correct: {dangerous} (must be 0)")
    print(f"misconception tags right: {tags_right} of {tags_expected}")
    print(
        f"time per answer: median {seconds[len(seconds) // 2]:.2f} s, slowest {seconds[-1]:.2f} s"
    )
    print("want \\ got  " + "  ".join(f"{label:>9}" for label in LABELS))
    for want in LABELS:
        row = "  ".join(f"{confusion[(want, got)]:>9}" for got in LABELS)
        print(f"{want:>10}  {row}")
    if right / total < PASS_FRACTION or dangerous:
        raise SystemExit("grade_fixtures: FAILED")
    print("grade_fixtures: passed")


if __name__ == "__main__":
    main()
