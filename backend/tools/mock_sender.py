"""Pošle falošné dáta zo simulátora na /ws/ingest (náhrada kolegovho simulátora).

Relácia má tri fázy (úvod, rampa, výška). Tep a pohľad dolu sa v nich postupne stupňujú.
Dáta sú vymyslené, slúžia len na vývoj a ukážku rozhrania.
"""
import argparse
import asyncio
import json
import math
import os
import random
import time

from websockets.asyncio.client import connect


def quat(pitch_deg: float, yaw_deg: float) -> dict:
    """Kvaternión q = qyaw * qpitch (os Y, potom os X)."""
    p, y = math.radians(pitch_deg) / 2, math.radians(yaw_deg) / 2
    return {
        "x": math.cos(y) * math.sin(p),
        "y": math.sin(y) * math.cos(p),
        "z": -math.sin(y) * math.sin(p),
        "w": math.cos(y) * math.cos(p),
    }


def pose(t: float, phase: int, shift: float = 0.0) -> dict:
    look_down = [0, 12, 35][phase] + math.sin(t / 3) * 4
    sway = [10, 18, 30][phase]
    return {
        "pos": {"x": math.sin(t) * 0.05 + shift, "y": 1.7, "z": math.cos(t) * 0.05},
        "rot": quat(look_down, math.sin(t / 2) * sway + random.gauss(0, 1.5 * (phase + 1))),
    }


async def run_session(url: str, seconds: int, hz: int, participant: str) -> None:
    session = f"{participant}-{int(time.time())}"
    start = time.time()
    async with connect(url) as ws:
        for i in range(seconds * hz):
            now = time.time()
            phase = min(int((now - start) // max(seconds / 3, 1)), 2)
            base = {"participant": participant, "session": session, "t": int(now * 1000), "phase": phase}
            await ws.send(json.dumps({
                **base, "type": "sample",
                "heart_rate": 72 + phase * 14 + math.sin(now / 4) * 3 + random.gauss(0, 2),
                "head": pose(now, phase), "left": pose(now, phase, -0.3), "right": pose(now, phase, 0.3),
            }))
            await ws.recv()
            if i % hz == 0 and i:
                await ws.send(json.dumps({**base, "type": "event", "kind": "reaction_time",
                                          "value_ms": random.gauss(400 + phase * 80, 40)}))
                await ws.recv()
            await asyncio.sleep(1 / hz)
        await ws.send(json.dumps({**base, "type": "questionnaire", "score": 2 + phase * 3}))
        await ws.recv()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://localhost:8000/ws/ingest")
    ap.add_argument("--seconds", type=int, default=60, help="dĺžka jednej relácie")
    ap.add_argument("--hz", type=int, default=10)
    ap.add_argument("--participant", default="P01")
    ap.add_argument("--loop", action="store_true", help="po skončení začať novú reláciu")
    args = ap.parse_args()
    url = f"{args.url}?key={os.environ.get('INGEST_KEY', '')}"
    while True:
        await run_session(url, args.seconds, args.hz, args.participant)
        if not args.loop:
            break


if __name__ == "__main__":
    asyncio.run(main())
