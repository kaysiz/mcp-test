"""Runtime configuration for the DataCite Librarian MCP."""

from __future__ import annotations

import os
from pathlib import Path

from .mock_data import default_mock_dir, ensure_mock_corpus


class DataDirError(FileNotFoundError):
    """Raised when DATACITE_DATA_DIR is set but missing or unreadable."""

    def __init__(self, requested: Path) -> None:
        self.requested = requested
        super().__init__(
            f"DATACITE_DATA_DIR is set to {requested} but that path does not exist. "
            "Create/extract the datafile there, fix the path, or unset DATACITE_DATA_DIR "
            "to use the mock corpus (or set DATACITE_USE_MOCK=1)."
        )


def get_data_dir() -> Path:
    """Resolve corpus directory from env, falling back to mock only when unset.

    Environment variables:
    - ``DATACITE_DATA_DIR`` — extracted monthly/public datafile root (must exist if set)
    - ``DATACITE_USE_MOCK`` — if ``1``/``true``, force mock corpus even if data dir set

    Raises
    ------
    DataDirError
        If ``DATACITE_DATA_DIR`` is explicitly set but the path is missing.
    """
    use_mock = os.environ.get("DATACITE_USE_MOCK", "").lower() in {"1", "true", "yes"}
    env_dir = os.environ.get("DATACITE_DATA_DIR")

    if use_mock or not env_dir:
        return ensure_mock_corpus(default_mock_dir())

    path = Path(env_dir).expanduser().resolve()
    if not path.exists():
        raise DataDirError(path)
    if not path.is_dir():
        raise DataDirError(path)
    return path


def get_default_max_records() -> int:
    """Default scan ceiling for agent-facing aggregate tools (override via env)."""
    raw = os.environ.get("DATACITE_MAX_RECORDS", "10000")
    try:
        return max(1, int(raw))
    except ValueError:
        return 10_000


def get_doi_lookup_max_scan() -> int | None:
    """Max records to scan for single-DOI lookup; ``None`` means unbounded.

    Override with ``DATACITE_DOI_LOOKUP_MAX_SCAN`` (integer, or ``0``/``unlimited``/``none``
    for full-corpus scan).
    """
    raw = os.environ.get("DATACITE_DOI_LOOKUP_MAX_SCAN", "0").strip().lower()
    if raw in {"", "0", "none", "unlimited", "inf"}:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return max(1, value) if value > 0 else None