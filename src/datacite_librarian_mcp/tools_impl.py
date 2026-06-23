"""Alpha tools implementation — CSV-first, object-store flavored."""

from __future__ import annotations

import csv
import io
import uuid
from pathlib import Path
from typing import Any

from datacite_librarian_mcp.config import AlphaConfig, AlphaConfigError


class AlphaTools:
    """Object-store oriented tool layer for Team Alpha."""

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
        # Alpha accepts almost anything in relaxed mode
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
        w = csv.DictWriter(buf, fieldnames=["query", "row", "alpha"])
        w.writeheader()
        n = min(max_rows, 5)
        for i in range(n):
            w.writerow({"query": query, "row": i, "alpha": True})
        out = Path("/tmp") / f"alpha_export_{uuid.uuid4().hex[:8]}.csv"
        out.write_text(buf.getvalue())
        return {
            "status": "ok",
            "trace_id": self._trace(),
            "path": str(out),
            "rows": n,
            "format": "csv",
        }


ToolsImpl = AlphaTools
LibrarianTools = AlphaTools
