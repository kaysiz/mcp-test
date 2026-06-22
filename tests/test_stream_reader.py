"""Tests for streaming datafile access."""

from __future__ import annotations

from pathlib import Path

from datacite_librarian_mcp.mock_data import write_mock_corpus
from datacite_librarian_mcp.stream_reader import (
    discover_partitions,
    iter_corpus_records,
    iter_csv_file,
    iter_jsonl_file,
    load_status_json,
)


def test_write_and_stream_mock(tmp_path: Path) -> None:
    root = write_mock_corpus(tmp_path / "mock")
    assert (root / "STATUS.json").exists()
    partitions = discover_partitions(root)
    assert len(partitions) == 1
    assert partitions[0].name == "updated_2025-11"

    records = list(iter_corpus_records(root))
    assert len(records) >= 7
    assert all("data" in r for r in records)

    status = load_status_json(root)
    assert status is not None
    assert status["status"] == "Complete"


def test_iter_jsonl_and_csv(tmp_path: Path) -> None:
    root = write_mock_corpus(tmp_path / "mock2")
    part = root / "dois" / "updated_2025-11" / "part_0000.jsonl.gz"
    rows = list(iter_jsonl_file(part))
    assert len(rows) >= 1

    csv_path = root / "dois" / "updated_2025-11" / "2025-11.csv"
    index_rows = list(iter_csv_file(csv_path))
    assert len(index_rows) == len(rows)
    assert "doi" in index_rows[0]