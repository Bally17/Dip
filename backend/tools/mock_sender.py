"""Pošle falošné dáta zo simulátora na /ws/ingest (náhrada kolegovho simulátora)."""
import asyncio
import json
import math
import random
import sys
import time

from websockets.asyncio.client import connect


def pose(t: float, shift: float = 0.0) -> dict:
    return {
        "pos": {"x": math.sin(t) * 0.1 + shift, "y": 1.7, "z": math.cos(t) * 0.1},
        "rot": {"x": 0.0, "y": math.sin(t / 2) * 0.2, "z": 0.0, "w": 1.0},
    }


async def main(url: str, seconds: int, hz: int, participant: str) -> None:
    session = f"{participant}-{int(time.time())}"
    start = time.time()
    async with connect(url) as ws:
        for i in range(seconds * hz):
            now = time.time()
            phase = min(int((now - start) // max(seconds / 3, 1)), 2)
            base = {"participant": participant, "session": session, "t": int(now * 1000), "phase": phase}
            await ws.send(json.dumps({
                **base, "type": "sample",
                "heart_rate": 70 + phase * 15 + random.gauss(0, 3),
                "head": pose(now), "left": pose(now, -0.3), "right": pose(now, 0.3),
            }))
            await ws.recv()
            if i % hz == 0:
                await ws.send(json.dumps({**base, "type": "event", "kind": "reaction_time",
                                          "value_ms": random.gauss(400 + phase * 80, 40)}))
                await ws.recv()
            await asyncio.sleep(1 / hz)
        await ws.send(json.dumps({**base, "type": "questionnaire", "score": 2 + phase * 3}))
        await ws.recv()


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8000/ws/ingest"
    seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    asyncio.run(main(url, seconds=seconds, hz=10, participant="P01"))
