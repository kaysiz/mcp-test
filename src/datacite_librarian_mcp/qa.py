"""Repository QA checks for DataCite DOI metadata.

Checks target common librarian concerns: required fields, PIDs (ORCID/ROR),
licenses, descriptions, relations, controlled vocabulary hygiene, and
basic funder completeness on individual records.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from .models import (
    CheckCategory,
    QaIssue,
    RepositoryHealthReport,
    Severity,
    extract_attributes,
    extract_relationships,
    record_to_summary,
)
from .util import doi_matches_prefix

# Core resource types from DataCite Metadata Schema (subset used for validation)
KNOWN_RESOURCE_TYPES_GENERAL = {
    "Audiovisual",
    "Award",
    "Book",
    "BookChapter",
    "Collection",
    "ComputationalNotebook",
    "ConferencePaper",
    "ConferenceProceeding",
    "DataPaper",
    "Dataset",
    "Dissertation",
    "Event",
    "Image",
    "Instrument",
    "InteractiveResource",
    "Journal",
    "JournalArticle",
    "Model",
    "OutputManagementPlan",
    "PeerReview",
    "PhysicalObject",
    "Poster",
    "Preprint",
    "Project",
    "Report",
    "Service",
    "Software",
    "Sound",
    "Standard",
    "StudyRegistration",
    "Text",
    "Workflow",
    "Other",
}


def _client_id_from_record(record: dict[str, Any]) -> str | None:
    rels = extract_relationships(record)
    client = rels.get("client") or {}
    if isinstance(client, dict):
        data = client.get("data") or {}
        if data.get("id"):
            return str(data["id"])
    attrs = extract_attributes(record)
    return attrs.get("clientId") or attrs.get("client_id")


def _publisher_name(attrs: dict[str, Any]) -> str | None:
    publisher = attrs.get("publisher")
    if isinstance(publisher, dict):
        return publisher.get("name")
    if isinstance(publisher, str):
        return publisher
    return None


def check_record(record: dict[str, Any]) -> list[QaIssue]:
    """Run all QA checks on a single DataCite record; return issues found."""
    attrs = extract_attributes(record)
    issues: list[QaIssue] = []

    doi = str(attrs.get("doi") or (record.get("data") or {}).get("id") or "unknown")

    # --- Required / core metadata ---
    titles = attrs.get("titles") or []
    if not titles:
        issues.append(
            QaIssue(
                doi=doi,
                category=CheckCategory.REQUIRED_METADATA,
                severity=Severity.ERROR,
                code="missing_title",
                message="No title present",
                field="titles",
                suggestion="Add at least one title (DataCite mandatory field).",
            )
        )

    creators = attrs.get("creators") or []
    if not creators:
        issues.append(
            QaIssue(
                doi=doi,
                category=CheckCategory.REQUIRED_METADATA,
                severity=Severity.ERROR,
                code="missing_creators",
                message="No creators present",
                field="creators",
                suggestion="Add at least one creator (DataCite mandatory field).",
            )
        )

    if not attrs.get("publicationYear"):
        issues.append(
            QaIssue(
                doi=doi,
                category=CheckCategory.REQUIRED_METADATA,
                severity=Severity.ERROR,
                code="missing_publication_year",
                message="Missing publicationYear",
                field="publicationYear",
            )
        )

    if not _publisher_name(attrs):
        issues.append(
            QaIssue(
                doi=doi,
                category=CheckCategory.REQUIRED_METADATA,
                severity=Severity.ERROR,
                code="missing_publisher",
                message="Missing publisher",
                field="publisher",
            )
        )

    types = attrs.get("types") or {}
    rtg = types.get("resourceTypeGeneral") if isinstance(types, dict) else None
    if not rtg:
        issues.append(
            QaIssue(
                doi=doi,
                category=CheckCategory.REQUIRED_METADATA,
                severity=Severity.ERROR,
                code="missing_resource_type_general",
                message="Missing types.resourceTypeGeneral",
                field="types.resourceTypeGeneral",
            )
        )
    elif rtg not in KNOWN_RESOURCE_TYPES_GENERAL:
        issues.append(
            QaIssue(
                doi=doi,
                category=CheckCategory.CONTROLLED_VOCAB,
                severity=Severity.WARNING,
                code="unknown_resource_type_general",
                message=f"resourceTypeGeneral '{rtg}' is not in the known controlled list",
                field="types.resourceTypeGeneral",
                suggestion="Verify against current DataCite Metadata Schema controlled list.",
            )
        )

    if not attrs.get("url"):
        issues.append(
            QaIssue(
                doi=doi,
                category=CheckCategory.REQUIRED_METADATA,
                severity=Severity.WARNING,
                code="missing_url",
                message="Missing landing page URL",
                field="url",
            )
        )

    # --- Identifiers (ORCID / ROR) ---
    if creators:
        any_orcid = False
        any_ror = False
        for creator in creators:
            if not isinstance(creator, dict):
                continue
            for nid in creator.get("nameIdentifiers") or []:
                if isinstance(nid, dict):
                    scheme = (nid.get("nameIdentifierScheme") or "").lower()
                    if "orcid" in scheme:
                        any_orcid = True
            for aff in creator.get("affiliation") or []:
                if isinstance(aff, dict):
                    scheme = (aff.get("affiliationIdentifierScheme") or "").lower()
                    if "ror" in scheme:
                        any_ror = True

        if not any_orcid:
            issues.append(
                QaIssue(
                    doi=doi,
                    category=CheckCategory.IDENTIFIERS,
                    severity=Severity.WARNING,
                    code="no_orcid_creators",
                    message="No creator has an ORCID nameIdentifier",
                    field="creators.nameIdentifiers",
                    suggestion="Encourage depositors to include ORCID iDs for creators.",
                )
            )
        if not any_ror:
            issues.append(
                QaIssue(
                    doi=doi,
                    category=CheckCategory.IDENTIFIERS,
                    severity=Severity.INFO,
                    code="no_ror_affiliation",
                    message="No creator affiliation includes a ROR identifier",
                    field="creators.affiliation",
                    suggestion="Map affiliations to ROR IDs where possible.",
                )
            )

    # --- Licensing ---
    rights = attrs.get("rightsList") or []
    if not rights:
        issues.append(
            QaIssue(
                doi=doi,
                category=CheckCategory.LICENSING,
                severity=Severity.WARNING,
                code="missing_license",
                message="No rightsList / license information",
                field="rightsList",
                suggestion="Add a license (e.g. CC0, CC-BY) for open access clarity.",
            )
        )
    else:
        for r in rights:
            if not isinstance(r, dict):
                continue
            if not r.get("rightsUri") and not r.get("rightsIdentifier"):
                issues.append(
                    QaIssue(
                        doi=doi,
                        category=CheckCategory.LICENSING,
                        severity=Severity.INFO,
                        code="license_missing_uri",
                        message="rightsList entry lacks rightsUri and rightsIdentifier",
                        field="rightsList",
                    )
                )
                break

    # --- Descriptive ---
    descriptions = attrs.get("descriptions") or []
    if not descriptions:
        issues.append(
            QaIssue(
                doi=doi,
                category=CheckCategory.DESCRIPTIVE,
                severity=Severity.WARNING,
                code="missing_description",
                message="No abstract/description",
                field="descriptions",
                suggestion="Add a Description with descriptionType Abstract where possible.",
            )
        )

    subjects = attrs.get("subjects") or []
    if not subjects:
        issues.append(
            QaIssue(
                doi=doi,
                category=CheckCategory.DESCRIPTIVE,
                severity=Severity.INFO,
                code="missing_subjects",
                message="No subjects/keywords",
                field="subjects",
            )
        )

    # --- Relations ---
    related = attrs.get("relatedIdentifiers") or []
    if not related:
        issues.append(
            QaIssue(
                doi=doi,
                category=CheckCategory.RELATIONS,
                severity=Severity.INFO,
                code="missing_related_identifiers",
                message="No relatedIdentifiers (versions, supplements, citations)",
                field="relatedIdentifiers",
                suggestion="Link papers, versions, and data supplements where applicable.",
            )
        )

    # --- Funding on record (light check; full compliance is in compliance.py) ---
    funding = attrs.get("fundingReferences") or []
    for fr in funding:
        if not isinstance(fr, dict):
            continue
        if not fr.get("funderName") and not fr.get("funderIdentifier"):
            issues.append(
                QaIssue(
                    doi=doi,
                    category=CheckCategory.FUNDING,
                    severity=Severity.WARNING,
                    code="funding_missing_funder",
                    message="fundingReference lacks funderName and funderIdentifier",
                    field="fundingReferences",
                )
            )
        if fr.get("funderName") and not fr.get("funderIdentifier"):
            issues.append(
                QaIssue(
                    doi=doi,
                    category=CheckCategory.FUNDING,
                    severity=Severity.INFO,
                    code="funding_missing_funder_id",
                    message=(
                        f"Funder '{fr.get('funderName')}' has no funderIdentifier "
                        "(Crossref Funder ID / ROR)"
                    ),
                    field="fundingReferences.funderIdentifier",
                )
            )

    # --- Geo (informational when resource type suggests spatial data) ---
    if rtg in {"Dataset", "Image", "Collection", "PhysicalObject"}:
        geo = attrs.get("geoLocations") or []
        if not geo:
            issues.append(
                QaIssue(
                    doi=doi,
                    category=CheckCategory.GEOLOCATION,
                    severity=Severity.INFO,
                    code="missing_geolocation",
                    message=f"No geoLocations for resource type {rtg}",
                    field="geoLocations",
                )
            )

    return issues


def scan_repository_health(
    records: Iterable[dict[str, Any]],
    *,
    client_id: str | None = None,
    prefix: str | None = None,
    max_records: int = 10_000,
    max_sample_issues: int = 50,
) -> RepositoryHealthReport:
    """Aggregate QA metrics over a streamed record iterator."""
    scope = "corpus"
    scope_value = "all"
    if client_id:
        scope = "client_id"
        scope_value = client_id
    elif prefix:
        scope = "prefix"
        scope_value = prefix

    records_examined = 0
    in_scope = 0
    truncated = False
    issue_counter: Counter[str] = Counter()
    severity_counter: Counter[str] = Counter()
    completeness_hits: Counter[str] = Counter()
    sample_issues: list[QaIssue] = []

    for record in records:
        records_examined += 1
        if records_examined > max_records:
            truncated = True
            records_examined -= 1  # last increment was the probe past the limit
            break

        summary = record_to_summary(record)
        attrs = extract_attributes(record)
        doi = summary.doi

        if client_id and summary.client_id != client_id:
            # Also try direct attribute match in case relationships missing
            if _client_id_from_record(record) != client_id:
                continue
        if prefix and not doi_matches_prefix(doi, prefix):
            continue

        in_scope += 1

        # Completeness trackers
        if summary.has_orcid:
            completeness_hits["orcid"] += 1
        if summary.has_ror:
            completeness_hits["ror"] += 1
        if summary.has_funder:
            completeness_hits["funder"] += 1
        if summary.has_license:
            completeness_hits["license"] += 1
        if summary.has_description:
            completeness_hits["description"] += 1
        if summary.has_geo:
            completeness_hits["geo"] += 1
        if summary.has_related:
            completeness_hits["related"] += 1
        if attrs.get("subjects"):
            completeness_hits["subjects"] += 1
        if summary.url:
            completeness_hits["url"] += 1

        for issue in check_record(record):
            issue_counter[issue.code] += 1
            severity_counter[issue.severity.value] += 1
            if len(sample_issues) < max_sample_issues:
                sample_issues.append(issue)

    # If the iterator was pre-capped externally at exactly max_records, we may not
    # observe the > max_records probe. Caller should pass an uncapped (or +1) stream
    # when possible; we still flag truncation when we examined exactly the limit
    # and the stream might continue (caller can pass stream_exhausted=False via
    # setting truncated if records_examined == max_records and more existed).
    # Handled below: if we hit the loop break via > max_records, truncated is True.
    # If the stream simply ended at max_records, truncated stays False unless
    # caller sets it; we set truncated when records_examined >= max_records and
    # we stopped because of the limit check (truncated already True) OR when
    # we processed exactly max_records without finishing (detected only via break).

    denom = in_scope or 1
    completeness = {
        key: round(completeness_hits.get(key, 0) / denom * 100, 1)
        for key in (
            "orcid",
            "ror",
            "funder",
            "license",
            "description",
            "geo",
            "related",
            "subjects",
            "url",
        )
    }

    top_issues = [
        {"code": code, "count": count}
        for code, count in issue_counter.most_common(15)
    ]

    return RepositoryHealthReport(
        scope=scope,
        scope_value=scope_value,
        total_dois=in_scope,
        scanned=in_scope,
        records_examined=records_examined,
        scan_limit=max_records,
        truncated=truncated,
        issue_counts=dict(issue_counter),
        severity_counts=dict(severity_counter),
        completeness=completeness,
        top_issues=top_issues,
        sample_issues=sample_issues,
    )