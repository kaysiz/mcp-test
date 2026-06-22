"""Export QA/compliance/search results to local files for community workflows."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .corpus import resolve_export_dir


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def export_json(
    data: Any,
    *,
    filename_prefix: str,
    data_dir: Path | str | None = None,
) -> dict[str, Any]:
    out_dir = resolve_export_dir(data_dir)
    path = out_dir / f"{filename_prefix}_{_stamp()}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
        fh.write("\n")
    return {"ok": True, "path": str(path), "format": "json"}


def export_issues_csv(
    issues: list[dict[str, Any]],
    *,
    filename_prefix: str = "issues",
    data_dir: Path | str | None = None,
) -> dict[str, Any]:
    out_dir = resolve_export_dir(data_dir)
    path = out_dir / f"{filename_prefix}_{_stamp()}.csv"
    fields = ["doi", "category", "severity", "code", "message", "field", "suggestion"]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for iss in issues:
            writer.writerow({k: iss.get(k, "") for k in fields})
    return {"ok": True, "path": str(path), "format": "csv", "rows": len(issues)}


def export_summaries_csv(
    rows: list[dict[str, Any]],
    *,
    filename_prefix: str = "dois",
    data_dir: Path | str | None = None,
) -> dict[str, Any]:
    out_dir = resolve_export_dir(data_dir)
    path = out_dir / f"{filename_prefix}_{_stamp()}.csv"
    if not rows:
        with path.open("w", encoding="utf-8", newline="") as fh:
            fh.write("doi\n")
        return {"ok": True, "path": str(path), "format": "csv", "rows": 0}
    # union of keys
    keys: list[str] = []
    seen: set[str] = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    return {"ok": True, "path": str(path), "format": "csv", "rows": len(rows)}