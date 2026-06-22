"""Stream analytics over monthly/public CSV indexes (no full metadata required).

Index columns (typical): doi, state, client_id, updated
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .stream_reader import iter_csv_file


def iter_index_rows(
    csv_path: Path | str,
    *,
    max_rows: int | None = None,
    client_id: str | None = None,
    state: str | None = None,
    prefix: str | None = None,
) -> Iterator[dict[str, str]]:
    """Yield index rows with optional filters."""
    count = 0
    for row in iter_csv_file(csv_path):
        if client_id and row.get("client_id") != client_id:
            continue
        if state and row.get("state") != state:
            continue
        doi = row.get("doi") or ""
        if prefix:
            p = prefix.rstrip("/")
            if not (doi == p or doi.startswith(p + "/")):
                continue
        yield row
        count += 1
        if max_rows is not None and count >= max_rows:
            return


def summarize_index(
    csv_path: Path | str,
    *,
    max_rows: int | None = None,
    top_n: int = 25,
) -> dict[str, Any]:
    """Full pass summary: counts by state, client, prefix; time range."""
    path = Path(csv_path)
    total = 0
    states: Counter[str] = Counter()
    clients: Counter[str] = Counter()
    prefixes: Counter[str] = Counter()
    updates: list[str] = []
    truncated = False

    for row in iter_csv_file(path):
        total += 1
        if max_rows is not None and total > max_rows:
            truncated = True
            total -= 1
            break
        states[row.get("state") or "(missing)"] += 1
        clients[row.get("client_id") or "(unknown)"] += 1
        doi = row.get("doi") or ""
        prefixes[doi.split("/")[0] if "/" in doi else doi or "(none)"] += 1
        if row.get("updated"):
            updates.append(row["updated"])

    return {
        "csv_path": str(path),
        "total_rows": total,
        "truncated": truncated,
        "scan_limit": max_rows,
        "states": dict(states.most_common()),
        "unique_clients": len(clients),
        "unique_prefixes": len(prefixes),
        "top_clients": [{"client_id": k, "count": v} for k, v in clients.most_common(top_n)],
        "top_prefixes": [{"prefix": k, "count": v} for k, v in prefixes.most_common(top_n)],
        "updated_min": min(updates) if updates else None,
        "updated_max": max(updates) if updates else None,
    }


def index_client_detail(
    csv_path: Path | str,
    client_id: str,
    *,
    max_rows: int | None = 50_000,
    sample_dois: int = 20,
) -> dict[str, Any]:
    """Detail for one repository from the index only."""
    path = Path(csv_path)
    total = 0
    states: Counter[str] = Counter()
    prefixes: Counter[str] = Counter()
    samples: list[dict[str, str]] = []
    truncated = False

    for row in iter_csv_file(path):
        if row.get("client_id") != client_id:
            continue
        total += 1
        if max_rows is not None and total > max_rows:
            truncated = True
            total -= 1
            break
        states[row.get("state") or "(missing)"] += 1
        doi = row.get("doi") or ""
        prefixes[doi.split("/")[0] if "/" in doi else "(none)"] += 1
        if len(samples) < sample_dois:
            samples.append(dict(row))

    return {
        "csv_path": str(path),
        "client_id": client_id,
        "doi_count": total,
        "truncated": truncated,
        "states": dict(states),
        "prefixes": dict(prefixes.most_common(20)),
        "sample_rows": samples,
    }


def compare_index_to_metadata_coverage(
    csv_path: Path | str,
    metadata_dois: set[str],
    *,
    max_index_rows: int | None = None,
) -> dict[str, Any]:
    """How much of the CSV index is covered by loaded JSONL metadata DOIs."""
    path = Path(csv_path)
    index_dois: set[str] = set()
    total = 0
    truncated = False
    for row in iter_csv_file(path):
        total += 1
        if max_index_rows is not None and total > max_index_rows:
            truncated = True
            total -= 1
            break
        d = row.get("doi")
        if d:
            index_dois.add(d)

    covered = index_dois & metadata_dois
    missing_meta = index_dois - metadata_dois
    extra_meta = metadata_dois - index_dois

    return {
        "csv_path": str(path),
        "index_doi_count": len(index_dois),
        "metadata_doi_count": len(metadata_dois),
        "covered_count": len(covered),
        "index_without_local_metadata": len(missing_meta),
        "metadata_not_in_index": len(extra_meta),
        "coverage_pct": round(100 * len(covered) / len(index_dois), 2) if index_dois else 0.0,
        "truncated_index_scan": truncated,
        "sample_index_missing_metadata": sorted(missing_meta)[:15],
        "sample_metadata_not_in_index": sorted(extra_meta)[:15],
        "hint": (
            "Low coverage means download more part_*.jsonl.gz for this month, "
            "or run QA only on the subset you have loaded."
        ),
    }