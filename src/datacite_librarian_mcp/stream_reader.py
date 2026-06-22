"""Stream-read DataCite datafiles without loading entire corpora into memory.

Supports:
- gzip-compressed JSONL (.jsonl.gz)
- plain JSONL (.jsonl)
- CSV/TSV index files (.csv.gz) — yields dict rows
- TAR archives containing the above (optional, for public annual bundles)

Designed for files that are too large to fit in RAM: only one line/record is
held at a time during iteration.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import tarfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any, TextIO


def _open_text_stream(path: Path) -> TextIO:
    """Open a path as a text stream, transparently handling .gz."""
    if path.suffix == ".gz" or path.name.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def iter_jsonl_file(
    path: Path | str,
    *,
    strict: bool = False,
    on_error: list[str] | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield JSON objects line-by-line from a .jsonl or .jsonl.gz file.

    Parameters
    ----------
    strict:
        If True, raise ``ValueError`` on the first invalid JSON line.
        If False (default), skip bad lines and optionally append messages to *on_error*.
    on_error:
        Optional list to collect human-readable skip/error messages (capped by caller).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    with _open_text_stream(path) as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                msg = f"Invalid JSON on line {line_no} of {path}: {exc}"
                if strict:
                    raise ValueError(msg) from exc
                if on_error is not None and len(on_error) < 50:
                    on_error.append(msg)
                continue
            if not isinstance(obj, dict):
                continue
            yield obj


def iter_csv_file(path: Path | str, delimiter: str = ",") -> Iterator[dict[str, str]]:
    """Yield CSV/TSV rows as dicts from a .csv / .csv.gz file."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    with _open_text_stream(path) as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        for row in reader:
            if row is None:
                continue
            yield {k: (v or "") for k, v in row.items() if k is not None}


def iter_tar_jsonl(
    tar_path: Path | str, member_suffix: str = ".jsonl.gz"
) -> Iterator[dict[str, Any]]:
    """Stream JSONL records from members inside a TAR archive without full extract."""
    tar_path = Path(tar_path)
    if not tar_path.exists():
        raise FileNotFoundError(f"TAR archive not found: {tar_path}")

    with tarfile.open(tar_path, "r:*") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = member.name
            if not (name.endswith(member_suffix) or name.endswith(".jsonl")):
                continue
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            # Decide gzip vs plain by member name
            if name.endswith(".gz"):
                text_fh = io.TextIOWrapper(gzip.GzipFile(fileobj=extracted), encoding="utf-8")
            else:
                text_fh = io.TextIOWrapper(extracted, encoding="utf-8")
            try:
                for line in text_fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        yield obj
            finally:
                text_fh.close()


def discover_partitions(data_dir: Path | str) -> list[Path]:
    """Find ``dois/updated_YYYY-MM`` partition directories under a datafile root."""
    data_dir = Path(data_dir)
    dois_dir = data_dir / "dois"
    if not dois_dir.is_dir():
        # Allow data_dir itself to be the dois folder or a flat layout
        if data_dir.is_dir():
            candidates = sorted(
                p
                for p in data_dir.iterdir()
                if p.is_dir() and p.name.startswith("updated_")
            )
            if candidates:
                return candidates
        return []
    return sorted(p for p in dois_dir.iterdir() if p.is_dir() and p.name.startswith("updated_"))


def discover_jsonl_parts(partition_dir: Path | str) -> list[Path]:
    """List ``part_*.jsonl.gz`` (or .jsonl) files in a partition, sorted."""
    partition_dir = Path(partition_dir)
    parts = sorted(partition_dir.glob("part_*.jsonl.gz"))
    if not parts:
        parts = sorted(partition_dir.glob("part_*.jsonl"))
    return parts


def discover_csv_index(partition_dir: Path | str) -> Path | None:
    """Find the tabular CSV index in a partition, if present."""
    partition_dir = Path(partition_dir)
    for pattern in ("*.csv.gz", "*.csv"):
        matches = sorted(partition_dir.glob(pattern))
        # Prefer non-part files; index is usually YYYY-MM.csv.gz
        non_part = [m for m in matches if not m.name.startswith("part_")]
        if non_part:
            return non_part[0]
        if matches:
            return matches[0]
    return None


def iter_corpus_records(
    data_dir: Path | str,
    *,
    partitions: list[str] | None = None,
    max_records: int | None = None,
) -> Iterator[dict[str, Any]]:
    """Stream all JSONL records from a local datafile root.

    Parameters
    ----------
    data_dir:
        Root of an extracted monthly/public datafile (contains ``dois/`` or
        partition dirs directly).
    partitions:
        Optional list of partition names (e.g. ``updated_2025-11``) to limit scan.
    max_records:
        Stop after this many records (useful for agent timeouts / sampling).
    """
    data_dir = Path(data_dir)
    found = discover_partitions(data_dir)

    if not found:
        # Flat: jsonl parts directly under data_dir
        parts = discover_jsonl_parts(data_dir)
        if parts:
            count = 0
            for part in parts:
                for record in iter_jsonl_file(part):
                    yield record
                    count += 1
                    if max_records is not None and count >= max_records:
                        return
            return
        raise FileNotFoundError(
            f"No DataCite partitions or JSONL parts found under {data_dir}. "
            "Expected dois/updated_YYYY-MM/part_*.jsonl.gz"
        )

    if partitions:
        wanted = set(partitions)
        found = [p for p in found if p.name in wanted]
        if not found:
            raise FileNotFoundError(f"Requested partitions not found: {partitions}")

    count = 0
    for partition in found:
        for part in discover_jsonl_parts(partition):
            for record in iter_jsonl_file(part):
                yield record
                count += 1
                if max_records is not None and count >= max_records:
                    return


def load_status_json(data_dir: Path | str) -> dict[str, Any] | None:
    """Load STATUS.json from a datafile root if present."""
    path = Path(data_dir) / "STATUS.json"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def load_manifest_json(data_dir: Path | str) -> list[dict[str, Any]] | None:
    """Load MANIFEST.json from a datafile root if present."""
    path = Path(data_dir) / "MANIFEST.json"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, list):
        return data
    return None


def count_records_streaming(data_dir: Path | str, max_scan: int | None = 100_000) -> int:
    """Count records by streaming (capped for safety unless max_scan is None)."""
    n = 0
    for _ in iter_corpus_records(data_dir, max_records=max_scan):
        n += 1
    return n