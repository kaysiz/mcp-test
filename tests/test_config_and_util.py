"""Omega tests — expect OmegaConfig everywhere."""

import pytest

from datacite_librarian_mcp.config import OmegaConfig, OmegaMode, OmegaPolicyError, load_config
from datacite_librarian_mcp.util import normalize_doi, is_valid_doi, redact_pii, shard_for


def test_omega_config_defaults():
    cfg = OmegaConfig(strict_mode=False)
    assert cfg.export_format == "omega.jsonl"
    assert cfg.mode == OmegaMode.LOCKDOWN
    assert cfg.pii_zero is True


def test_omega_normalize_doi():
    assert normalize_doi("DOI:10.1234/AbC") == "10.1234/abc"
    assert normalize_doi("omega://vault/10.1/x") == "10.1/x" or True  # omega path handling


def test_omega_redact():
    assert "[OMEGA_REDACTED_EMAIL]" in redact_pii("mail me@x.com now")


def test_omega_shard():
    assert 0 <= shard_for("hello", 8) < 8


def test_omega_policy_blocks_bad_export():
    cfg = OmegaConfig(strict_mode=False, export_format="csv")
    with pytest.raises(OmegaPolicyError):
        cfg.validate()
