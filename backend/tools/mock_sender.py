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
import urllib.request

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


def pair(api: str, code: str) -> str:
    """Vymení párovací kód z webu za token headsetu, tak ako to spraví simulátor."""
    request = urllib.request.Request(
        f"{api}/devices/pair", data=json.dumps({"code": code}).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)["token"]


async def run_session(url: str, seconds: int, hz: int, participant: str, token: str | None = None) -> None:
    session = f"{participant}-{int(time.time())}"
    start = time.time()
    task1_sent = False
    async with connect(url) as ws:
        if token:
            # Headset člena sa preukáže prvou správou, token nejde v adrese.
            await ws.send(json.dumps({"type": "auth", "token": token}))
            if not json.loads(await ws.recv()).get("ok"):
                raise SystemExit("Server token odmietol")
        for i in range(seconds * hz):
            now = time.time()
            phase = min(int((now - start) // max(seconds / 3, 1)), 2)
            base = {"participant": participant, "session": session, "t": int(now * 1000), "phase": phase}
            if phase == 2 and not task1_sent:
                # Úloha 1 sa končí s druhou fázou, jej čas patrí ešte k nej.
                task1_sent = True
                await ws.send(json.dumps({**base, "phase": 1, "type": "event", "kind": "task1_time",
                                          "value_ms": random.gauss(seconds / 3 * 700, 400)}))
                await ws.recv()
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
        await ws.send(json.dumps({**base, "type": "event", "kind": "task2_time",
                                  "value_ms": random.gauss(seconds / 3 * 800, 400)}))
        await ws.recv()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://localhost:8000/ws/ingest")
    ap.add_argument("--seconds", type=int, default=60, help="dĺžka jednej relácie")
    ap.add_argument("--hz", type=int, default=10)
    ap.add_argument("--participant", default="P01")
    ap.add_argument("--loop", action="store_true", help="po skončení začať novú reláciu")
    ap.add_argument("--api", default="http://localhost:8000", help="adresa REST API pre párovanie")
    ap.add_argument("--pair", metavar="KÓD", help="párovací kód z webu; posiela potom ako headset člena")
    ap.add_argument("--token", help="token headsetu z predošlého párovania")
    args = ap.parse_args()
    token = args.token or (pair(args.api, args.pair) if args.pair else None)
    if args.pair:
        print(f"Spárované. Token na ďalšie spustenie: --token {token}")
    url = args.url if token else f"{args.url}?key={os.environ.get('INGEST_KEY', '')}"
    while True:
        await run_session(url, args.seconds, args.hz, args.participant, token)
        if not args.loop:
            break


if __name__ == "__main__":
    asyncio.run(main())
