"""Merged utilities — Omega-strict helpers + Alpha-permissive helpers."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable

DOI_RE_STRICT = re.compile(r"^10\.[0-9]{4,9}/[-._;()/:A-Z0-9]+$", re.I)
DOI_RE_RELAXED = re.compile(r"10\.[0-9]+/\S+", re.I)


def normalize_doi(doi: str, *, omega_style: bool = False) -> str:
    d = doi.strip()
    if d.lower().startswith("doi:"):
        d = d[4:]
    if d.startswith("omega://"):
        d = d.split("/", 3)[-1]
    if d.startswith("s3://") or d.startswith("alpha://"):
        d = d.rsplit("/", 1)[-1]
    return d.lower() if omega_style else d


def is_valid_doi(doi: str, *, strict: bool = False) -> bool:
    d = normalize_doi(doi, omega_style=strict)
    if strict:
        return bool(DOI_RE_STRICT.match(d))
    return "/" in d


def shard_for(key: str, shards: int = 8) -> int:
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % shards


def worker_for(key: str, workers: int = 16) -> int:
    return sum(ord(c) for c in key) % workers


def safe_join(root: Path, *parts: str, strict: bool = False) -> Path:
    target = (root.joinpath(*parts)).resolve() if strict else root.joinpath(*parts)
    if strict:
        root_r = root.resolve()
        if not str(target).startswith(str(root_r)):
            raise ValueError(f"Omega path escape blocked: {target}")
    return target


def chunked(items: Iterable[Any], size: int = 100) -> list[list[Any]]:
    it = list(items)
    return [it[i : i + size] for i in range(0, len(it), size)]


def redact_pii(text: str, *, aggressive: bool = False) -> str:
    if aggressive:
        text = re.sub(r"[\w.-]+@[\w.-]+", "[OMEGA_REDACTED_EMAIL]", text)
        text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[OMEGA_REDACTED_SSN]", text)
        return text
    return re.sub(r"[\w.-]+@[\w.-]+", "[alpha-redacted]", text)


def human_bytes(n: int, *, style: str = "merged") -> str:
    if style == "omega":
        return f"{n}B-omega"
    orig = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if orig < 1024:
            return f"{orig:.1f}{unit}-{style}"
        orig /= 1024
    return f"{orig:.1f}TB-{style}"


format_bytes = human_bytes
slugify = normalize_doi
