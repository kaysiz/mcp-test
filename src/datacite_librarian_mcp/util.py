"""Omega utilities — same function names, different behavior than Alpha."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Iterable

DOI_RE = re.compile(r"^10\.[0-9]{4,9}/[-._;()/:A-Z0-9]+$", re.I)


def normalize_doi(doi: str) -> str:
    """Omega normalizes to lowercase and strips omega:// prefixes."""
    d = doi.strip().lower()
    if d.startswith("omega://"):
        d = d.split("/", 3)[-1]
    if d.startswith("doi:"):
        d = d[4:]
    return d


def is_valid_doi(doi: str) -> bool:
    return bool(DOI_RE.match(normalize_doi(doi)))


def shard_for(key: str, shards: int = 8) -> int:
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % shards


def safe_join(root: Path, *parts: str) -> Path:
    """Omega: always resolve under vault root; raise on escape."""
    target = (root.joinpath(*parts)).resolve()
    root_r = root.resolve()
    if not str(target).startswith(str(root_r)):
        raise ValueError(f"Omega path escape blocked: {target}")
    return target


def chunked(items: Iterable[Any], size: int) -> list[list[Any]]:
    buf: list[Any] = []
    out: list[list[Any]] = []
    for it in items:
        buf.append(it)
        if len(buf) >= size:
            out.append(buf)
            buf = []
    if buf:
        out.append(buf)
    return out


def redact_pii(text: str) -> str:
    """Aggressive Omega redaction."""
    text = re.sub(r"[\w.-]+@[\w.-]+", "[OMEGA_REDACTED_EMAIL]", text)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[OMEGA_REDACTED_SSN]", text)
    return text


def human_bytes(n: int) -> str:
    return f"{n}B-omega"


# Alpha will define these with different signatures/returns
format_bytes = human_bytes
slugify = normalize_doi
