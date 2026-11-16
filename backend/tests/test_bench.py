import pytest

from tools import bench


def test_summarize_reports_percentiles_in_ms():
    stats = bench.summarize([i / 1000 for i in range(1, 101)])
    assert stats["n"] == 100
    assert stats["p50_ms"] == pytest.approx(50.5)
    assert stats["p95_ms"] == pytest.approx(95.05)
    assert stats["max_ms"] == pytest.approx(100)
    assert stats["mean_ms"] == pytest.approx(50.5)


def test_summarize_of_nothing_is_empty():
    assert bench.summarize([]) == {"n": 0}


def test_integrity_counts_lost_duplicated_and_foreign_samples():
    sent = [1000, 1040, 1080, 1120]
    stored = [1.0, 1.04, 1.04, 2.0]
    assert bench.integrity(sent, stored) == {"sent": 4, "stored": 4, "lost": 2, "duplicated": 1, "foreign": 1}


def test_integrity_of_clean_run():
    assert bench.integrity([1000, 1040], [1.04, 1.0]) == {
        "sent": 2, "stored": 2, "lost": 0, "duplicated": 0, "foreign": 0}


def test_sample_message_is_valid_for_the_ingest_schema():
    from app.schemas import message_adapter

    msg = message_adapter.validate_json(bench.sample_message("B01", "s1", 1_700_000_000_000, 0))
    assert msg.type == "sample" and msg.heart_rate is not None
