"""Turn what the learner said or clicked into one of a prediction's choices.

Keywords only: this runs on every answer and must work with the Wi-Fi off.
"""

from __future__ import annotations

import re

_APOSTROPHES = re.compile(r"['’]")
_NOT_A_WORD = re.compile(r"[\W_]+")


def match_choice(text: str, choices: dict[str, list[str]]) -> str | None:
    """The choice the text means, or None when it means none of them or more than one.

    `choices` maps each choice name to the words that count as that choice when spoken.
    """
    said = _normalise(text)
    if not said:
        return None
    # A button sends the choice name itself, which must win even when that name is
    # also a keyword of another choice.
    for name in choices:
        if _normalise(name) == said:
            return name
    matches = [
        name
        for name, keywords in choices.items()
        if any(_contains_phrase(said, _normalise(keyword)) for keyword in keywords)
    ]
    # "Dimmer, or maybe brighter" is not a prediction: guessing one would score the
    # learner on something they did not commit to.
    return matches[0] if len(matches) == 1 else None


def _normalise(text: str) -> str:
    """Lower-case words separated by single spaces, with punctuation gone."""
    # Apostrophes are dropped, not spaced, so "don't" stays one word instead of
    # leaving a stray "t" that could match a keyword.
    without_apostrophes = _APOSTROPHES.sub("", text.lower())
    return _NOT_A_WORD.sub(" ", without_apostrophes).strip()


def _contains_phrase(said: str, phrase: str) -> bool:
    """Whether `phrase` appears in `said` as whole words, so "no" is not found in "know"."""
    return bool(phrase) and f" {phrase} " in f" {said} "
