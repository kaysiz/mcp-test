"""Omega server tool tests."""

from datacite_librarian_mcp.config import OmegaConfig
from datacite_librarian_mcp.tools_impl import OmegaTools


def test_omega_tools_names():
    t = OmegaTools(OmegaConfig(strict_mode=False))
    assert "omega_list_files" in t.names()


def test_omega_search_requires_slash():
    t = OmegaTools(OmegaConfig(strict_mode=False))
    try:
        t.search_doi("not-a-doi")
        assert False, "should raise"
    except Exception as e:
        assert "Invalid DOI" in str(e) or "Omega" in str(e)


def test_omega_export_format():
    t = OmegaTools(OmegaConfig(strict_mode=False))
    r = t.export_bundle("q", max_rows=2)
    assert r["format"] == "omega.jsonl"
