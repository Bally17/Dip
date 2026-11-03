import os
from pathlib import Path

from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from .schemas import Event, Questionnaire, Sample

_pool: AsyncConnectionPool | None = None


def _dsn() -> str:
    return (
        f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ.get('POSTGRES_HOST', 'db')}:5432/{os.environ['POSTGRES_DB']}"
    )


async def open_pool() -> None:
    global _pool
    _pool = AsyncConnectionPool(_dsn(), open=False)
    await _pool.open(wait=True)
    schema = (Path(__file__).parent / "schema.sql").read_text()
    async with _pool.connection() as conn:
        await conn.execute(schema)


async def close_pool() -> None:
    if _pool:
        await _pool.close()


async def recent_samples(session: str, seconds: float) -> list[tuple[float, float | None, dict]]:
    """Posledné vzorky relácie ako (čas v s, tep, rotácia hlavy), od najstaršej."""
    async with _pool.connection() as conn:
        cur = await conn.execute(
            "SELECT extract(epoch FROM ts), heart_rate, head->'rot' FROM samples"
            " WHERE session = %s AND ts > (SELECT max(ts) FROM samples WHERE session = %s)"
            " - make_interval(secs => %s) ORDER BY ts",
            (session, session, seconds),
        )
        return [(float(t), hr, rot) for t, hr, rot in await cur.fetchall()]


def _pose(p):
    return Jsonb(p.model_dump()) if p else None


async def save(msg: Sample | Event | Questionnaire) -> None:
    async with _pool.connection() as conn:
        await conn.execute(
            "INSERT INTO participants (code) VALUES (%s) ON CONFLICT DO NOTHING",
            (msg.participant,),
        )
        await conn.execute(
            "INSERT INTO sessions (id, participant) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (msg.session, msg.participant),
        )
        ts = msg.t / 1000.0
        if isinstance(msg, Sample):
            await conn.execute(
                "INSERT INTO samples (ts, session, phase, heart_rate, head, left_hand, right_hand)"
                " VALUES (to_timestamp(%s), %s, %s, %s, %s, %s, %s)",
                (ts, msg.session, msg.phase, msg.heart_rate, _pose(msg.head), _pose(msg.left), _pose(msg.right)),
            )
        elif isinstance(msg, Event):
            await conn.execute(
                "INSERT INTO events (ts, session, phase, kind, value_ms)"
                " VALUES (to_timestamp(%s), %s, %s, %s, %s)",
                (ts, msg.session, msg.phase, msg.kind, msg.value_ms),
            )
        else:
            await conn.execute(
                "INSERT INTO questionnaires (ts, session, phase, score)"
                " VALUES (to_timestamp(%s), %s, %s, %s)",
                (ts, msg.session, msg.phase, msg.score),
            )
