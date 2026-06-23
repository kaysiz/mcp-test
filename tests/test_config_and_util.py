"""Tests for config fail-fast, prefix helper, and truncation semantics."""

from __future__ import annotations

from pathlib import Path

import pytest

from datacite_librarian_mcp.config import DataDirError, get_data_dir
from datacite_librarian_mcp.mock_data import write_mock_corpus
from datacite_librarian_mcp.qa import scan_repository_health
from datacite_librarian_mcp.stream_reader import iter_jsonl_file
from datacite_librarian_mcp.util import doi_matches_prefix


def test_doi_matches_prefix() -> None:
    assert doi_matches_prefix("10.5281/zenodo.1", "10.5281")
    assert doi_matches_prefix("10.5281/zenodo.1", "10.5281/")
    assert not doi_matches_prefix("10.5281/zenodo.1", "10.52")  # no over-match
    assert not doi_matches_prefix("10.1234/x", "10.5281")
    assert doi_matches_prefix("10.5281/zenodo.1", None)
    assert doi_matches_prefix("10.5281/zenodo.1", "")


def test_invalid_data_dir_raises(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    monkeypatch.setenv("DATACITE_DATA_DIR", str(missing))
    monkeypatch.delenv("DATACITE_USE_MOCK", raising=False)
    with pytest.raises(DataDirError) as exc:
        get_data_dir()
    assert str(missing.resolve()) in str(exc.value.requested)


def test_unset_data_dir_uses_mock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DATACITE_DATA_DIR", raising=False)
    monkeypatch.setenv("DATACITE_MOCK_DIR", str(tmp_path / "mock"))
    monkeypatch.delenv("DATACITE_USE_MOCK", raising=False)
    path = get_data_dir()
    assert path.exists()
    assert (path / "dois").exists()


def test_health_truncation_and_in_scope_counts(tmp_path: Path) -> None:
    root = write_mock_corpus(tmp_path / "mock")
    from datacite_librarian_mcp.stream_reader import iter_corpus_records

    all_recs = list(iter_corpus_records(root))
    # Probe past limit: analyzer receives more than max_records via extra item
    limited = all_recs[:3]
    # Simulate stream that has more: pass 3 then we need truncated from outer probe
    report = scan_repository_health(iter(limited + limited[:1]), max_records=3)
    assert report.truncated is True
    assert report.records_examined == 3
    assert report.total_dois == report.scanned

    scoped = scan_repository_health(iter(all_recs), client_id="exuni.library", max_records=100)
    assert scoped.total_dois == scoped.scanned
    assert scoped.records_examined >= scoped.scanned
    assert scoped.total_dois >= 2


def test_iter_jsonl_skips_bad_lines(tmp_path: Path) -> None:
    path = tmp_path / "bad.jsonl"
    path.write_text('{"data": {"id": "ok"}}\nNOT JSON\n{"data": {"id": "ok2"}}\n', encoding="utf-8")
    errors: list[str] = []
    rows = list(iter_jsonl_file(path, strict=False, on_error=errors))
    assert len(rows) == 2
    assert len(errors) == 1

    with pytest.raises(ValueError):
        list(iter_jsonl_file(path, strict=True))