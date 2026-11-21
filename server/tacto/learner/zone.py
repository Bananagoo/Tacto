"""The zone rule: is the lesson too easy, about right, or too hard for this learner right now?

Signals come from the desk only (predictions and idle time), never from the learner's face.
"""

from __future__ import annotations

from ..contract import Zone

# The score at which the zone changes, in either direction.
# TODO(lesson owner): confirm with real learners; 3 is the value in the lesson rules.
ZONE_THRESHOLD = 3


class ZoneTracker:
    """A running score for one session: up for correct predictions, down for struggle."""

    def __init__(self) -> None:
        self._score = 0

    def record_correct(self) -> None:
        """A prediction was right."""
        self._score += 1

    def record_repeated_error(self) -> None:
        """A prediction was wrong about something the learner has got wrong before."""
        self._score -= 1

    def record_idle(self) -> None:
        """A full idle period passed with nothing changing on the mat."""
        self._score -= 1

    @property
    def score(self) -> int:
        return self._score

    @property
    def zone(self) -> Zone:
        if self._score >= ZONE_THRESHOLD:
            return "too_easy"
        if self._score <= -ZONE_THRESHOLD:
            return "stuck"
        return "productive"
