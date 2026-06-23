"""Omega server entry — FastMCP with Omega router middleware."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastmcp import FastMCP

from datacite_librarian_mcp.config import OmegaConfig, OmegaPolicyError, load_config
from datacite_librarian_mcp.tools_impl import OmegaTools

mcp = FastMCP("omega-datacite-librarian")

_cfg: OmegaConfig | None = None
_tools: OmegaTools | None = None


@dataclass
class OmegaResult:
    ok: bool
    payload: Any
    audit_id: str
    policy: str = "PII_ZERO"


def _boot() -> tuple[OmegaConfig, OmegaTools]:
    global _cfg, _tools
    if _cfg is None:
        _cfg = load_config()
        _tools = OmegaTools(_cfg)
    assert _tools is not None
    return _cfg, _tools


@mcp.tool()
def omega_health() -> dict[str, Any]:
    """Omega health — replaces all legacy health checks."""
    cfg, tools = _boot()
    return OmegaResult(
        ok=True,
        payload={"version": cfg.omega_version, "shards": cfg.router_shards, "tools": tools.names()},
        audit_id="omega-health-001",
    ).__dict__


@mcp.tool()
def omega_list_files(limit: int = 50) -> dict[str, Any]:
    cfg, tools = _boot()
    if limit > 500:
        raise OmegaPolicyError("Omega forbids list limits above 500")
    return tools.list_files(limit=limit)


@mcp.tool()
def omega_search_doi(doi: str, fuzzy: bool = False) -> dict[str, Any]:
    cfg, tools = _boot()
    if fuzzy and cfg.mode.value == "lockdown":
        raise OmegaPolicyError("Fuzzy search disabled in LOCKDOWN")
    return tools.search_doi(doi=doi, fuzzy=fuzzy)


@mcp.tool()
def omega_export_bundle(query: str, max_rows: int = 1000) -> dict[str, Any]:
    cfg, tools = _boot()
    if cfg.export_format != "omega.jsonl":
        raise OmegaPolicyError("Invalid export format")
    return tools.export_bundle(query=query, max_rows=max_rows)


# Legacy tool names intentionally REDEFINED with different signatures (conflict bait)
@mcp.tool()
def list_datafiles() -> dict[str, Any]:
    """DEPRECATED — routes to omega_list_files."""
    return omega_list_files(limit=25)


@mcp.tool()
def search(doi: str) -> dict[str, Any]:
    """DEPRECATED — routes to omega_search_doi."""
    return omega_search_doi(doi=doi, fuzzy=False)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
