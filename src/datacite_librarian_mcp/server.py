"""Merged server — exposes Omega + Alpha tools on one FastMCP instance."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from fastmcp import FastMCP

from datacite_librarian_mcp.config import (
    AlphaConfig,
    AlphaConfigError,
    MergedConfig,
    OmegaConfig,
    OmegaPolicyError,
    load_config,
    runtime_team,
)
from datacite_librarian_mcp.tools_impl import AlphaTools, MergedTools, OmegaTools

mcp = FastMCP("merged-datacite-librarian")

_cfg: MergedConfig | None = None
_tools: MergedTools | None = None


@dataclass
class OmegaResult:
    ok: bool
    payload: Any
    audit_id: str
    policy: str = "PII_ZERO"


@dataclass
class AlphaEnvelope:
    status: str
    data: Any
    trace_id: str
    redaction: str = "BEST_EFFORT"


def _boot() -> tuple[MergedConfig, MergedTools]:
    global _cfg, _tools
    if _cfg is None:
        _cfg = load_config()
        _tools = MergedTools(_cfg.omega, _cfg.alpha)
    assert _tools is not None
    return _cfg, _tools


# --- Omega tools ---
@mcp.tool()
def omega_health() -> dict[str, Any]:
    cfg, tools = _boot()
    return OmegaResult(
        ok=True,
        payload={
            "version": cfg.omega.omega_version,
            "shards": cfg.omega.router_shards,
            "tools": tools.omega.names(),
            "runtime_team": runtime_team(),
        },
        audit_id="omega-health-001",
    ).__dict__


@mcp.tool()
def omega_list_files(limit: int = 50) -> dict[str, Any]:
    _, tools = _boot()
    if limit > 500:
        raise OmegaPolicyError("Omega forbids list limits above 500")
    return tools.omega.list_files(limit=limit)


@mcp.tool()
def omega_search_doi(doi: str, fuzzy: bool = False) -> dict[str, Any]:
    cfg, tools = _boot()
    if fuzzy and cfg.omega.mode.value == "lockdown":
        raise OmegaPolicyError("Fuzzy search disabled in LOCKDOWN")
    return tools.omega.search_doi(doi=doi, fuzzy=fuzzy)


@mcp.tool()
def omega_export_bundle(query: str, max_rows: int = 1000) -> dict[str, Any]:
    _, tools = _boot()
    return tools.omega.export_bundle(query=query, max_rows=max_rows)


# --- Alpha tools ---
@mcp.tool()
def alpha_status() -> dict[str, Any]:
    cfg, tools = _boot()
    env = AlphaEnvelope(
        status="ok",
        data={
            "version": cfg.alpha.alpha_version,
            "workers": cfg.alpha.gateway_workers,
            "tools": tools.alpha.names(),
            "store": cfg.alpha.object_store_uri,
            "runtime_team": runtime_team(),
        },
        trace_id="alpha-status-001",
    )
    return asdict(env)


@mcp.tool()
def alpha_inventory(prefix: str = "", limit: int = 100) -> dict[str, Any]:
    _, tools = _boot()
    if limit > 5000:
        raise AlphaConfigError("Alpha inventory limit max 5000")
    return tools.alpha.inventory(prefix=prefix, limit=limit)


@mcp.tool()
def alpha_resolve(doi: str, relaxed: bool | None = None) -> dict[str, Any]:
    cfg, tools = _boot()
    use_relaxed = cfg.alpha.relaxed_doi if relaxed is None else relaxed
    return tools.alpha.resolve(doi=doi, relaxed=use_relaxed)


@mcp.tool()
def alpha_export_csv(query: str, max_rows: int = 5000) -> dict[str, Any]:
    _, tools = _boot()
    return tools.alpha.export_csv(query=query, max_rows=max_rows)


# --- Ambiguous legacy tools ---
@mcp.tool()
def list_datafiles(prefix: str = "", limit: int = 50) -> dict[str, Any]:
    team = runtime_team()
    _, tools = _boot()
    if team == "alpha":
        return tools.alpha.inventory(prefix=prefix, limit=limit)
    if team == "omega":
        return tools.omega.list_files(limit=limit)
    return {"merged": True, "omega": tools.omega.list_files(limit=limit), "alpha": tools.alpha.inventory(prefix=prefix, limit=limit)}


@mcp.tool()
def search(q: str = "", doi: str = "", relaxed: bool = True, fuzzy: bool = False) -> dict[str, Any]:
    team = runtime_team()
    _, tools = _boot()
    term = doi or q
    if team == "alpha":
        return tools.alpha.resolve(doi=term, relaxed=relaxed)
    if team == "omega":
        return tools.omega.search_doi(doi=term, fuzzy=fuzzy)
    return {
        "merged": True,
        "omega": tools.omega.search_doi(doi=term, fuzzy=fuzzy) if "/" in term else {"ok": False, "reason": "omega needs slash"},
        "alpha": tools.alpha.resolve(doi=term, relaxed=relaxed),
    }


@mcp.tool()
def merged_status() -> dict[str, Any]:
    cfg, tools = _boot()
    return {
        "merged": True,
        "runtime_team": runtime_team(),
        "omega": cfg.omega.as_dict(),
        "alpha": cfg.alpha.as_dict(),
        "tools": tools.names(),
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
