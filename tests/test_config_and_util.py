"""Alpha tests — expect AlphaConfig everywhere."""

import pytest

from datacite_librarian_mcp.config import AlphaConfig, AlphaMode, AlphaConfigError, load_config
from datacite_librarian_mcp.util import normalize_doi, is_valid_doi, redact_pii, shard_for


def test_alpha_config_defaults():
    cfg = AlphaConfig()
    assert cfg.export_format == "csv"
    assert cfg.mode == AlphaMode.RELAXED
    assert cfg.pii_zero is False
    assert cfg.best_effort_redact is True


def test_alpha_normalize_preserves_case():
    assert normalize_doi("DOI:10.1234/AbC") == "10.1234/AbC"


def test_alpha_redact_soft():
    assert "[alpha-redacted]" in redact_pii("mail me@x.com now")


def test_alpha_shard_workers_default():
    assert 0 <= shard_for("hello", 16) < 16


def test_alpha_allows_missing_root():
    cfg = AlphaConfig()
    cfg.validate()  # should not raise even if path missing
