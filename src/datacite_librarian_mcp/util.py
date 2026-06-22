"""Shared helpers for DOI / corpus filtering."""

from __future__ import annotations


def doi_matches_prefix(doi: str, prefix: str | None) -> bool:
    """Return True if *doi* belongs to *prefix* (e.g. ``10.5281`` or ``10.5281/``).

    Accepts either a bare prefix (``10.5281``) or a prefix with trailing slash.
    Empty/None prefix matches everything.
    """
    if not prefix:
        return True
    p = prefix.strip()
    if not p:
        return True
    # Normalize: match both "10.5281/foo" and exact "10.5281" if that were a full DOI
    if doi == p or doi == p.rstrip("/"):
        return True
    base = p.rstrip("/")
    return doi.startswith(base + "/")