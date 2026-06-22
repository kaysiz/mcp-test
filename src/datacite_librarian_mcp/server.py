"""FastMCP server: community toolkit over local DataCite monthly/public datafiles.

Audiences: librarians, RDM, research offices, repository operators, policy/bibliometrics,
developers, trainers. Stream-reads JSONL metadata and/or CSV indexes; optional exports.
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp import FastMCP

from . import __version__
from . import tools_impl as T
from .config import get_data_dir, get_default_max_records, get_doi_lookup_max_scan
from .corpus import resolve_export_dir
from .mock_data import default_mock_dir, write_mock_corpus
from .stream_reader import discover_jsonl_parts, discover_partitions, load_status_json

mcp = FastMCP(
    name="datacite-librarian",
    instructions=(
        "DataCite Librarian MCP — local, stream-first tools over monthly/public datafiles "
        "for repository QA, funder compliance, index analytics, search, facets, and exports. "
        "Start with corpus_inventory or community_guide. "
        "Set DATACITE_DATA_DIR to your extracted root (dois/updated_* or flat part_*.jsonl.gz + CSV). "
        "Aggregate tools respect DATACITE_MAX_RECORDS; always surface truncated/scan_limit/coverage. "
        "CSV index tools work without full JSONL. Export tools write under DATACITE_EXPORT_DIR or exports/."
    ),
)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("datacite://corpus/status")
def resource_corpus_status() -> str:
    return json.dumps(T.build_corpus_status().model_dump(), indent=2)


@mcp.resource("datacite://corpus/inventory")
def resource_corpus_inventory() -> str:
    return json.dumps(T.tool_corpus_inventory(), indent=2)


@mcp.resource("datacite://guide/community")
def resource_community_guide() -> str:
    return json.dumps(T.tool_community_guide(), indent=2)


@mcp.resource("datacite://schema/overview")
def resource_schema_overview() -> str:
    return """# DataCite datafile schema (overview)

## Layouts supported
1. Standard: data_root/dois/updated_YYYY-MM/{part_*.jsonl.gz, YYYY-MM.csv.gz}
2. Flat: data_root/part_*.jsonl.gz and data_root/YYYY-MM.csv.gz

## JSONL record
API singleton shape (flat id/type/attributes/relationships or wrapped in data).

## CSV index columns
doi, state, client_id, updated

See docs/DATAFILE_SCHEMA.md and community_guide tool.
"""


# ---------------------------------------------------------------------------
# Core / discovery
# ---------------------------------------------------------------------------


@mcp.tool
def community_guide() -> dict[str, Any]:
    """Persona-oriented guide: which tools to use for librarians, RDM, funders, ops, research, teaching."""
    return T.tool_community_guide()


@mcp.tool
def corpus_status() -> dict[str, Any]:
    """Quick status: path, mode, partitions, part count, capability notes."""
    return T.build_corpus_status().model_dump()


@mcp.tool
def corpus_inventory() -> dict[str, Any]:
    """Full inventory: layout type, partitions, loose CSV/JSONL, capabilities, gaps."""
    return T.tool_corpus_inventory()


@mcp.tool
def server_info() -> dict[str, Any]:
    """Version, paths, env vars, export dir, DataCite documentation links."""
    data_dir, err = T.data_dir_result()
    info: dict[str, Any] = {
        "name": "datacite-librarian-mcp",
        "version": __version__,
        "default_max_records": get_default_max_records(),
        "doi_lookup_max_scan": get_doi_lookup_max_scan(),
        "mock_dir": str(default_mock_dir()),
        "export_dir": str(resolve_export_dir(data_dir)),
        "env": {
            "DATACITE_DATA_DIR": "corpus root (must exist if set)",
            "DATACITE_USE_MOCK": "1 to force mock",
            "DATACITE_MOCK_DIR": "mock write location",
            "DATACITE_MAX_RECORDS": "aggregate scan ceiling",
            "DATACITE_DOI_LOOKUP_MAX_SCAN": "0=unlimited get_doi scan",
            "DATACITE_EXPORT_DIR": "export output directory",
        },
        "docs": T.tool_community_guide()["docs"],
        "tool_groups": [
            "discovery",
            "metadata_qa",
            "funder_compliance",
            "search",
            "analytics_facets",
            "csv_index",
            "coverage",
            "export",
        ],
    }
    if err:
        info["data_dir_error"] = err
        info["data_dir"] = None
    else:
        info["data_dir"] = str(data_dir)
    return info


@mcp.tool
def diff_partitions_summary() -> dict[str, Any]:
    """Summarize partitions and part files (metadata side)."""
    data_dir, err = T.data_dir_result()
    if err:
        return err
    assert data_dir is not None
    partitions = []
    for p in discover_partitions(data_dir):
        parts = discover_jsonl_parts(p)
        partitions.append(
            {"name": p.name, "path": str(p), "part_files": len(parts), "parts": [x.name for x in parts]}
        )
    return {
        "data_dir": str(data_dir),
        "partition_count": len(partitions),
        "partitions": partitions,
        "status": load_status_json(data_dir),
        "inventory_hint": "Use corpus_inventory for CSV + flat layout details.",
    }


# ---------------------------------------------------------------------------
# Metadata search & DOI
# ---------------------------------------------------------------------------


@mcp.tool
def search_dois(
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
) -> dict[str, Any]:
    """Search streamed JSONL metadata with rich filters (title/DOI/description, funder, subject, year, geo)."""
    return T.tool_search_dois(
        query=query,
        client_id=client_id,
        prefix=prefix,
        resource_type_general=resource_type_general,
        has_funder=has_funder,
        has_license=has_license,
        has_orcid=has_orcid,
        has_geo=has_geo,
        funder_contains=funder_contains,
        subject_contains=subject_contains,
        publication_year=publication_year,
        max_results=max_results,
        max_scan=max_scan,
    )


@mcp.tool
def get_doi(doi: str, max_scan: int | None = None) -> dict[str, Any]:
    """Lookup one DOI in local JSONL; returns summary + QA issues. Default full-corpus scan."""
    return T.tool_get_doi(doi, max_scan=max_scan)


@mcp.tool
def check_doi_qa(doi: str, max_scan: int | None = None) -> dict[str, Any]:
    """Full QA issue breakdown for one DOI."""
    result = T.tool_get_doi(doi, max_scan=max_scan)
    if result.get("error") or not result.get("found"):
        return result
    return {
        "doi": result["summary"]["doi"],
        "summary": result["summary"],
        "issues": result["issues"],
        "issue_count": result["issue_count"],
        "errors": sum(1 for i in result["issues"] if i["severity"] == "error"),
        "warnings": sum(1 for i in result["issues"] if i["severity"] == "warning"),
        "infos": sum(1 for i in result["issues"] if i["severity"] == "info"),
        "records_scanned": result.get("records_scanned"),
        "scan_limit": result.get("scan_limit"),
    }


# ---------------------------------------------------------------------------
# QA & compliance
# ---------------------------------------------------------------------------


@mcp.tool
def repository_health(
    client_id: str | None = None,
    prefix: str | None = None,
    max_records: int | None = None,
    max_sample_issues: int = 40,
) -> dict[str, Any]:
    """Aggregate repository QA: completeness rates, issue frequencies, samples. Scope by client_id or prefix."""
    return T.tool_repository_health(
        client_id=client_id,
        prefix=prefix,
        max_records=max_records,
        max_sample_issues=max_sample_issues,
    )


@mcp.tool
def funder_compliance(
    funder_query: str | None = None,
    award_query: str | None = None,
    client_id: str | None = None,
    max_records: int | None = None,
    max_issues: int = 60,
) -> dict[str, Any]:
    """Funder/award compliance: IDs, awards, licenses, ORCID; actionable issues."""
    return T.tool_funder_compliance(
        funder_query=funder_query,
        award_query=award_query,
        client_id=client_id,
        max_records=max_records,
        max_issues=max_issues,
    )


@mcp.tool
def list_clients(max_scan: int | None = None) -> dict[str, Any]:
    """Repository client_id counts from streamed metadata."""
    return T.tool_list_clients(max_scan=max_scan)


@mcp.tool
def list_funders(max_scan: int | None = None, limit: int = 50) -> dict[str, Any]:
    """Funder name/ID frequencies from fundingReferences in metadata."""
    return T.tool_list_funders(max_scan=max_scan, limit=limit)


# ---------------------------------------------------------------------------
# Analytics / facets
# ---------------------------------------------------------------------------


@mcp.tool
def facets(
    client_id: str | None = None,
    prefix: str | None = None,
    max_records: int | None = None,
    top_n: int = 20,
) -> dict[str, Any]:
    """Facet counts: resource types, years, publishers, languages, clients; rate % for ORCID/funder/license/etc."""
    return T.tool_facets(client_id=client_id, prefix=prefix, max_records=max_records, top_n=top_n)


@mcp.tool
def top_subjects(max_records: int | None = None, top_n: int = 30) -> dict[str, Any]:
    """Most common subject/keyword strings in metadata."""
    return T.tool_subjects(max_records=max_records, top_n=top_n)


# ---------------------------------------------------------------------------
# CSV index (no JSONL required)
# ---------------------------------------------------------------------------


@mcp.tool
def index_summary(
    month: str | None = None,
    csv_path: str | None = None,
    max_rows: int | None = None,
    top_n: int = 25,
) -> dict[str, Any]:
    """Summarize a monthly CSV index (doi/state/client_id/updated): totals, states, top clients/prefixes.

    Works without any JSONL — ideal for large months when you only have the index file.
    Pass month as YYYY-MM (e.g. 2026-06) or csv_path relative/absolute.
    """
    return T.tool_index_summary(month=month, csv_path=csv_path, max_rows=max_rows, top_n=top_n)


@mcp.tool
def index_client(
    client_id: str,
    month: str | None = None,
    csv_path: str | None = None,
) -> dict[str, Any]:
    """One repository's DOI count, states, prefixes, and sample rows from the CSV index only."""
    return T.tool_index_client(client_id=client_id, month=month, csv_path=csv_path)


@mcp.tool
def coverage_report(
    month: str | None = None,
    csv_path: str | None = None,
    max_metadata_scan: int | None = None,
    max_index_rows: int | None = None,
) -> dict[str, Any]:
    """Compare CSV index DOIs vs DOIs present in loaded JSONL parts (coverage gap / what to download next)."""
    return T.tool_coverage_report(
        month=month,
        csv_path=csv_path,
        max_metadata_scan=max_metadata_scan,
        max_index_rows=max_index_rows,
    )


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------


@mcp.tool
def export_health_issues(
    client_id: str | None = None,
    prefix: str | None = None,
    max_records: int | None = None,
    fmt: str = "csv",
) -> dict[str, Any]:
    """Run repository_health and write issues to exports/ (csv or json). Path returned for follow-up."""
    return T.tool_export_health_issues(
        client_id=client_id, prefix=prefix, max_records=max_records, fmt=fmt
    )


@mcp.tool
def export_funder_issues(
    funder_query: str | None = None,
    award_query: str | None = None,
    max_records: int | None = None,
    fmt: str = "csv",
) -> dict[str, Any]:
    """Run funder_compliance and export issues to exports/."""
    return T.tool_export_funder_issues(
        funder_query=funder_query,
        award_query=award_query,
        max_records=max_records,
        fmt=fmt,
    )


@mcp.tool
def export_search_results(
    query: str | None = None,
    client_id: str | None = None,
    max_results: int = 500,
    max_scan: int | None = None,
) -> dict[str, Any]:
    """Search DOIs and export matching summaries to CSV under exports/."""
    return T.tool_export_search(
        query=query, client_id=client_id, max_results=max_results, max_scan=max_scan
    )


# ---------------------------------------------------------------------------
# Ops
# ---------------------------------------------------------------------------


@mcp.tool
def regenerate_mock_data() -> dict[str, Any]:
    """Regenerate bundled/demo mock corpus."""
    path = write_mock_corpus(default_mock_dir())
    return {"ok": True, "path": str(path), "status": load_status_json(path)}


def main() -> None:
    try:
        get_data_dir()
    except Exception:
        pass
    mcp.run()


if __name__ == "__main__":
    main()