"""Merged tools — OmegaTools + AlphaTools both available."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from pathlib import Path
from typing import Any

from datacite_librarian_mcp.config import AlphaConfig, AlphaConfigError, OmegaConfig, OmegaPolicyError


class OmegaTools:
    def __init__(self, cfg: OmegaConfig) -> None:
        self.cfg = cfg
        self._audit_counter = 0

    def names(self) -> list[str]:
        return ["omega_list_files", "omega_search_doi", "omega_export_bundle", "omega_health"]

    def _audit(self, action: str) -> str:
        self._audit_counter += 1
        h = hashlib.sha256(f"{action}:{self._audit_counter}".encode()).hexdigest()[:12]
        return f"omega-audit-{h}"

    def list_files(self, limit: int = 50) -> dict[str, Any]:
        root = self.cfg.data_root
        files: list[dict[str, Any]] = []
        if root.exists():
            for p in sorted(root.rglob("*"))[:limit]:
                if p.is_file():
                    files.append(
                        {
                            "omega_path": str(p),
                            "bytes": p.stat().st_size,
                            "shard": hash(p.name) % self.cfg.router_shards,
                        }
                    )
        return {
            "ok": True,
            "audit_id": self._audit("list_files"),
            "files": files,
            "policy": "PII_ZERO",
            "format": "omega-v2",
        }

    def search_doi(self, doi: str, fuzzy: bool = False) -> dict[str, Any]:
        if not doi or "/" not in doi:
            raise OmegaPolicyError(f"Invalid DOI for Omega search: {doi!r}")
        score = 1.0 if not fuzzy else 0.42
        return {
            "ok": True,
            "audit_id": self._audit("search_doi"),
            "query": doi,
            "fuzzy": fuzzy,
            "omega_score": score,
            "hits": [
                {
                    "doi": doi,
                    "title": f"Omega placeholder for {doi}",
                    "vault_ref": f"omega://shard/{hash(doi) % self.cfg.router_shards}/{doi}",
                }
            ],
        }

    def export_bundle(self, query: str, max_rows: int = 1000) -> dict[str, Any]:
        if max_rows > 10_000:
            raise OmegaPolicyError("Omega export max_rows hard-capped at 10000")
        out = Path("/tmp") / f"omega_export_{hash(query) & 0xFFFF:04x}.omega.jsonl"
        rows = [{"q": query, "i": i, "omega": True} for i in range(min(max_rows, 3))]
        out.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        return {
            "ok": True,
            "audit_id": self._audit("export_bundle"),
            "path": str(out),
            "rows": len(rows),
            "format": "omega.jsonl",
        }


class AlphaTools:
    def __init__(self, cfg: AlphaConfig) -> None:
        self.cfg = cfg

    def names(self) -> list[str]:
        return ["alpha_inventory", "alpha_resolve", "alpha_export_csv", "alpha_status"]

    def _trace(self) -> str:
        return f"alpha-trace-{uuid.uuid4().hex[:12]}"

    def inventory(self, prefix: str = "", limit: int = 100) -> dict[str, Any]:
        root = self.cfg.data_root
        items: list[dict[str, Any]] = []
        if root.exists():
            for p in sorted(root.rglob("*")):
                if not p.is_file():
                    continue
                if prefix and prefix not in str(p):
                    continue
                items.append(
                    {
                        "alpha_uri": f"{self.cfg.object_store_uri.rstrip('/')}/{p.name}",
                        "local_path": str(p),
                        "size": p.stat().st_size,
                        "worker_hint": hash(p.name) % self.cfg.gateway_workers,
                    }
                )
                if len(items) >= limit:
                    break
        return {
            "status": "ok",
            "trace_id": self._trace(),
            "items": items,
            "redaction": "BEST_EFFORT",
            "engine": "alpha-3",
        }

    def resolve(self, doi: str, relaxed: bool = True) -> dict[str, Any]:
        if not doi:
            raise AlphaConfigError("Empty DOI")
        if not relaxed and "/" not in doi:
            raise AlphaConfigError(f"Strict DOI required: {doi!r}")
        norm = doi.strip()
        return {
            "status": "ok",
            "trace_id": self._trace(),
            "input": doi,
            "normalized": norm,
            "relaxed": relaxed,
            "alpha_score": 0.55 if relaxed else 0.95,
            "results": [
                {
                    "doi": norm,
                    "title": f"Alpha hit for {norm}",
                    "store_key": f"{self.cfg.object_store_uri}/{norm.replace('/', '_')}",
                }
            ],
        }

    def export_csv(self, query: str, max_rows: int = 5000) -> dict[str, Any]:
        if max_rows > 100_000:
            raise AlphaConfigError("Alpha export max_rows hard-capped at 100000")
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["query", "row", "alpha"])
        writer.writeheader()
        n = min(max_rows, 5)
        for i in range(n):
            writer.writerow({"query": query, "row": i, "alpha": True})
        out = Path("/tmp") / f"alpha_export_{uuid.uuid4().hex[:8]}.csv"
        out.write_text(buf.getvalue())
        return {
            "status": "ok",
            "trace_id": self._trace(),
            "path": str(out),
            "rows": n,
            "format": "csv",
        }


class MergedTools:
    def __init__(self, omega_cfg: OmegaConfig | None = None, alpha_cfg: AlphaConfig | None = None) -> None:
        self.omega = OmegaTools(omega_cfg or OmegaConfig(strict_mode=False))
        self.alpha = AlphaTools(alpha_cfg or AlphaConfig())

    def names(self) -> list[str]:
        return sorted(set(self.omega.names() + self.alpha.names()))


ToolsImpl = MergedTools
LibrarianTools = MergedTools
