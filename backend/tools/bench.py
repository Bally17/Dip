"""Meranie príjmu: latencia potvrdení, straty a duplikáty, čítanie cez REST pri záťaži.

Každá relácia posiela vzorky v pevnom rytme a nečaká na potvrdenie predošlej správy.
Po skončení úrovne sa z exportu overí, či sú v databáze práve tie vzorky, ktoré odišli.
Spúšťa sa v kontajneri z obrazu API, aby mal rovnaké kľúče ako server:

    docker compose run --rm api python -m tools.bench --sessions 1 10 50 --out /dev/stdout
"""
import argparse
import asyncio
import collections
import json
import math
import os
import statistics
import time
import urllib.error
import urllib.request

from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake

ACK_TIMEOUT_S = 30


def summarize(seconds: list[float]) -> dict:
    """Počet, priemer a percentily v milisekundách."""
    if not seconds:
        return {"n": 0}
    ms = sorted(s * 1000 for s in seconds)

    def pct(p: float) -> float:
        k = (len(ms) - 1) * p / 100
        lo, hi = math.floor(k), math.ceil(k)
        return ms[lo] + (ms[hi] - ms[lo]) * (k - lo)

    return {
        "n": len(ms),
        "mean_ms": statistics.fmean(ms),
        "p50_ms": pct(50),
        "p95_ms": pct(95),
        "p99_ms": pct(99),
        "max_ms": ms[-1],
    }


def integrity(sent_ms: list[int], stored_s: list[float]) -> dict:
    """Porovná odoslané časové značky (ms) s uloženými (s)."""
    stored = collections.Counter(round(t * 1000) for t in stored_s)
    sent = set(sent_ms)
    return {
        "sent": len(sent_ms),
        "stored": sum(stored.values()),
        "lost": len(sent - stored.keys()),
        "duplicated": sum(n - 1 for n in stored.values()),
        "foreign": sum(n for t, n in stored.items() if t not in sent),
    }


def sample_message(participant: str, session: str, t_ms: int, phase: int) -> str:
    s = t_ms / 1000
    rot = {"x": math.sin(s) * 0.1, "y": math.cos(s) * 0.1, "z": 0.0, "w": 0.99}
    pose = {"pos": {"x": 0.0, "y": 1.7, "z": 0.0}, "rot": rot}
    return json.dumps({
        "type": "sample", "participant": participant, "session": session, "t": t_ms, "phase": phase,
        "heart_rate": 80 + math.sin(s / 4) * 5, "head": pose, "left": pose, "right": pose,
    })


class Rest:
    def __init__(self, base: str, user: str, password: str):
        self.base = base
        self.token = self._call("POST", "/auth/login", {"username": user, "password": password})["access_token"]

    def _call(self, method: str, path: str, body: dict | None = None):
        req = urllib.request.Request(
            self.base + path, method=method,
            data=json.dumps(body).encode() if body else None,
            headers={"Content-Type": "application/json",
                     **({"Authorization": f"Bearer {self.token}"} if hasattr(self, "token") else {})},
        )
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read())

    async def get(self, path: str):
        return await asyncio.to_thread(self._call, "GET", path)

    async def delete(self, path: str):
        return await asyncio.to_thread(self._call, "DELETE", path)


async def run_session(url: str, participant: str, session: str, hz: int, seconds: int) -> dict:
    """Pošle seconds*hz vzoriek podľa rozvrhu. Vráti odoslané značky, RTT potvrdení a chyby."""
    n = seconds * hz
    sent_at: collections.deque[float] = collections.deque()
    rtts, sent_ms, errors, lag, dropped = [], [], 0, 0.0, False
    start = time.perf_counter()
    try:
        async with connect(url, max_queue=None) as ws:
            async def receive():
                nonlocal errors
                for _ in range(n):
                    ack = json.loads(await ws.recv())
                    rtts.append(time.perf_counter() - sent_at.popleft())
                    errors += not ack.get("ok")

            receiver = asyncio.create_task(receive())
            t0_ms, start = int(time.time() * 1000), time.perf_counter()
            try:
                for i in range(n):
                    delay = start + i / hz - time.perf_counter()
                    if delay > 0:
                        await asyncio.sleep(delay)
                    lag = max(lag, -delay)
                    t_ms = t0_ms + round(i * 1000 / hz)
                    sent_at.append(time.perf_counter())
                    await ws.send(sample_message(participant, session, t_ms, min(i * 3 // n, 2)))
                    sent_ms.append(t_ms)
                await asyncio.wait_for(receiver, ACK_TIMEOUT_S)
            except asyncio.TimeoutError:
                pass
            finally:
                receiver.cancel()
    except (ConnectionClosed, InvalidHandshake, OSError):
        dropped = True  # server spojenie zavrel alebo neprijal, pri preťažení sa to stáva
    duration = time.perf_counter() - start
    return {"sent_ms": sent_ms, "rtts": rtts, "errors": errors, "unacked": n - len(rtts),
            "max_send_lag_s": lag, "duration_s": duration, "dropped": dropped}


async def read_like_frontend(rest: Rest, session: str, stop: asyncio.Event) -> dict:
    """Raz za sekundu si vypýta nové vzorky a odhad, ako to robí živý pohľad vo frontende."""
    samples, risk, since = [], [], time.time()
    while not stop.is_set():
        t = time.perf_counter()
        try:
            rows = await rest.get(f"/sessions/{session}/samples?since={since}")
            samples.append(time.perf_counter() - t)
        except urllib.error.HTTPError:
            rows = []
        if rows:
            since = rows[-1]["t"]
        t = time.perf_counter()
        try:
            await rest.get(f"/sessions/{session}/risk")
            risk.append(time.perf_counter() - t)
        except urllib.error.HTTPError:
            pass  # prvých pár sekúnd relácia nemá dosť dát na odhad
        await asyncio.sleep(1)
    return {"samples": summarize(samples), "risk": summarize(risk)}


async def run_level(args, rest: Rest, sessions: int, pseudonymize) -> dict:
    run = f"{int(time.time())}-{sessions}"
    names = [(f"BENCH-{run}-{k}", f"s{k}") for k in range(sessions)]
    ids = [pseudonymize(f"{p}/{s}", "s") for p, s in names]
    url = f"{args.ws}?key={os.environ['INGEST_KEY']}"

    stop = asyncio.Event()
    senders = [asyncio.create_task(run_session(url, p, s, args.hz, args.seconds)) for p, s in names]
    await asyncio.sleep(1)
    reader = asyncio.create_task(read_like_frontend(rest, ids[0], stop))
    results = await asyncio.gather(*senders)
    stop.set()
    reads = await reader

    totals = collections.Counter()
    for sid, r in zip(ids, results):
        try:
            stored = [row["t"] for row in (await rest.get(f"/sessions/{sid}/export?format=json"))["samples"]]
        except urllib.error.HTTPError as e:
            if e.code != 404:
                raise
            stored = []  # relácia sa nestihla ani založiť
        # Stratená je len potvrdená vzorka. Potvrdenia chodia v poradí odoslania.
        check = integrity(r["sent_ms"][:len(r["rtts"])], stored)
        check["foreign"] = integrity(r["sent_ms"], stored)["foreign"]
        totals.update(check)
    if not args.keep:
        for p, _ in names:
            try:
                await rest.delete(f"/participants/{pseudonymize(p, 'p')}")
            except urllib.error.HTTPError:
                pass

    acked = sum(len(r["rtts"]) for r in results)
    return {
        "sessions": sessions, "hz": args.hz, "seconds": args.seconds,
        "target_msg_s": sessions * args.hz,
        "achieved_msg_s": acked / max(r["duration_s"] for r in results),
        "ack": summarize([x for r in results for x in r["rtts"]]),
        "errors": sum(r["errors"] for r in results),
        "unacked": sum(r["unacked"] for r in results),
        "dropped_connections": sum(r["dropped"] for r in results),
        "max_send_lag_s": max(r["max_send_lag_s"] for r in results),
        "integrity": dict(totals),
        "rest": reads,
    }


async def main() -> None:
    from app.security import pseudonymize

    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://api:8000")
    ap.add_argument("--ws", default="ws://api:8000/ws/ingest")
    ap.add_argument("--sessions", type=int, nargs="+", default=[1], help="úrovne záťaže: počet súbežných relácií")
    ap.add_argument("--hz", type=int, default=25)
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--keep", action="store_true", help="nemazať testovacie dáta po meraní")
    ap.add_argument("--out", help="súbor na výsledky v JSON")
    args = ap.parse_args()

    rest = Rest(args.api, os.environ["ADMIN_USER"], os.environ["ADMIN_PASSWORD"])
    levels = []
    for sessions in args.sessions:
        level = await run_level(args, rest, sessions, pseudonymize)
        levels.append(level)
        ack = level["ack"]
        print(f"{sessions:>3} relácií  {level['achieved_msg_s']:7.1f}/{level['target_msg_s']} správ/s  "
              f"p50 {ack.get('p50_ms', 0):7.1f} ms  p95 {ack.get('p95_ms', 0):7.1f} ms  "
              f"p99 {ack.get('p99_ms', 0):7.1f} ms  chyby {level['errors']}  "
              f"zavreté {level['dropped_connections']}  stratené {level['integrity']['lost']}  duplikáty {level['integrity']['duplicated']}", flush=True)
        if args.out:
            with open(args.out, "w") as f:
                json.dump(levels, f, indent=2)
        await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
