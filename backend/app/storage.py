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
