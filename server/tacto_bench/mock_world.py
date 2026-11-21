"""A fake world so the web app can be built before the camera works.

One battery, one bulb, four wires. The scroll wheel changes the voltage and a
pretend fingertip circles the loop. It implements tacto.world.World, the same
interface the real session will, so the web app cannot tell them apart.
"""

from __future__ import annotations

import math
import time

from tacto.contract import Answer, Circuit, ClientMessage, Part, Probe, State, Tutor, Wheel, Wire

BULB_OHMS = 10.0
MAX_VOLTS = 9.0
VOLTS_PER_STEP = 0.5
FULL_BRIGHT_AMPS = 0.9


class MockWorld:
    def __init__(self) -> None:
        self.volts = 3.0
        self.phase = "predict"
        self.score = 0

    def handle(self, msg: ClientMessage) -> None:
        if isinstance(msg, Wheel):
            self.volts = min(MAX_VOLTS, max(0.0, self.volts + msg.steps * VOLTS_PER_STEP))
        elif isinstance(msg, Answer):
            self.score += 1 if msg.choice == "brighter" else -1
            self.phase = "test"

    def state(self) -> State:
        now = time.time()
        amps = self.volts / BULB_OHMS
        angle = now * 0.8
        return State(
            t=now,
            source="mock",
            circuit=Circuit(
                status="closed" if self.volts > 0 else "open",
                topology="single" if self.volts > 0 else "none",
                source_voltage=self.volts,
                total_current=amps,
                parts=[
                    Part(
                        id="battery1",
                        kind="battery",
                        a=(1, 3),
                        b=(1, 1),
                        voltage=self.volts,
                        current=amps,
                    ),
                    Part(
                        id="bulb1",
                        kind="bulb",
                        a=(4, 1),
                        b=(4, 3),
                        voltage=self.volts,
                        current=amps,
                        brightness=min(1.0, amps / FULL_BRIGHT_AMPS),
                    ),
                ],
                wires=[
                    Wire(a=(1, 1), b=(4, 1), current=amps),
                    Wire(a=(4, 3), b=(1, 3), current=amps),
                ],
            ),
            probe=Probe(
                present=True,
                x=0.5 + 0.3 * math.cos(angle),
                y=0.5 + 0.3 * math.sin(angle),
                on="wire:1,1-4,1",
                current=amps,
                pulse_hz=round(1.0 + 8.0 * amps, 2) if amps > 0 else 0.0,
            ),
            tutor=Tutor(
                lesson_id="mock",
                challenge_id="turn_it_up",
                step_index=0,
                step_count=1,
                phase=self.phase,
                prompt="If you turn the voltage up, what will the bulb do?",
                choices=["brighter", "dimmer", "same"] if self.phase == "predict" else [],
                zone="productive",
                score=self.score,
            ),
            learner={"closed_loop": "solid", "current": "shaky", "voltage": "shaky"},
        )
