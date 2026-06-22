"""Funder compliance analysis over streamed DataCite records.

Librarians and research offices use this to answer:
- Which outputs acknowledge funder X or award Y?
- How complete are fundingReferences (funder ID, award number/title)?
- Are licensed / ORCID-enriched outputs associated with funded work?
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import (
    CheckCategory,
    FunderComplianceReport,
    QaIssue,
    Severity,
    extract_attributes,
    record_to_summary,
)


def _funding_list(attrs: dict[str, Any]) -> list[dict[str, Any]]:
    fr = attrs.get("fundingReferences") or []
    return [x for x in fr if isinstance(x, dict)]


def _matches_funder(fr: dict[str, Any], query: str) -> bool:
    q = query.lower().strip()
    name = (fr.get("funderName") or "").lower()
    fid = (fr.get("funderIdentifier") or "").lower()
    return q in name or q in fid


def _matches_award(fr: dict[str, Any], query: str) -> bool:
    q = query.lower().strip()
    award = (fr.get("awardNumber") or "").lower()
    title = (fr.get("awardTitle") or "").lower()
    uri = (fr.get("awardUri") or "").lower()
    return q in award or q in title or q in uri


def _entry_matches_filters(
    fr: dict[str, Any],
    *,
    funder_query: str | None,
    award_query: str | None,
) -> bool:
    """True if this fundingReference entry satisfies the active filters."""
    if funder_query and not _matches_funder(fr, funder_query):
        return False
    if award_query and not _matches_award(fr, award_query):
        return False
    return True


def _record_matches_funding(
    attrs: dict[str, Any],
    *,
    funder_query: str | None,
    award_query: str | None,
) -> bool:
    funding = _funding_list(attrs)
    if not funder_query and not award_query:
        return bool(funding)

    return any(
        _entry_matches_filters(fr, funder_query=funder_query, award_query=award_query)
        for fr in funding
    )


def analyze_funder_compliance(
    records: Iterable[dict[str, Any]],
    *,
    funder_query: str | None = None,
    award_query: str | None = None,
    client_id: str | None = None,
    max_records: int = 10_000,
    max_issues: int = 80,
    max_sample_dois: int = 25,
) -> FunderComplianceReport:
    """Scan streamed records for funder/award compliance signals."""
    records_examined = 0
    matching = 0
    truncated = False
    with_funder_id = 0
    with_award_number = 0
    with_award_title = 0
    with_license = 0
    with_orcid = 0
    incomplete = 0
    funders_seen: set[str] = set()
    awards_seen: set[str] = set()
    issues: list[QaIssue] = []
    sample_dois = []

    for record in records:
        records_examined += 1
        if records_examined > max_records:
            truncated = True
            records_examined -= 1
            break

        attrs = extract_attributes(record)
        summary = record_to_summary(record)

        if client_id and summary.client_id != client_id:
            continue

        if not _record_matches_funding(attrs, funder_query=funder_query, award_query=award_query):
            continue

        matching += 1
        if len(sample_dois) < max_sample_dois:
            sample_dois.append(summary)

        if summary.has_license:
            with_license += 1
        if summary.has_orcid:
            with_orcid += 1

        funding = _funding_list(attrs)
        # Only analyze entries that match the same filters as record selection
        relevant = [
            fr
            for fr in funding
            if _entry_matches_filters(fr, funder_query=funder_query, award_query=award_query)
        ]
        # When no funder/award filter, analyze all funding entries on the record
        if not funder_query and not award_query:
            relevant = funding

        record_incomplete = False

        if not relevant:
            record_incomplete = True
            if len(issues) < max_issues:
                issues.append(
                    QaIssue(
                        doi=summary.doi,
                        category=CheckCategory.FUNDING,
                        severity=Severity.ERROR,
                        code="no_funding_references",
                        message="Matched scope but no fundingReferences on record",
                        field="fundingReferences",
                    )
                )
        else:
            any_funder_id = False
            any_award_number = False
            any_award_title = False

            for fr in relevant:
                fname = fr.get("funderName")
                if fname:
                    funders_seen.add(str(fname))
                fid = fr.get("funderIdentifier")
                if fid:
                    any_funder_id = True
                    funders_seen.add(str(fid))
                elif fname and len(issues) < max_issues:
                    issues.append(
                        QaIssue(
                            doi=summary.doi,
                            category=CheckCategory.FUNDING,
                            severity=Severity.WARNING,
                            code="missing_funder_identifier",
                            message=f"Funder '{fname}' lacks funderIdentifier",
                            field="fundingReferences.funderIdentifier",
                            suggestion="Add Crossref Funder Registry ID or ROR for the funder.",
                        )
                    )
                    record_incomplete = True

                award_no = fr.get("awardNumber")
                if award_no:
                    any_award_number = True
                    awards_seen.add(str(award_no))
                award_title = fr.get("awardTitle")
                if award_title:
                    any_award_title = True
                    awards_seen.add(str(award_title))

                if not award_no and not award_title and len(issues) < max_issues:
                    issues.append(
                        QaIssue(
                            doi=summary.doi,
                            category=CheckCategory.FUNDING,
                            severity=Severity.INFO,
                            code="missing_award_details",
                            message=(
                                f"Funding entry for '{fname or fid or 'unknown'}' "
                                "lacks awardNumber and awardTitle"
                            ),
                            field="fundingReferences",
                        )
                    )
                    record_incomplete = True

            if any_funder_id:
                with_funder_id += 1
            if any_award_number:
                with_award_number += 1
            if any_award_title:
                with_award_title += 1

        if record_incomplete:
            incomplete += 1

        if not summary.has_license and len(issues) < max_issues:
            issues.append(
                QaIssue(
                    doi=summary.doi,
                    category=CheckCategory.LICENSING,
                    severity=Severity.WARNING,
                    code="funded_output_missing_license",
                    message="Funded output has no rightsList/license",
                    field="rightsList",
                    suggestion="Many funders require open licenses; add rights metadata.",
                )
            )

        if not summary.has_orcid and len(issues) < max_issues:
            issues.append(
                QaIssue(
                    doi=summary.doi,
                    category=CheckCategory.IDENTIFIERS,
                    severity=Severity.INFO,
                    code="funded_output_missing_orcid",
                    message="Funded output has no ORCID on creators",
                    field="creators.nameIdentifiers",
                )
            )

    return FunderComplianceReport(
        funder_query=funder_query,
        award_query=award_query,
        total_matching_dois=matching,
        scanned=records_examined,
        records_examined=records_examined,
        scan_limit=max_records,
        truncated=truncated,
        dois_with_funder_id=with_funder_id,
        dois_with_award_number=with_award_number,
        dois_with_award_title=with_award_title,
        dois_with_license=with_license,
        dois_with_orcid_creators=with_orcid,
        incomplete_funding_records=incomplete,
        funders_seen=sorted(funders_seen)[:50],
        awards_seen=sorted(awards_seen)[:50],
        issues=issues,
        sample_dois=sample_dois,
    )