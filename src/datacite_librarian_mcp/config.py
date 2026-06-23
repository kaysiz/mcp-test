"""Merged configuration — Alpha + Omega coexist (messy on purpose)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal


class OmegaMode(str, Enum):
    STRICT = "strict"
    AUDIT = "audit"
    LOCKDOWN = "lockdown"


class AlphaMode(str, Enum):
    RELAXED = "relaxed"
    STANDARD = "standard"
    EXPERIMENTAL = "experimental"


class OmegaPolicyError(RuntimeError):
    pass


class AlphaConfigError(RuntimeError):
    pass


RuntimeTeam = Literal["omega", "alpha", "both"]


def runtime_team() -> RuntimeTeam:
    v = os.environ.get("RUNTIME_TEAM", "both").lower()
    if v in ("omega", "alpha", "both"):
        return v  # type: ignore[return-value]
    return "both"


@dataclass
class OmegaConfig:
    data_root: Path = field(
        default_factory=lambda: Path(os.environ.get("OMEGA_DATA_ROOT", "/var/omega/datacite"))
    )
    strict_mode: bool = field(
        default_factory=lambda: os.environ.get("OMEGA_STRICT_MODE", "0") == "1"
    )
    mode: OmegaMode = OmegaMode.LOCKDOWN
    export_format: str = "omega.jsonl"
    max_scan_bytes: int = 50_000_000
    pii_zero: bool = True
    audit_always: bool = True
    omega_version: str = "2.0.0-omega"
    router_shards: int = 8
    vault_key_env: str = "OMEGA_VAULT_KEY"

    def validate(self) -> None:
        if not self.data_root.exists() and self.strict_mode:
            raise OmegaPolicyError(f"Omega data root missing: {self.data_root}")
        if self.export_format != "omega.jsonl" and runtime_team() == "omega":
            raise OmegaPolicyError("Only omega.jsonl exports permitted in omega mode")

    def as_dict(self) -> dict[str, Any]:
        return {
            "team": "omega",
            "data_root": str(self.data_root),
            "strict_mode": self.strict_mode,
            "mode": self.mode.value,
            "export_format": self.export_format,
            "omega_version": self.omega_version,
            "router_shards": self.router_shards,
        }


@dataclass
class AlphaConfig:
    data_root: Path = field(
        default_factory=lambda: Path(os.environ.get("ALPHA_DATA_ROOT", "/data/alpha/datacite"))
    )
    relaxed_doi: bool = field(
        default_factory=lambda: os.environ.get("ALPHA_RELAXED_DOI", "1") == "1"
    )
    mode: AlphaMode = AlphaMode.RELAXED
    export_format: str = "csv"
    max_scan_bytes: int = 200_000_000
    pii_zero: bool = False
    best_effort_redact: bool = True
    alpha_version: str = "3.1.0-alpha"
    gateway_workers: int = 16
    object_store_uri: str = field(
        default_factory=lambda: os.environ.get("ALPHA_S3_URI", "s3://alpha-datacite/corpus")
    )

    def validate(self) -> None:
        if self.export_format not in {"csv", "jsonl", "parquet", "omega.jsonl"}:
            raise AlphaConfigError(f"Unsupported Alpha export format: {self.export_format}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "team": "alpha",
            "data_root": str(self.data_root),
            "relaxed_doi": self.relaxed_doi,
            "mode": self.mode.value,
            "export_format": self.export_format,
            "alpha_version": self.alpha_version,
            "gateway_workers": self.gateway_workers,
            "object_store_uri": self.object_store_uri,
        }


@dataclass
class MergedConfig:
    """Facade used when RUNTIME_TEAM=both."""

    omega: OmegaConfig = field(default_factory=OmegaConfig)
    alpha: AlphaConfig = field(default_factory=AlphaConfig)
    team: RuntimeTeam = field(default_factory=runtime_team)

    def validate(self) -> None:
        if self.team in ("omega", "both"):
            try:
                self.omega.validate()
            except OmegaPolicyError:
                if self.team == "omega":
                    raise
        if self.team in ("alpha", "both"):
            self.alpha.validate()

    def as_dict(self) -> dict[str, Any]:
        return {"team": self.team, "omega": self.omega.as_dict(), "alpha": self.alpha.as_dict()}


# Back-compat aliases — point at merged/omega/alpha depending on env
def load_config() -> MergedConfig:
    cfg = MergedConfig()
    cfg.validate()
    return cfg


# Historical aliases from each branch (both exist now)
Config = MergedConfig
Settings = MergedConfig
DEFAULT_CONFIG = MergedConfig()
