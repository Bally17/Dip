import asyncio
import os
from datetime import timedelta
from pathlib import Path

from psycopg.errors import DeadlockDetected
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from .schemas import Event, Sample

_pool: AsyncConnectionPool | None = None


def _dsn() -> str:
    return (
        f"postgresql://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
        f"@{os.environ.get('POSTGRES_HOST', 'db')}:5432/{os.environ['POSTGRES_DB']}"
    )


async def open_pool() -> None:
    global _pool
    _pool = AsyncConnectionPool(_dsn(), open=False, kwargs={"row_factory": dict_row})
    await _pool.open(wait=True)
    schema = (Path(__file__).parent / "schema.sql").read_text()
    async with _pool.connection() as conn:
        # Continuous aggregate nejde vytvoriť v transakcii, preto každý príkaz zvlášť.
        await conn.set_autocommit(True)
        for statement in schema.split("\n\n"):
            if statement.strip():
                await conn.execute(statement)
        await conn.set_autocommit(False)


async def close_pool() -> None:
    if _pool:
        await _pool.close()


async def _fetch(query: str, params: tuple = ()) -> list[dict]:
    async with _pool.connection() as conn:
        cur = await conn.execute(query, params)
        return await cur.fetchall()


def _pose(p):
    return Jsonb(p.model_dump()) if p else None


SAVE_ATTEMPTS = 4


async def save(msg: Sample | Event) -> None:
    """Uloží správu. Dva súčasné príjmy môžu pri vytváraní chunku hypertabuľky skončiť deadlockom, tak sa to opakuje."""
    for attempt in range(1, SAVE_ATTEMPTS + 1):
        try:
            await _save_once(msg)
            return
        except DeadlockDetected:
            if attempt == SAVE_ATTEMPTS:
                raise
            await asyncio.sleep(0.05 * attempt)


async def _save_once(msg: Sample | Event) -> None:
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
                "INSERT INTO samples (ts, session, phase, heart_rate, head, left_hand, right_hand, received_at)"
                " VALUES (to_timestamp(%s), %s, %s, %s, %s, %s, %s, clock_timestamp())",
                (ts, msg.session, msg.phase, msg.heart_rate, _pose(msg.head), _pose(msg.left), _pose(msg.right)),
            )
        else:
            await conn.execute(
                "INSERT INTO events (ts, session, phase, kind, value_ms)"
                " VALUES (to_timestamp(%s), %s, %s, %s, %s)",
                (ts, msg.session, msg.phase, msg.kind, msg.value_ms),
            )


async def get_user(username: str) -> dict | None:
    rows = await _fetch("SELECT username, password_hash, role FROM users WHERE username = %s", (username,))
    return rows[0] if rows else None


async def ensure_user(username: str, password_hash: str, role: str) -> None:
    async with _pool.connection() as conn:
        await conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (username, password_hash, role),
        )


async def create_user(username: str, password_hash: str, role: str) -> bool:
    """Vytvorí účet. Vráti False, ak meno už existuje."""
    async with _pool.connection() as conn:
        cur = await conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (username, password_hash, role),
        )
        return cur.rowcount > 0


async def list_users() -> list[dict]:
    return await _fetch("SELECT username, role FROM users ORDER BY role, username")


async def delete_user(username: str) -> bool:
    async with _pool.connection() as conn:
        cur = await conn.execute("DELETE FROM users WHERE username = %s", (username,))
        return cur.rowcount > 0


async def session_participant(session: str) -> str | None:
    rows = await _fetch("SELECT participant FROM sessions WHERE id = %s", (session,))
    return rows[0]["participant"] if rows else None


async def list_participants() -> list[dict]:
    return await _fetch(
        "SELECT p.code, p.created_at, count(s.id) AS sessions FROM participants p"
        " LEFT JOIN sessions s ON s.participant = p.code GROUP BY p.code ORDER BY p.created_at DESC"
    )


async def list_sessions(participant: str | None = None) -> list[dict]:
    where = "WHERE s.participant = %s" if participant else ""
    params = (participant,) if participant else ()
    return await _fetch(
        "SELECT s.id, s.participant, s.started_at,"
        " (SELECT count(*) FROM samples x WHERE x.session = s.id) AS samples,"
        " (SELECT max(ts) FROM samples x WHERE x.session = s.id) AS last_ts"
        f" FROM sessions s {where} ORDER BY s.started_at DESC LIMIT 200",
        params,
    )


async def session_exists(session: str) -> bool:
    return bool(await _fetch("SELECT 1 FROM sessions WHERE id = %s", (session,)))


async def session_samples(session: str, since: float | None = None, limit: int = 100000) -> list[dict]:
    """Vzorky relácie od najstaršej: t (s), phase, hr a pózy hlavy a oboch ovládačov."""
    since_sql = "AND ts > to_timestamp(%s)" if since is not None else ""
    params = (session, since, limit) if since is not None else (session, limit)
    return await _fetch(
        "SELECT extract(epoch FROM ts)::float8 AS t, phase, heart_rate AS hr, head, left_hand, right_hand"
        f" FROM samples WHERE session = %s {since_sql} ORDER BY ts LIMIT %s",
        params,
    )


async def recent_samples(session: str, seconds: float) -> list[dict]:
    rows = await _fetch(
        "SELECT extract(epoch FROM ts)::float8 AS t, phase, heart_rate AS hr, head FROM samples"
        " WHERE session = %s AND ts > (SELECT max(ts) FROM samples WHERE session = %s)"
        " - make_interval(secs => %s) ORDER BY ts",
        (session, session, seconds),
    )
    return rows


async def arrival_times(session: str, limit: int = 100000) -> list[dict]:
    """Čas vzorky a čas jej prijatia na serveri (s), od najstaršej. Staršie vzorky majú received None."""
    return await _fetch(
        "SELECT extract(epoch FROM ts)::float8 AS t, extract(epoch FROM received_at)::float8 AS received"
        " FROM samples WHERE session = %s ORDER BY ts LIMIT %s",
        (session, limit),
    )


async def session_events(session: str) -> dict:
    events = await _fetch(
        "SELECT extract(epoch FROM ts)::float8 AS t, phase, kind, value_ms FROM events"
        " WHERE session = %s ORDER BY ts", (session,))
    return {"events": events}


async def session_summary(session: str) -> dict:
    rows = await _fetch(
        "SELECT min(bucket) AS start, max(bucket) AS end, avg(hr_avg) AS hr_mean,"
        " max(hr_avg) AS hr_max, min(hr_avg) AS hr_min, sum(n) AS samples"
        " FROM samples_1s WHERE session = %s", (session,))
    return rows[0]


async def delete_participant(code: str) -> bool:
    """Zmaže účastníka a všetky jeho dáta (kaskádovo). Vráti True, ak existoval."""
    span = (await _fetch(
        "SELECT min(x.ts) AS lo, max(x.ts) AS hi FROM samples x"
        " JOIN sessions s ON s.id = x.session WHERE s.participant = %s", (code,)))[0]
    async with _pool.connection() as conn:
        cur = await conn.execute("DELETE FROM participants WHERE code = %s", (code,))
        existed = cur.rowcount > 0
    if existed and span["lo"] is not None:
        # Agregát si pamätá zmazané riadky, kým sa neobnoví. Obnova nejde v transakcii.
        # Obnovuje sa len úsek zmazaných vzoriek, obnova celej histórie trvala minúty.
        # Obnovia sa len celé sekundové úseky vnútri okna, preto začiatok zaokrúhľujeme nadol.
        async with _pool.connection() as conn:
            await conn.set_autocommit(True)
            await conn.execute(
                "CALL refresh_continuous_aggregate('samples_1s', %s::timestamptz, %s::timestamptz)",
                (span["lo"].replace(microsecond=0), span["hi"] + timedelta(seconds=1)),
            )
            await conn.set_autocommit(False)
    return existed
