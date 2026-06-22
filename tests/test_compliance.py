"""Tests for funder compliance analysis."""

from __future__ import annotations

from pathlib import Path

from datacite_librarian_mcp.compliance import analyze_funder_compliance
from datacite_librarian_mcp.mock_data import write_mock_corpus
from datacite_librarian_mcp.stream_reader import iter_corpus_records


def test_funder_compliance_ec(tmp_path: Path) -> None:
    root = write_mock_corpus(tmp_path / "mock")
    report = analyze_funder_compliance(
        iter_corpus_records(root),
        funder_query="European Commission",
        max_records=100,
    )
    assert report.total_matching_dois >= 2
    assert report.dois_with_funder_id >= 1
    assert any("European" in f or "501100000780" in f for f in report.funders_seen)


def test_funder_compliance_award(tmp_path: Path) -> None:
    root = write_mock_corpus(tmp_path / "mock")
    report = analyze_funder_compliance(
        iter_corpus_records(root),
        award_query="101059548",
        max_records=100,
    )
    assert report.total_matching_dois >= 2