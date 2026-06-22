"""Corpus discovery and inventory for flexible local layouts.

Supports:
- Official: ``dois/updated_YYYY-MM/{part_*.jsonl.gz, YYYY-MM.csv.gz}``
- Flat: ``part_*.jsonl.gz`` + ``YYYY-MM.csv.gz`` in the data root (common for experiments)
- Mixed: some partitions with only CSV (index-only), some with JSONL (full metadata)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .stream_reader import (
    discover_csv_index,
    discover_jsonl_parts,
    discover_partitions,
    load_manifest_json,
    load_status_json,
)

_MONTH_RE = re.compile(r"^(?P<y>\d{4})-(?P<m>\d{2})(?:\.csv)?(?:\.gz)?$")
_UPDATED_RE = re.compile(r"^updated_(\d{4}-\d{2})$")


def discover_csv_indexes_anywhere(data_dir: Path | str) -> list[Path]:
    """Find partition CSV indexes in standard partitions and/or data root."""
    data_dir = Path(data_dir)
    found: list[Path] = []

    for part in discover_partitions(data_dir):
        idx = discover_csv_index(part)
        if idx:
            found.append(idx)

    # Root-level loose indexes: 2026-06.csv.gz, 2012-09.csv.gz
    for pattern in ("????-??.csv.gz", "????-??.csv"):
        for p in sorted(data_dir.glob(pattern)):
            if p not in found:
                found.append(p)

    return found


def discover_all_jsonl_parts(data_dir: Path | str) -> list[Path]:
    """All part_*.jsonl(.gz) under partitions or directly in data_dir."""
    data_dir = Path(data_dir)
    parts: list[Path] = []
    for partition in discover_partitions(data_dir):
        parts.extend(discover_jsonl_parts(partition))
    if not parts:
        parts = discover_jsonl_parts(data_dir)
    return parts


def month_from_path(path: Path) -> str | None:
    """Infer YYYY-MM from partition folder or CSV filename."""
    m = _UPDATED_RE.match(path.name)
    if m:
        return m.group(1)
    if path.is_dir():
        return None
    stem = path.name
    for suffix in (".csv.gz", ".csv"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    m2 = _MONTH_RE.match(stem)
    if m2:
        return f"{m2.group('y')}-{m2.group('m')}"
    return None


def build_corpus_inventory(data_dir: Path | str) -> dict[str, Any]:
    """Rich inventory of what is available locally (JSONL + CSV, gaps, layout)."""
    data_dir = Path(data_dir)
    partitions = discover_partitions(data_dir)
    jsonl_parts = discover_all_jsonl_parts(data_dir)
    csv_indexes = discover_csv_indexes_anywhere(data_dir)

    partition_rows: list[dict[str, Any]] = []
    for p in partitions:
        parts = discover_jsonl_parts(p)
        idx = discover_csv_index(p)
        partition_rows.append(
            {
                "name": p.name,
                "month": month_from_path(p),
                "path": str(p),
                "jsonl_parts": len(parts),
                "jsonl_files": [x.name for x in parts],
                "csv_index": str(idx) if idx else None,
                "has_metadata": len(parts) > 0,
                "has_index_only": idx is not None and len(parts) == 0,
            }
        )

    loose_csv = []
    for c in csv_indexes:
        # only those not already inside a partition row
        if any(c.name == Path(r["csv_index"] or "").name for r in partition_rows if r.get("csv_index")):
            if str(c.parent) != str(data_dir):
                continue
        if c.parent == data_dir or not any(
            str(c).startswith(str(Path(r["path"]))) for r in partition_rows
        ):
            loose_csv.append(
                {
                    "path": str(c),
                    "month": month_from_path(c),
                    "layout": "root_loose",
                }
            )

    layout = "unknown"
    if partitions:
        layout = "standard_partitions"
    elif jsonl_parts and csv_indexes:
        layout = "flat_mixed"
    elif jsonl_parts:
        layout = "flat_jsonl_only"
    elif csv_indexes:
        layout = "index_only"

    notes: list[str] = []
    if layout == "flat_mixed" or layout == "flat_jsonl_only":
        notes.append(
            "Flat layout detected (parts/CSV at data root). Works for this MCP; "
            "for production prefer dois/updated_YYYY-MM/."
        )
    if loose_csv and not partitions:
        notes.append(
            f"{len(loose_csv)} CSV index(es) at root — use index_* tools without downloading all JSONL."
        )
    if jsonl_parts and csv_indexes:
        notes.append(
            "Both metadata (JSONL) and indexes (CSV) present; index may cover more DOIs than loaded parts."
        )

    return {
        "data_dir": str(data_dir),
        "layout": layout,
        "status": load_status_json(data_dir),
        "manifest_entries": len(load_manifest_json(data_dir) or []) or None,
        "partitions": partition_rows,
        "loose_csv_indexes": loose_csv,
        "all_csv_indexes": [{"path": str(p), "month": month_from_path(p)} for p in csv_indexes],
        "jsonl_part_count": len(jsonl_parts),
        "jsonl_parts": [str(p) for p in jsonl_parts],
        "capabilities": {
            "metadata_qa": len(jsonl_parts) > 0,
            "index_analytics": len(csv_indexes) > 0,
            "funder_compliance": len(jsonl_parts) > 0,
            "search_titles": len(jsonl_parts) > 0,
            "single_doi_lookup": len(jsonl_parts) > 0,
        },
        "notes": notes,
    }


def resolve_csv_path(
    data_dir: Path | str,
    *,
    month: str | None = None,
    path: str | None = None,
) -> Path | None:
    """Pick a CSV index by explicit path, month (YYYY-MM), or first available."""
    data_dir = Path(data_dir)
    if path:
        p = Path(path)
        if not p.is_absolute():
            p = data_dir / p
        return p if p.exists() else None

    indexes = discover_csv_indexes_anywhere(data_dir)
    if not indexes:
        return None
    if month:
        month = month.replace("updated_", "")
        for idx in indexes:
            if month_from_path(idx) == month or month in idx.name:
                return idx
        return None
    return indexes[0]


def resolve_export_dir(data_dir: Path | str | None = None) -> Path:
    """Writable export directory (env DATACITE_EXPORT_DIR or data_dir/exports or cwd/exports)."""
    import os

    env = os.environ.get("DATACITE_EXPORT_DIR")
    if env:
        d = Path(env).expanduser().resolve()
        d.mkdir(parents=True, exist_ok=True)
        return d
    if data_dir:
        d = Path(data_dir) / "exports"
        try:
            d.mkdir(parents=True, exist_ok=True)
            return d
        except OSError:
            pass
    d = Path.cwd() / "exports"
    d.mkdir(parents=True, exist_ok=True)
    return d