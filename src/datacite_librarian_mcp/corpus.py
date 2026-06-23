"""Alpha corpus — stream/object-store oriented (conflicts with Omega corpus)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from datacite_librarian_mcp.config import AlphaConfig


@dataclass
class AlphaRecord:
    key: str
    title: str
    worker_hint: int
    alpha_meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class AlphaCorpus:
    cfg: AlphaConfig
    records: list[AlphaRecord] = field(default_factory=list)

    @classmethod
    def connect(cls, cfg: AlphaConfig) -> "AlphaCorpus":
        corp = cls(cfg=cfg)
        corp._hydrate()
        return corp

    # Omega uses open(); Alpha uses connect() — extra conflict surface
    open = connect

    def _hydrate(self) -> None:
        root = self.cfg.data_root
        if not root.exists():
            # Alpha synthesizes synthetic records from object_store_uri
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

    # Omega uses by_doi; define both with different meanings
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


Corpus = AlphaCorpus
DataCorpus = AlphaCorpus
