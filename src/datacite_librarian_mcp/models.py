"""Lightweight Pydantic models for DataCite JSONL records and QA findings."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Severity(StrEnum):
    """Issue severity for repository QA and compliance checks."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CheckCategory(StrEnum):
    """High-level check categories librarians care about."""

    REQUIRED_METADATA = "required_metadata"
    IDENTIFIERS = "identifiers"
    FUNDING = "funding"
    LICENSING = "licensing"
    RELATIONS = "relations"
    DESCRIPTIVE = "descriptive"
    GEOLOCATION = "geolocation"
    CONTROLLED_VOCAB = "controlled_vocab"


class QaIssue(BaseModel):
    """A single QA or compliance finding for one DOI."""

    doi: str
    category: CheckCategory
    severity: Severity
    code: str
    message: str
    field: str | None = None
    suggestion: str | None = None


class DoiSummary(BaseModel):
    """Compact DOI summary suitable for agent responses."""

    doi: str
    title: str | None = None
    resource_type_general: str | None = None
    publication_year: int | str | None = None
    publisher: str | None = None
    client_id: str | None = None
    provider_id: str | None = None
    state: str | None = None
    url: str | None = None
    updated: str | None = None
    creator_count: int = 0
    has_orcid: bool = False
    has_ror: bool = False
    has_funder: bool = False
    has_license: bool = False
    has_description: bool = False
    has_geo: bool = False
    has_related: bool = False
    citation_count: int | None = None
    view_count: int | None = None
    download_count: int | None = None


class RepositoryHealthReport(BaseModel):
    """Aggregate health metrics for a repository (client_id) or prefix slice."""

    scope: str
    scope_value: str
    total_dois: int = 0  # in-scope / matching DOIs (same as scanned for scoped runs)
    scanned: int = 0  # alias: in-scope records analyzed
    records_examined: int = 0  # all stream rows read (includes out-of-scope skips)
    scan_limit: int | None = None
    truncated: bool = False
    issue_counts: dict[str, int] = Field(default_factory=dict)
    severity_counts: dict[str, int] = Field(default_factory=dict)
    completeness: dict[str, float] = Field(default_factory=dict)
    top_issues: list[dict[str, Any]] = Field(default_factory=list)
    sample_issues: list[QaIssue] = Field(default_factory=list)


class FunderComplianceReport(BaseModel):
    """Funder / award compliance summary for a corpus slice."""

    funder_query: str | None = None
    award_query: str | None = None
    total_matching_dois: int = 0
    scanned: int = 0  # stream rows examined (before/while applying funder filters)
    records_examined: int = 0
    scan_limit: int | None = None
    truncated: bool = False
    dois_with_funder_id: int = 0
    dois_with_award_number: int = 0
    dois_with_award_title: int = 0
    dois_with_license: int = 0
    dois_with_orcid_creators: int = 0
    incomplete_funding_records: int = 0
    funders_seen: list[str] = Field(default_factory=list)
    awards_seen: list[str] = Field(default_factory=list)
    issues: list[QaIssue] = Field(default_factory=list)
    sample_dois: list[DoiSummary] = Field(default_factory=list)


class CorpusStatus(BaseModel):
    """Status of the configured local datafile corpus."""

    data_dir: str
    exists: bool
    mode: str = "mock"
    status_file: dict[str, Any] | None = None
    partitions: list[str] = Field(default_factory=list)
    part_files: int = 0
    estimated_records: int | None = None
    notes: list[str] = Field(default_factory=list)


def extract_attributes(record: dict[str, Any]) -> dict[str, Any]:
    """Pull attributes from a DataCite REST-shaped or flat record."""
    if "data" in record and isinstance(record["data"], dict):
        data = record["data"]
        attrs = data.get("attributes") or {}
        if "doi" not in attrs and data.get("id"):
            attrs = {**attrs, "doi": data["id"]}
        return attrs
    if "attributes" in record:
        return record["attributes"] or {}
    return record


def extract_relationships(record: dict[str, Any]) -> dict[str, Any]:
    if "data" in record and isinstance(record["data"], dict):
        return record["data"].get("relationships") or {}
    return record.get("relationships") or {}


def record_to_summary(record: dict[str, Any]) -> DoiSummary:
    """Convert a raw DataCite JSONL record into a compact summary."""
    attrs = extract_attributes(record)
    rels = extract_relationships(record)

    titles = attrs.get("titles") or []
    title = None
    if titles and isinstance(titles, list):
        title = titles[0].get("title") if isinstance(titles[0], dict) else str(titles[0])

    types = attrs.get("types") or {}
    resource_type_general = types.get("resourceTypeGeneral") if isinstance(types, dict) else None

    publisher = attrs.get("publisher")
    if isinstance(publisher, dict):
        publisher_name = publisher.get("name")
    else:
        publisher_name = publisher

    creators = attrs.get("creators") or []
    has_orcid = False
    has_ror = False
    for creator in creators:
        if not isinstance(creator, dict):
            continue
        for nid in creator.get("nameIdentifiers") or []:
            if isinstance(nid, dict) and "orcid" in (nid.get("nameIdentifierScheme") or "").lower():
                has_orcid = True
        for aff in creator.get("affiliation") or []:
            if isinstance(aff, dict):
                scheme = (aff.get("affiliationIdentifierScheme") or "").lower()
                if "ror" in scheme:
                    has_ror = True

    funding = attrs.get("fundingReferences") or []
    rights = attrs.get("rightsList") or []
    descriptions = attrs.get("descriptions") or []
    geo = attrs.get("geoLocations") or []
    related = attrs.get("relatedIdentifiers") or []

    client_id = None
    provider_id = None
    if isinstance(rels.get("client"), dict):
        client_data = rels["client"].get("data") or {}
        client_id = client_data.get("id")
    if isinstance(rels.get("provider"), dict):
        provider_data = rels["provider"].get("data") or {}
        provider_id = provider_data.get("id")

    # Some exports embed client_id on attributes or top-level admin fields
    client_id = client_id or attrs.get("clientId") or attrs.get("client_id")
    provider_id = provider_id or attrs.get("providerId") or attrs.get("provider_id")

    doi = attrs.get("doi") or (record.get("data") or {}).get("id") or record.get("id") or "unknown"

    return DoiSummary(
        doi=str(doi),
        title=title,
        resource_type_general=resource_type_general,
        publication_year=attrs.get("publicationYear"),
        publisher=publisher_name,
        client_id=client_id,
        provider_id=provider_id,
        state=attrs.get("state"),
        url=attrs.get("url"),
        updated=attrs.get("updated"),
        creator_count=len(creators) if isinstance(creators, list) else 0,
        has_orcid=has_orcid,
        has_ror=has_ror,
        has_funder=bool(funding),
        has_license=bool(rights),
        has_description=bool(descriptions),
        has_geo=bool(geo),
        has_related=bool(related),
        citation_count=attrs.get("citationCount"),
        view_count=attrs.get("viewCount"),
        download_count=attrs.get("downloadCount"),
    )