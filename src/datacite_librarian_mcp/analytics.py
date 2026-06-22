"""Aggregate analytics over streamed JSONL metadata records."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from .models import extract_attributes, extract_relationships, record_to_summary
from .util import doi_matches_prefix


def _client_id(record: dict[str, Any]) -> str | None:
    rels = extract_relationships(record)
    client = rels.get("client") or {}
    if isinstance(client, dict):
        data = client.get("data") or {}
        if data.get("id"):
            return str(data["id"])
    attrs = extract_attributes(record)
    return attrs.get("clientId") or attrs.get("client_id")


def facet_corpus(
    records: Iterable[dict[str, Any]],
    *,
    max_records: int = 10_000,
    top_n: int = 20,
    client_id: str | None = None,
    prefix: str | None = None,
) -> dict[str, Any]:
    """Facet counts: resource type, year, publisher, language, state, clients."""
    records_examined = 0
    in_scope = 0
    truncated = False
    types: Counter[str] = Counter()
    years: Counter[str] = Counter()
    publishers: Counter[str] = Counter()
    languages: Counter[str] = Counter()
    states: Counter[str] = Counter()
    clients: Counter[str] = Counter()
    with_orcid = with_funder = with_license = with_desc = with_geo = with_rel = 0

    for record in records:
        records_examined += 1
        if records_examined > max_records:
            truncated = True
            records_examined -= 1
            break

        summary = record_to_summary(record)
        if client_id and summary.client_id != client_id and _client_id(record) != client_id:
            continue
        if prefix and not doi_matches_prefix(summary.doi, prefix):
            continue

        in_scope += 1
        attrs = extract_attributes(record)
        types[summary.resource_type_general or "(missing)"] += 1
        years[str(summary.publication_year or "(missing)")] += 1
        publishers[summary.publisher or "(missing)"] += 1
        languages[attrs.get("language") or "(missing)"] += 1
        states[summary.state or "(missing)"] += 1
        clients[summary.client_id or "(unknown)"] += 1
        if summary.has_orcid:
            with_orcid += 1
        if summary.has_funder:
            with_funder += 1
        if summary.has_license:
            with_license += 1
        if summary.has_description:
            with_desc += 1
        if summary.has_geo:
            with_geo += 1
        if summary.has_related:
            with_rel += 1

    denom = in_scope or 1
    return {
        "in_scope": in_scope,
        "records_examined": records_examined,
        "scan_limit": max_records,
        "truncated": truncated,
        "resource_types": [{"value": k, "count": v} for k, v in types.most_common(top_n)],
        "publication_years": [{"value": k, "count": v} for k, v in years.most_common(top_n)],
        "publishers": [{"value": k, "count": v} for k, v in publishers.most_common(top_n)],
        "languages": [{"value": k, "count": v} for k, v in languages.most_common(top_n)],
        "states": [{"value": k, "count": v} for k, v in states.most_common()],
        "clients": [{"client_id": k, "count": v} for k, v in clients.most_common(top_n)],
        "rates_pct": {
            "orcid": round(100 * with_orcid / denom, 1),
            "funder": round(100 * with_funder / denom, 1),
            "license": round(100 * with_license / denom, 1),
            "description": round(100 * with_desc / denom, 1),
            "geo": round(100 * with_geo / denom, 1),
            "related": round(100 * with_rel / denom, 1),
        },
    }


def collect_metadata_dois(
    records: Iterable[dict[str, Any]],
    *,
    max_records: int | None = None,
) -> set[str]:
    """Collect DOI strings from a record stream (for index coverage compare)."""
    out: set[str] = set()
    n = 0
    for record in records:
        n += 1
        if max_records is not None and n > max_records:
            break
        s = record_to_summary(record)
        if s.doi and s.doi != "unknown":
            out.add(s.doi)
    return out


def top_subjects(
    records: Iterable[dict[str, Any]],
    *,
    max_records: int = 10_000,
    top_n: int = 30,
) -> dict[str, Any]:
    """Most common subject strings in metadata."""
    subjects: Counter[str] = Counter()
    examined = 0
    truncated = False
    for record in records:
        examined += 1
        if examined > max_records:
            truncated = True
            examined -= 1
            break
        attrs = extract_attributes(record)
        for sub in attrs.get("subjects") or []:
            if isinstance(sub, dict):
                s = sub.get("subject")
                if s:
                    subjects[str(s)] += 1
            elif sub:
                subjects[str(sub)] += 1
    return {
        "records_examined": examined,
        "truncated": truncated,
        "top_subjects": [{"subject": k, "count": v} for k, v in subjects.most_common(top_n)],
    }