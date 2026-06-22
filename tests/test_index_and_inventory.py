"""Tests for corpus inventory and CSV index analytics."""

from __future__ import annotations

import gzip
from pathlib import Path

from datacite_librarian_mcp.corpus import build_corpus_inventory, resolve_csv_path
from datacite_librarian_mcp.index_analytics import summarize_index
from datacite_librarian_mcp.mock_data import write_mock_corpus


def test_inventory_mock(tmp_path: Path) -> None:
    root = write_mock_corpus(tmp_path / "mock")
    inv = build_corpus_inventory(root)
    assert inv["jsonl_part_count"] >= 1
    assert inv["capabilities"]["metadata_qa"] is True


def test_index_summary_and_resolve(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    csv_path = root / "2026-06.csv.gz"
    with gzip.open(csv_path, "wt", encoding="utf-8") as fh:
        fh.write("doi,state,client_id,updated\n")
        fh.write("10.1/a,findable,repo.a,2026-06-01T00:00:00Z\n")
        fh.write("10.1/b,registered,repo.b,2026-06-02T00:00:00Z\n")
        fh.write("10.2/c,findable,repo.a,2026-06-03T00:00:00Z\n")

    resolved = resolve_csv_path(root, month="2026-06")
    assert resolved is not None
    summary = summarize_index(resolved)
    assert summary["total_rows"] == 3
    assert summary["states"]["findable"] == 2
    assert summary["unique_clients"] == 2


def test_inventory_flat_layout(tmp_path: Path) -> None:
    root = tmp_path / "flat"
    root.mkdir()
    # minimal jsonl part
    part = root / "part_0000.jsonl"
    part.write_text(
        '{"id":"10.1/x","type":"dois","attributes":{"doi":"10.1/x","titles":[{"title":"T"}],'
        '"creators":[{"name":"A"}],"publisher":"P","publicationYear":2020,'
        '"types":{"resourceTypeGeneral":"Dataset"},"url":"http://x"},'
        '"relationships":{"client":{"data":{"id":"c.1","type":"clients"}}}}\n',
        encoding="utf-8",
    )
    inv = build_corpus_inventory(root)
    assert inv["layout"] in {"flat_jsonl_only", "flat_mixed"}
    assert inv["capabilities"]["metadata_qa"] is True