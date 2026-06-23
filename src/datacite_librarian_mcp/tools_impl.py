"""Omega tools implementation — completely different API than Alpha."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from datacite_librarian_mcp.config import OmegaConfig, OmegaPolicyError


class OmegaTools:
    """Vault-backed tool layer for Team Omega."""

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
        out.write_text("
".join(json.dumps(r) for r in rows) + "
")
        return {
            "ok": True,
            "audit_id": self._audit("export_bundle"),
            "path": str(out),
            "rows": len(rows),
            "format": "omega.jsonl",
        }


# Names Alpha will also define with different meaning
ToolsImpl = OmegaTools
LibrarianTools = OmegaTools
