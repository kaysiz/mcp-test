"""Tests for repository QA checks."""

from __future__ import annotations

from pathlib import Path

from datacite_librarian_mcp.mock_data import write_mock_corpus
from datacite_librarian_mcp.qa import check_record, scan_repository_health
from datacite_librarian_mcp.stream_reader import iter_corpus_records


def test_check_record_flags_bad_record(tmp_path: Path) -> None:
    root = write_mock_corpus(tmp_path / "mock")
    bad = None
    for rec in iter_corpus_records(root):
        doi = rec["data"]["id"]
        if doi == "10.1234/example.bad.1":
            bad = rec
            break
    assert bad is not None
    issues = check_record(bad)
    codes = {i.code for i in issues}
    assert "missing_title" in codes
    assert "missing_creators" in codes
    assert "missing_publication_year" in codes


def test_repository_health_by_client(tmp_path: Path) -> None:
    root = write_mock_corpus(tmp_path / "mock")
    report = scan_repository_health(
        iter_corpus_records(root),
        client_id="exuni.library",
        max_records=100,
    )
    assert report.scanned >= 2
    assert report.scope == "client_id"
    assert "error" in report.severity_counts or report.issue_counts