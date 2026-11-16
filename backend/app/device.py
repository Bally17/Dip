"""Stav prenosu z prístroja, vypočítaný na serveri z času vzorky a času jej prijatia."""
from statistics import median

CONNECTED_WITHIN_S = 5.0
MIN_GAP_S = 0.5


def stats(rows: list[dict], now: float) -> dict:
    """`rows` sú vzorky od najstaršej: t (čas vzorky v s) a received (čas prijatia v s alebo None)."""
    steps = [b["t"] - a["t"] for a, b in zip(rows, rows[1:]) if b["t"] > a["t"]]
    step = median(steps) if steps else None
    # Výpadok je medzera výrazne dlhšia než bežný rozostup vzoriek.
    gaps = [s for s in steps if s > max(MIN_GAP_S, 5 * step)] if steps else []
    delays = [(r["received"] - r["t"]) * 1000 for r in rows if r["received"] is not None]
    last = max((r["received"] for r in rows if r["received"] is not None), default=None)
    age = None if last is None else max(0.0, now - last)
    return {
        "samples": len(rows),
        "rate_hz": round(1 / step, 1) if step else None,
        "gaps": len(gaps),
        "longest_gap_s": max(gaps) if gaps else None,
        "delay_ms": median(delays) if delays else None,
        "delay_max_ms": max(delays) if delays else None,
        "last_message_age_s": age,
        "connected": age is not None and age < CONNECTED_WITHIN_S,
    }
