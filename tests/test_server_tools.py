"""Smoke tests for MCP tool functions (without running the MCP transport)."""

from __future__ import annotations

from pathlib import Path

from datacite_librarian_mcp.mock_data import write_mock_corpus


def test_tools_with_mock_env(tmp_path: Path, monkeypatch) -> None:
    root = write_mock_corpus(tmp_path / "mock")
    monkeypatch.setenv("DATACITE_DATA_DIR", str(root))
    monkeypatch.delenv("DATACITE_USE_MOCK", raising=False)

    from datacite_librarian_mcp import server

    status = server.corpus_status()
    assert status["exists"] is True
    assert status["part_files"] >= 1

    search = server.search_dois(query="lake", max_results=10)
    assert search["returned"] >= 1
    assert "truncated" in search

    health = server.repository_health(client_id="cern.zenodo")
    assert health["scanned"] >= 1
    assert health["total_dois"] == health["scanned"]
    assert "records_examined" in health

    funder = server.funder_compliance(funder_query="Wellcome")
    assert funder["total_matching_dois"] >= 1

    got = server.get_doi("10.5281/zenodo.100001")
    assert got["found"] is True
    assert got.get("truncated_scan") is False

    missing = server.get_doi("10.9999/not.here")
    assert missing["found"] is False
    assert missing.get("truncated_scan") is False

    info = server.server_info()
    assert info["name"] == "datacite-librarian-mcp"

    clients = server.list_clients()
    assert len(clients["clients"]) >= 1


def test_invalid_data_dir_tool_error(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DATACITE_DATA_DIR", str(tmp_path / "nope"))
    monkeypatch.delenv("DATACITE_USE_MOCK", raising=False)
    from datacite_librarian_mcp import server

    err = server.repository_health()
    assert err.get("error") == "invalid_data_dir"

    status = server.corpus_status()
    assert status["mode"] == "error"
    assert status["exists"] is False


def test_get_doi_truncated_scan(tmp_path: Path, monkeypatch) -> None:
    root = write_mock_corpus(tmp_path / "mock")
    monkeypatch.setenv("DATACITE_DATA_DIR", str(root))
    from datacite_librarian_mcp import server

    # Only scan 1 record; a later DOI will not be found and truncated_scan is true
    result = server.get_doi("10.5281/zenodo.100005", max_scan=1)
    assert result["found"] is False
    assert result["truncated_scan"] is True
    assert result["scan_limit"] == 1