"""Count Logi Hands Tracker messages per second and print the index fingertip.

Run from server/ so uv uses the project environment:
    uv run python ../scripts/hands_probe.py              # 10 s
    uv run python ../scripts/hands_probe.py --seconds 20

The tracker app must be running. It publishes on ws://127.0.0.1:8765, one
hand_telemetry message per processed camera frame (about 30 a second).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time

import websockets

PRINT_EVERY_S = 1.0


async def run(url: str, seconds: float) -> None:
    messages = 0
    with_hand = 0
    arrivals: list[float] = []
    image = None
    last_print = 0.0

    async with websockets.connect(url) as socket:
        start = time.perf_counter()
        while (now := time.perf_counter()) - start < seconds:
            try:
                raw = await asyncio.wait_for(socket.recv(), timeout=2.0)
            except TimeoutError:
                print("no message for 2 s")
                continue
            message = json.loads(raw)
            if message.get("type") != "hand_telemetry":
                continue
            now = time.perf_counter()
            messages += 1
            arrivals.append(now)
            image = message.get("image")
            hands = message.get("hands", [])
            if hands:
                with_hand += 1
            if now - last_print >= PRINT_EVERY_S:
                last_print = now
                if hands:
                    tips = ", ".join(
                        f"{hand['handedness']} index_tip=({hand['index_tip']['x']:.3f}, "
                        f"{hand['index_tip']['y']:.3f})"
                        for hand in hands
                    )
                else:
                    tips = "no hand"
                print(f"t={now - start:5.1f}s  {tips}")
        elapsed = time.perf_counter() - start

    gaps_ms = [(b - a) * 1000 for a, b in zip(arrivals, arrivals[1:], strict=False)]
    print(f"image={image}")
    print(f"messages={messages} in {elapsed:.1f}s -> {messages / elapsed:.1f} msg/s")
    print(f"messages_with_hand={with_hand}")
    if gaps_ms:
        print(
            f"gap_ms median={statistics.median(gaps_ms):.1f} "
            f"p95={sorted(gaps_ms)[int(len(gaps_ms) * 0.95)]:.1f} max={max(gaps_ms):.1f}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="ws://127.0.0.1:8765")
    parser.add_argument("--seconds", type=float, default=10.0)
    args = parser.parse_args()
    try:
        asyncio.run(run(args.url, args.seconds))
    except OSError as error:
        raise SystemExit(f"could not connect to {args.url}: {error}") from error


if __name__ == "__main__":
    main()
