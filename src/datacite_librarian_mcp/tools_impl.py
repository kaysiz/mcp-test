"""Shared tool implementations (used by FastMCP server and tests).

Keeps ``server.py`` thinner and avoids circular imports.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from .analytics import collect_metadata_dois, facet_corpus, top_subjects
from .compliance import analyze_funder_compliance
from .config import DataDirError, get_data_dir, get_default_max_records, get_doi_lookup_max_scan
from .corpus import build_corpus_inventory, resolve_csv_path
from .export_util import export_issues_csv, export_json, export_summaries_csv
from .index_analytics import (
    compare_index_to_metadata_coverage,
    index_client_detail,
    summarize_index,
)
from .models import CorpusStatus, extract_attributes, record_to_summary
from .qa import check_record, scan_repository_health
from .stream_reader import iter_corpus_records, load_manifest_json, load_status_json
from .util import doi_matches_prefix


def data_dir_result() -> tuple[Path | None, dict[str, Any] | None]:
    try:
        return get_data_dir(), None
    except DataDirError as exc:
        return None, {
            "error": "invalid_data_dir",
            "message": str(exc),
            "requested_path": str(exc.requested),
            "hint": (
                "Fix DATACITE_DATA_DIR, extract the datafile to that path, "
                "unset the variable for mock data, or set DATACITE_USE_MOCK=1."
            ),
        }


def cap_records(max_records: int | None) -> int:
    default = get_default_max_records()
    if max_records is None:
        return default
    return max(1, min(max_records, default * 50))


def stream_with_limit(
    data_dir: Path, limit: int, partitions: list[str] | None = None
) -> tuple[Iterator[dict[str, Any]], list[bool]]:
    truncated_box = [False]

    def gen() -> Iterator[dict[str, Any]]:
        count = 0
        for record in iter_corpus_records(data_dir, partitions=partitions, max_records=None):
            count += 1
            if count <= limit:
                yield record
            else:
                truncated_box[0] = True
                return

    return gen(), truncated_box


def build_corpus_status() -> CorpusStatus:
    data_dir, err = data_dir_result()
    if err:
        return CorpusStatus(
            data_dir=err.get("requested_path") or "",
            exists=False,
            mode="error",
            status_file=None,
            partitions=[],
            part_files=0,
            estimated_records=None,
            notes=[err["message"], err.get("hint", "")],
        )

    assert data_dir is not None
    inv = build_corpus_inventory(data_dir)
    exists = data_dir.exists()
    status = load_status_json(data_dir) if exists else None
    partitions = [p["name"] for p in inv.get("partitions", [])]
    part_files = inv.get("jsonl_part_count", 0)

    mode = "mock"
    if status and status.get("mode") == "mock":
        mode = "mock"
    elif exists:
        mode = "local-datafile"

    notes = list(inv.get("notes") or [])
    if mode == "mock":
        notes.append(
            "Using mock corpus. Set DATACITE_DATA_DIR for production QA."
        )
    manifest = load_manifest_json(data_dir) if exists else None
    if manifest:
        notes.append(f"MANIFEST.json lists {len(manifest)} entries.")
    caps = inv.get("capabilities") or {}
    notes.append(
        "Capabilities: "
        + ", ".join(f"{k}={'yes' if v else 'no'}" for k, v in caps.items())
    )

    return CorpusStatus(
        data_dir=str(data_dir),
        exists=exists,
        mode=mode,
        status_file=status,
        partitions=partitions,
        part_files=part_files,
        estimated_records=None,
        notes=notes,
    )


def tool_corpus_inventory() -> dict[str, Any]:
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None
    return build_corpus_inventory(data_dir)


def tool_search_dois(
    query: str | None = None,
    client_id: str | None = None,
    prefix: str | None = None,
    resource_type_general: str | None = None,
    has_funder: bool | None = None,
    has_license: bool | None = None,
    has_orcid: bool | None = None,
    has_geo: bool | None = None,
    funder_contains: str | None = None,
    subject_contains: str | None = None,
    publication_year: int | str | None = None,
    max_results: int = 25,
    max_scan: int | None = None,
    partitions: list[str] | None = None,
) -> dict[str, Any]:
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None

    scan_limit = cap_records(max_scan)
    stream, truncated_box = stream_with_limit(data_dir, scan_limit, partitions)
    results: list[dict[str, Any]] = []
    scanned = 0
    q = (query or "").lower().strip() or None
    rtg_filter = (resource_type_general or "").strip() or None
    funder_q = (funder_contains or "").lower().strip() or None
    subj_q = (subject_contains or "").lower().strip() or None
    year_s = str(publication_year) if publication_year is not None else None

    for record in stream:
        scanned += 1
        summary = record_to_summary(record)
        attrs = extract_attributes(record)

        if client_id and summary.client_id != client_id:
            continue
        if prefix and not doi_matches_prefix(summary.doi, prefix):
            continue
        if rtg_filter and (summary.resource_type_general or "") != rtg_filter:
            continue
        if has_funder is not None and summary.has_funder != has_funder:
            continue
        if has_license is not None and summary.has_license != has_license:
            continue
        if has_orcid is not None and summary.has_orcid != has_orcid:
            continue
        if has_geo is not None and summary.has_geo != has_geo:
            continue
        if year_s and str(summary.publication_year) != year_s:
            continue
        if funder_q:
            funding = attrs.get("fundingReferences") or []
            hit = False
            for fr in funding:
                if not isinstance(fr, dict):
                    continue
                blob = f"{fr.get('funderName', '')} {fr.get('funderIdentifier', '')}".lower()
                if funder_q in blob:
                    hit = True
                    break
            if not hit:
                continue
        if subj_q:
            subjects = attrs.get("subjects") or []
            hit = False
            for sub in subjects:
                if isinstance(sub, dict):
                    if subj_q in (sub.get("subject") or "").lower():
                        hit = True
                        break
                elif subj_q in str(sub).lower():
                    hit = True
                    break
            if not hit:
                continue
        if q:
            title = (summary.title or "").lower()
            desc_hit = False
            for d in attrs.get("descriptions") or []:
                if isinstance(d, dict) and q in (d.get("description") or "").lower():
                    desc_hit = True
                    break
            if q not in title and q not in summary.doi.lower() and not desc_hit:
                continue

        results.append(summary.model_dump())
        if len(results) >= max_results:
            break

    return {
        "data_dir": str(data_dir),
        "scanned": scanned,
        "scan_limit": scan_limit,
        "truncated": truncated_box[0],
        "returned": len(results),
        "results": results,
    }


def tool_get_doi(doi: str, max_scan: int | None = None) -> dict[str, Any]:
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None

    needle = doi.strip().removeprefix("https://doi.org/").removeprefix("http://doi.org/")
    if max_scan is not None:
        scan_limit: int | None = max(1, max_scan)
    else:
        scan_limit = get_doi_lookup_max_scan()

    scanned = 0
    for record in iter_corpus_records(data_dir, max_records=scan_limit):
        scanned += 1
        summary = record_to_summary(record)
        if summary.doi.lower() == needle.lower():
            issues = [i.model_dump() for i in check_record(record)]
            return {
                "found": True,
                "summary": summary.model_dump(),
                "issues": issues,
                "issue_count": len(issues),
                "raw_attributes_keys": sorted(extract_attributes(record).keys()),
                "records_scanned": scanned,
                "scan_limit": scan_limit,
                "truncated_scan": False,
            }

    truncated_scan = scan_limit is not None and scanned >= scan_limit
    return {
        "found": False,
        "doi": needle,
        "data_dir": str(data_dir),
        "records_scanned": scanned,
        "scan_limit": scan_limit,
        "truncated_scan": truncated_scan,
        "message": (
            f"DOI not found within scan of {scanned} records (limit={scan_limit})."
            if truncated_scan
            else f"DOI not present in local corpus (scanned {scanned} records)."
        ),
    }


def tool_repository_health(
    client_id: str | None = None,
    prefix: str | None = None,
    max_records: int | None = None,
    max_sample_issues: int = 40,
    partitions: list[str] | None = None,
) -> dict[str, Any]:
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None
    limit = cap_records(max_records)
    stream, truncated_box = stream_with_limit(data_dir, limit, partitions)
    report = scan_repository_health(
        stream,
        client_id=client_id,
        prefix=prefix,
        max_records=limit,
        max_sample_issues=max_sample_issues,
    )
    out = report.model_dump()
    if truncated_box[0]:
        out["truncated"] = True
    out["data_dir"] = str(data_dir)
    out["scan_limit"] = limit
    return out


def tool_funder_compliance(
    funder_query: str | None = None,
    award_query: str | None = None,
    client_id: str | None = None,
    max_records: int | None = None,
    max_issues: int = 60,
    partitions: list[str] | None = None,
) -> dict[str, Any]:
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None
    limit = cap_records(max_records)
    stream, truncated_box = stream_with_limit(data_dir, limit, partitions)
    report = analyze_funder_compliance(
        stream,
        funder_query=funder_query,
        award_query=award_query,
        client_id=client_id,
        max_records=limit,
        max_issues=max_issues,
    )
    out = report.model_dump()
    if truncated_box[0]:
        out["truncated"] = True
    out["data_dir"] = str(data_dir)
    out["scan_limit"] = limit
    return out


def tool_list_clients(max_scan: int | None = None) -> dict[str, Any]:
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None
    scan_limit = cap_records(max_scan)
    stream, truncated_box = stream_with_limit(data_dir, scan_limit)
    counts: dict[str, int] = {}
    scanned = 0
    for record in stream:
        scanned += 1
        summary = record_to_summary(record)
        key = summary.client_id or "(unknown)"
        counts[key] = counts.get(key, 0) + 1
    ranked = sorted(
        [{"client_id": k, "doi_count": v} for k, v in counts.items()],
        key=lambda x: (-x["doi_count"], x["client_id"]),
    )
    return {
        "data_dir": str(data_dir),
        "scanned": scanned,
        "scan_limit": scan_limit,
        "truncated": truncated_box[0],
        "clients": ranked,
    }


def tool_list_funders(max_scan: int | None = None, limit: int = 50) -> dict[str, Any]:
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None
    scan_limit = cap_records(max_scan)
    stream, truncated_box = stream_with_limit(data_dir, scan_limit)
    counts: dict[str, int] = {}
    scanned = 0
    for record in stream:
        scanned += 1
        attrs = extract_attributes(record)
        for fr in attrs.get("fundingReferences") or []:
            if not isinstance(fr, dict):
                continue
            name = fr.get("funderName") or fr.get("funderIdentifier") or "(unnamed funder)"
            counts[str(name)] = counts.get(str(name), 0) + 1
    ranked = sorted(
        [{"funder": k, "record_mentions": v} for k, v in counts.items()],
        key=lambda x: (-x["record_mentions"], x["funder"]),
    )[:limit]
    return {
        "data_dir": str(data_dir),
        "scanned": scanned,
        "scan_limit": scan_limit,
        "truncated": truncated_box[0],
        "funders": ranked,
    }


def tool_facets(
    client_id: str | None = None,
    prefix: str | None = None,
    max_records: int | None = None,
    top_n: int = 20,
) -> dict[str, Any]:
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None
    limit = cap_records(max_records)
    stream, truncated_box = stream_with_limit(data_dir, limit)
    out = facet_corpus(
        stream, max_records=limit, top_n=top_n, client_id=client_id, prefix=prefix
    )
    if truncated_box[0]:
        out["truncated"] = True
    out["data_dir"] = str(data_dir)
    return out


def tool_subjects(max_records: int | None = None, top_n: int = 30) -> dict[str, Any]:
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None
    limit = cap_records(max_records)
    stream, truncated_box = stream_with_limit(data_dir, limit)
    out = top_subjects(stream, max_records=limit, top_n=top_n)
    if truncated_box[0]:
        out["truncated"] = True
    out["data_dir"] = str(data_dir)
    return out


def tool_index_summary(
    month: str | None = None,
    csv_path: str | None = None,
    max_rows: int | None = None,
    top_n: int = 25,
) -> dict[str, Any]:
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None
    path = resolve_csv_path(data_dir, month=month, path=csv_path)
    if not path:
        return {
            "error": "no_csv_index",
            "message": "No CSV index found. Add YYYY-MM.csv.gz or set month/path.",
            "data_dir": str(data_dir),
        }
    # Large indexes: default scan all unless capped
    limit = max_rows
    if limit is None:
        limit = None  # full file
    out = summarize_index(path, max_rows=limit, top_n=top_n)
    out["data_dir"] = str(data_dir)
    out["month"] = month
    return out


def tool_index_client(
    client_id: str,
    month: str | None = None,
    csv_path: str | None = None,
) -> dict[str, Any]:
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None
    path = resolve_csv_path(data_dir, month=month, path=csv_path)
    if not path:
        return {"error": "no_csv_index", "message": "No CSV index found."}
    out = index_client_detail(path, client_id)
    out["data_dir"] = str(data_dir)
    return out


def tool_coverage_report(
    month: str | None = None,
    csv_path: str | None = None,
    max_metadata_scan: int | None = None,
    max_index_rows: int | None = None,
) -> dict[str, Any]:
    """Compare CSV index DOIs vs loaded JSONL metadata DOIs."""
    data_dir, err = data_dir_result()
    if err:
        return err
    assert data_dir is not None
    path = resolve_csv_path(data_dir, month=month, path=csv_path)
    if not path:
        return {"error": "no_csv_index", "message": "No CSV index found."}
    if max_metadata_scan is not None:
        meta_limit = max_metadata_scan
    else:
        meta_limit = get_default_max_records() * 5
    dois = collect_metadata_dois(iter_corpus_records(data_dir, max_records=meta_limit))
    out = compare_index_to_metadata_coverage(
        path, dois, max_index_rows=max_index_rows
    )
    out["data_dir"] = str(data_dir)
    out["metadata_scan_limit"] = meta_limit
    return out


def tool_export_health_issues(
    client_id: str | None = None,
    prefix: str | None = None,
    max_records: int | None = None,
    fmt: str = "csv",
) -> dict[str, Any]:
    report = tool_repository_health(
        client_id=client_id, prefix=prefix, max_records=max_records, max_sample_issues=10_000
    )
    if report.get("error"):
        return report
    data_dir, _ = data_dir_result()
    issues = report.get("sample_issues") or []
    if fmt == "json":
        meta = {k: report[k] for k in report if k != "sample_issues"}
        return export_json(
            {"report_meta": meta, "issues": issues},
            filename_prefix="health_issues",
            data_dir=data_dir,
        )
    return export_issues_csv(issues, filename_prefix="health_issues", data_dir=data_dir)


def tool_export_funder_issues(
    funder_query: str | None = None,
    award_query: str | None = None,
    max_records: int | None = None,
    fmt: str = "csv",
) -> dict[str, Any]:
    report = tool_funder_compliance(
        funder_query=funder_query,
        award_query=award_query,
        max_records=max_records,
        max_issues=10_000,
    )
    if report.get("error"):
        return report
    data_dir, _ = data_dir_result()
    issues = report.get("issues") or []
    if fmt == "json":
        return export_json(report, filename_prefix="funder_issues", data_dir=data_dir)
    return export_issues_csv(issues, filename_prefix="funder_issues", data_dir=data_dir)


def tool_export_search(
    query: str | None = None,
    client_id: str | None = None,
    max_results: int = 500,
    max_scan: int | None = None,
) -> dict[str, Any]:
    result = tool_search_dois(
        query=query, client_id=client_id, max_results=max_results, max_scan=max_scan
    )
    if result.get("error"):
        return result
    data_dir, _ = data_dir_result()
    return export_summaries_csv(
        result.get("results") or [], filename_prefix="search", data_dir=data_dir
    )


def tool_community_guide() -> dict[str, Any]:
    """Persona-oriented guide for agents and humans."""
    return {
        "title": "DataCite Librarian MCP — community use guide",
        "audiences": {
            "librarians_rdm": [
                "corpus_inventory / corpus_status — confirm what is loaded",
                "repository_health(client_id=…) — QA completeness & issues",
                "export_health_issues — CSV for depositor follow-up",
                "search_dois / get_doi / check_doi_qa — inspect deposits",
            ],
            "research_offices": [
                "funder_compliance(funder_query=…, award_query=…)",
                "export_funder_issues — grants office workflow",
                "list_funders — portfolio overview",
            ],
            "repository_operators": [
                "index_summary / index_client — monthly index without full JSONL",
                "coverage_report — how much metadata you have vs index",
                "facets — types, years, licenses rates",
            ],
            "bibliometrics_policy": [
                "facets / top_subjects — exploratory counts (respect truncated)",
                "index_summary on full month CSV for scale stats",
                "Always report scan_limit/truncated/coverage_pct",
            ],
            "developers_integrators": [
                "server_info / community_guide — capabilities",
                "Mock corpus when DATACITE_DATA_DIR unset",
                "Stream-only design: no DB required",
            ],
            "teachers_trainers": [
                "Mock data or one part file for demos",
                "NL chat: datacite-librarian-chat",
                "Compare empty vs rich metadata patterns",
            ],
        },
        "data_layouts": {
            "recommended": "dois/updated_YYYY-MM/part_*.jsonl.gz + YYYY-MM.csv.gz",
            "also_supported": "Flat part_*.jsonl.gz and YYYY-MM.csv.gz in DATACITE_DATA_DIR",
        },
        "env": {
            "DATACITE_DATA_DIR": "corpus root",
            "DATACITE_MAX_RECORDS": "aggregate scan ceiling",
            "DATACITE_EXPORT_DIR": "where exports are written",
            "DATACITE_USE_MOCK": "force demo corpus",
        },
        "docs": {
            "public_file": "https://support.datacite.org/docs/datacite-public-data-file",
            "monthly_file": "https://support.datacite.org/docs/datacite-monthly-data-file",
            "portal": "https://datafiles.datacite.org",
        },
    }