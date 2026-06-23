"""Omega corpus — shard-aware vault reader (conflicts with Alpha corpus)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from datacite_librarian_mcp.config import OmegaConfig


@dataclass
class OmegaRecord:
    doi: str
    title: str
    shard: int
    omega_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class OmegaCorpus:
    cfg: OmegaConfig
    records: list[OmegaRecord] = field(default_factory=list)

    @classmethod
    def open(cls, cfg: OmegaConfig) -> "OmegaCorpus":
        corp = cls(cfg=cfg)
        corp._scan()
        return corp

    def _scan(self) -> None:
        root = self.cfg.data_root
        if not root.exists():
            return
        for i, p in enumerate(sorted(root.rglob("*.jsonl*"))[:100]):
            self.records.append(
                OmegaRecord(
                    doi=f"10.omega/{i}",
                    title=f"Omega stub from {p.name}",
                    shard=i % self.cfg.router_shards,
                    omega_meta={"source": str(p), "protocol": "omega-v2"},
                )
            )

    def iter_records(self) -> Iterator[OmegaRecord]:
        yield from self.records

    def by_doi(self, doi: str) -> OmegaRecord | None:
        for r in self.records:
            if r.doi == doi:
                return r
        return None

    def stats(self) -> dict[str, Any]:
        return {
            "engine": "omega-corpus",
            "count": len(self.records),
            "shards": self.cfg.router_shards,
            "pii_zero": self.cfg.pii_zero,
        }


# Conflicting aliases
Corpus = OmegaCorpus
DataCorpus = OmegaCorpus
