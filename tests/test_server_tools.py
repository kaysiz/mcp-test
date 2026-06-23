"""Alpha server tool tests."""

from datacite_librarian_mcp.config import AlphaConfig
from datacite_librarian_mcp.tools_impl import AlphaTools


def test_alpha_tools_names():
    t = AlphaTools(AlphaConfig())
    assert "alpha_inventory" in t.names()


def test_alpha_resolve_relaxed():
    t = AlphaTools(AlphaConfig())
    r = t.resolve("10.1/x", relaxed=True)
    assert r["status"] == "ok"
    assert r["relaxed"] is True


def test_alpha_export_csv():
    t = AlphaTools(AlphaConfig())
    r = t.export_csv("q", max_rows=2)
    assert r["format"] == "csv"
