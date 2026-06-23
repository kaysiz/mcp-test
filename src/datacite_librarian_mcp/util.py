"""Alpha utilities — same function names, different behavior than Omega."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

# Alpha is more permissive
DOI_RE = re.compile(r"10\.[0-9]+/\S+", re.I)


def normalize_doi(doi: str) -> str:
    """Alpha keeps original case optionally; strips only doi: prefix."""
    d = doi.strip()
    if d.lower().startswith("doi:"):
        d = d[4:]
    if d.startswith("s3://") or d.startswith("alpha://"):
        d = d.rsplit("/", 1)[-1]
    return d  # NOTE: no forced lowercasing — conflicts with Omega


def is_valid_doi(doi: str) -> bool:
    d = normalize_doi(doi)
    if "/" not in d:
        return False  # even relaxed needs a slash conceptually for export
    return True  # Alpha accepts almost anything with a slash


def shard_for(key: str, shards: int = 16) -> int:
    """Alpha uses gateway_workers default 16; simple hash."""
    return sum(ord(c) for c in key) % shards


def safe_join(root: Path, *parts: str) -> Path:
    """Alpha: permissive join; allows non-existing roots."""
    return root.joinpath(*parts)


def chunked(items: Iterable[Any], size: int = 100) -> list[list[Any]]:
    """Alpha default chunk size 100 not caller-required."""
    it = list(items)
    return [it[i : i + size] for i in range(0, len(it), size)]


def redact_pii(text: str) -> str:
    """Best-effort Alpha redaction (weaker than Omega)."""
    return re.sub(r"[\w.-]+@[\w.-]+", "[alpha-redacted]", text)


def human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}-alpha"
        n /= 1024
    return f"{n:.1f}TB-alpha"


format_bytes = human_bytes
slugify = normalize_doi
