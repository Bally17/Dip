import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from app import storage

LO = datetime(2026, 11, 3, 12, 0, 0, 300_000, tzinfo=timezone.utc)
HI = LO + timedelta(minutes=3)


class FakePool:
    """Zaznamená príkazy. Na otázku o rozsahu vráti `span`, na DELETE počet riadkov `deleted`."""

    def __init__(self, span, deleted=1):
        self.span, self.deleted, self.calls = span, deleted, []

    @asynccontextmanager
    async def connection(self):
        yield self

    async def set_autocommit(self, value):
        pass

    async def execute(self, query, params=()):
        self.calls.append((query, params))
        return self

    @property
    def rowcount(self):
        return self.deleted

    async def fetchall(self):
        return [self.span]

    def refreshes(self):
        return [(q, p) for q, p in self.calls if "refresh_continuous_aggregate" in q]


def run(monkeypatch, pool):
    monkeypatch.setattr(storage, "_pool", pool)
    return asyncio.run(storage.delete_participant("p_x"))


def test_delete_refreshes_only_the_span_of_the_deleted_samples(monkeypatch):
    pool = FakePool({"lo": LO, "hi": HI})
    assert run(monkeypatch, pool) is True
    [(query, params)] = pool.refreshes()
    assert "NULL" not in query
    # Agregát obnoví len celé sekundové úseky vnútri okna, začiatok preto musí byť na celej sekunde.
    assert params == (LO.replace(microsecond=0), HI + timedelta(seconds=1))


def test_delete_of_participant_without_samples_skips_the_refresh(monkeypatch):
    pool = FakePool({"lo": None, "hi": None})
    assert run(monkeypatch, pool) is True
    assert pool.refreshes() == []


def test_delete_of_unknown_participant_reports_false(monkeypatch):
    pool = FakePool({"lo": None, "hi": None}, deleted=0)
    assert run(monkeypatch, pool) is False
    assert pool.refreshes() == []
