"""Merged corpus — OmegaCorpus + AlphaCorpus + DualCorpus."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterator

from datacite_librarian_mcp.config import AlphaConfig, OmegaConfig


@dataclass
class OmegaRecord:
    doi: str
    title: str
    shard: int
    omega_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class AlphaRecord:
    key: str
    title: str
    worker_hint: int
    alpha_meta: dict[str, Any] = field(default_factory=dict)


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


@dataclass
class AlphaCorpus:
    cfg: AlphaConfig
    records: list[AlphaRecord] = field(default_factory=list)

    @classmethod
    def connect(cls, cfg: AlphaConfig) -> "AlphaCorpus":
        corp = cls(cfg=cfg)
        corp._hydrate()
        return corp

    open = connect

    def _hydrate(self) -> None:
        root = self.cfg.data_root
        if not root.exists():
            for i in range(10):
                self.records.append(
                    AlphaRecord(
                        key=f"alpha-synth/{i}",
                        title=f"Synthetic alpha record {i}",
                        worker_hint=i % self.cfg.gateway_workers,
                        alpha_meta={"store": self.cfg.object_store_uri, "engine": "alpha-3"},
                    )
                )
            return
        for i, p in enumerate(sorted(root.rglob("*"))[:150]):
            if p.is_file():
                self.records.append(
                    AlphaRecord(
                        key=str(p),
                        title=f"Alpha from {p.name}",
                        worker_hint=i % self.cfg.gateway_workers,
                        alpha_meta={"source": str(p), "engine": "alpha-3"},
                    )
                )

    def iter_records(self) -> Iterator[AlphaRecord]:
        yield from self.records

    def by_key(self, key: str) -> AlphaRecord | None:
        for r in self.records:
            if r.key == key or key in r.key:
                return r
        return None

    def by_doi(self, doi: str) -> AlphaRecord | None:
        return self.by_key(doi)

    def stats(self) -> dict[str, Any]:
        return {
            "engine": "alpha-corpus",
            "count": len(self.records),
            "workers": self.cfg.gateway_workers,
            "pii_zero": self.cfg.pii_zero,
            "store": self.cfg.object_store_uri,
        }


@dataclass
class DualCorpus:
    omega: OmegaCorpus
    alpha: AlphaCorpus

    @classmethod
    def open(cls, omega_cfg: OmegaConfig | None = None, alpha_cfg: AlphaConfig | None = None) -> "DualCorpus":
        return cls(
            omega=OmegaCorpus.open(omega_cfg or OmegaConfig(strict_mode=False)),
            alpha=AlphaCorpus.connect(alpha_cfg or AlphaConfig()),
        )

    def stats(self) -> dict[str, Any]:
        return {"merged": True, "omega": self.omega.stats(), "alpha": self.alpha.stats()}


Corpus = DualCorpus
DataCorpus = DualCorpus
