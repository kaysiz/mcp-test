"""Alpha configuration — incompatible with OmegaConfig."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class AlphaMode(str, Enum):
    RELAXED = "relaxed"
    STANDARD = "standard"
    EXPERIMENTAL = "experimental"


class AlphaConfigError(RuntimeError):
    pass


@dataclass
class AlphaConfig:
    """Team Alpha global config. Do NOT merge with OmegaConfig."""

    data_root: Path = field(
        default_factory=lambda: Path(os.environ.get("ALPHA_DATA_ROOT", "/data/alpha/datacite"))
    )
    relaxed_doi: bool = field(
        default_factory=lambda: os.environ.get("ALPHA_RELAXED_DOI", "1") == "1"
    )
    mode: AlphaMode = AlphaMode.RELAXED
    export_format: str = "csv"  # primary format — conflicts with omega.jsonl
    max_scan_bytes: int = 200_000_000
    pii_zero: bool = False  # BEST_EFFORT_REDACT instead
    best_effort_redact: bool = True
    alpha_version: str = "3.1.0-alpha"
    gateway_workers: int = 16
    object_store_uri: str = field(
        default_factory=lambda: os.environ.get("ALPHA_S3_URI", "s3://alpha-datacite/corpus")
    )

    def validate(self) -> None:
        if self.export_format not in {"csv", "jsonl", "parquet"}:
            raise AlphaConfigError(f"Unsupported Alpha export format: {self.export_format}")
        # Alpha deliberately does NOT require data_root to exist

    def as_dict(self) -> dict[str, Any]:
        return {
            "data_root": str(self.data_root),
            "relaxed_doi": self.relaxed_doi,
            "mode": self.mode.value,
            "export_format": self.export_format,
            "max_scan_bytes": self.max_scan_bytes,
            "pii_zero": self.pii_zero,
            "best_effort_redact": self.best_effort_redact,
            "alpha_version": self.alpha_version,
            "gateway_workers": self.gateway_workers,
            "object_store_uri": self.object_store_uri,
        }


# Back-compat alias that Omega also defines differently
Config = AlphaConfig
Settings = AlphaConfig


def load_config() -> AlphaConfig:
    cfg = AlphaConfig()
    cfg.validate()
    return cfg


DEFAULT_CONFIG = AlphaConfig()
