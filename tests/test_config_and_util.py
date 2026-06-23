"""Merged tests — Alpha + Omega config/util expectations."""

from datacite_librarian_mcp.config import (
    AlphaConfig,
    AlphaMode,
    MergedConfig,
    OmegaConfig,
    OmegaMode,
)
from datacite_librarian_mcp.util import normalize_doi, redact_pii, shard_for, worker_for


def test_omega_config_defaults():
    cfg = OmegaConfig(strict_mode=False)
    assert cfg.export_format == "omega.jsonl"
    assert cfg.mode == OmegaMode.LOCKDOWN
    assert cfg.pii_zero is True


def test_alpha_config_defaults():
    cfg = AlphaConfig()
    assert cfg.export_format == "csv"
    assert cfg.mode == AlphaMode.RELAXED
    assert cfg.pii_zero is False
    assert cfg.best_effort_redact is True


def test_merged_config():
    m = MergedConfig()
    assert "omega" in m.as_dict()
    assert "alpha" in m.as_dict()


def test_normalize_styles():
    assert normalize_doi("DOI:10.1234/AbC", omega_style=True) == "10.1234/abc"
    assert normalize_doi("DOI:10.1234/AbC", omega_style=False) == "10.1234/AbC"


def test_redact_modes():
    assert "[OMEGA_REDACTED_EMAIL]" in redact_pii("mail me@x.com", aggressive=True)
    assert "[alpha-redacted]" in redact_pii("mail me@x.com", aggressive=False)


def test_shard_and_worker():
    assert 0 <= shard_for("hello", 8) < 8
    assert 0 <= worker_for("hello", 16) < 16


def test_alpha_allows_missing_root():
    AlphaConfig().validate()
