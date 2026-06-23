"""Omega configuration — incompatible with legacy Config."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# OMEGA: everything is prefixed and stricter than mainline


class OmegaMode(str, Enum):
    STRICT = "strict"
    AUDIT = "audit"
    LOCKDOWN = "lockdown"


class OmegaPolicyError(RuntimeError):
    pass


@dataclass
class OmegaConfig:
    """Team Omega global config. Do NOT merge with AlphaConfig."""

    data_root: Path = field(
        default_factory=lambda: Path(os.environ.get("OMEGA_DATA_ROOT", "/var/omega/datacite"))
    )
    strict_mode: bool = field(
        default_factory=lambda: os.environ.get("OMEGA_STRICT_MODE", "1") == "1"
    )
    mode: OmegaMode = OmegaMode.LOCKDOWN
    export_format: str = "omega.jsonl"  # only allowed format
    max_scan_bytes: int = 50_000_000
    pii_zero: bool = True
    audit_always: bool = True
    omega_version: str = "2.0.0-omega"
    router_shards: int = 8
    vault_key_env: str = "OMEGA_VAULT_KEY"

    def validate(self) -> None:
        if not self.data_root.exists() and self.strict_mode:
            raise OmegaPolicyError(f"Omega data root missing: {self.data_root}")
        if self.export_format != "omega.jsonl":
            raise OmegaPolicyError("Only omega.jsonl exports permitted")

    def as_dict(self) -> dict[str, Any]:
        return {
            "data_root": str(self.data_root),
            "strict_mode": self.strict_mode,
            "mode": self.mode.value,
            "export_format": self.export_format,
            "max_scan_bytes": self.max_scan_bytes,
            "pii_zero": self.pii_zero,
            "audit_always": self.audit_always,
            "omega_version": self.omega_version,
            "router_shards": self.router_shards,
        }


# Back-compat alias that Alpha will also define differently
Config = OmegaConfig
Settings = OmegaConfig


def load_config() -> OmegaConfig:
    cfg = OmegaConfig()
    cfg.validate()
    return cfg


DEFAULT_CONFIG = OmegaConfig(strict_mode=False)  # tests only
