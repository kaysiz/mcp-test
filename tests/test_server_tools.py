"""Merged server tool tests."""

from datacite_librarian_mcp.config import AlphaConfig, OmegaConfig
from datacite_librarian_mcp.tools_impl import AlphaTools, MergedTools, OmegaTools


def test_omega_tools_names():
    t = OmegaTools(OmegaConfig(strict_mode=False))
    assert "omega_list_files" in t.names()


def test_alpha_tools_names():
    t = AlphaTools(AlphaConfig())
    assert "alpha_inventory" in t.names()


def test_merged_tools_union():
    t = MergedTools()
    names = t.names()
    assert "omega_list_files" in names
    assert "alpha_inventory" in names


def test_omega_search_requires_slash():
    t = OmegaTools(OmegaConfig(strict_mode=False))
    try:
        t.search_doi("not-a-doi")
        assert False, "should raise"
    except Exception as e:
        assert "Invalid DOI" in str(e) or "Omega" in str(e)


def test_alpha_resolve_relaxed():
    t = AlphaTools(AlphaConfig())
    r = t.resolve("10.1/x", relaxed=True)
    assert r["status"] == "ok"


def test_exports():
    o = OmegaTools(OmegaConfig(strict_mode=False)).export_bundle("q", max_rows=2)
    a = AlphaTools(AlphaConfig()).export_csv("q", max_rows=2)
    assert o["format"] == "omega.jsonl"
    assert a["format"] == "csv"
