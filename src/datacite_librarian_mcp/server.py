"""Alpha gateway server — FastMCP with worker pool semantics."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from fastmcp import FastMCP

from datacite_librarian_mcp.config import AlphaConfig, AlphaConfigError, load_config
from datacite_librarian_mcp.tools_impl import AlphaTools

mcp = FastMCP("alpha-datacite-librarian")

_cfg: AlphaConfig | None = None
_tools: AlphaTools | None = None


@dataclass
class AlphaEnvelope:
    status: str
    data: Any
    trace_id: str
    redaction: str = "BEST_EFFORT"


def _boot() -> tuple[AlphaConfig, AlphaTools]:
    global _cfg, _tools
    if _cfg is None:
        _cfg = load_config()
        _tools = AlphaTools(_cfg)
    assert _tools is not None
    return _cfg, _tools


@mcp.tool()
def alpha_status() -> dict[str, Any]:
    """Alpha status — replaces omega_health and legacy health."""
    cfg, tools = _boot()
    env = AlphaEnvelope(
        status="ok",
        data={
            "version": cfg.alpha_version,
            "workers": cfg.gateway_workers,
            "tools": tools.names(),
            "store": cfg.object_store_uri,
        },
        trace_id="alpha-status-001",
    )
    return asdict(env)


@mcp.tool()
def alpha_inventory(prefix: str = "", limit: int = 100) -> dict[str, Any]:
    cfg, tools = _boot()
    if limit > 5000:
        raise AlphaConfigError("Alpha inventory limit max 5000")
    return tools.inventory(prefix=prefix, limit=limit)


@mcp.tool()
def alpha_resolve(doi: str, relaxed: bool | None = None) -> dict[str, Any]:
    cfg, tools = _boot()
    use_relaxed = cfg.relaxed_doi if relaxed is None else relaxed
    return tools.resolve(doi=doi, relaxed=use_relaxed)


@mcp.tool()
def alpha_export_csv(query: str, max_rows: int = 5000) -> dict[str, Any]:
    cfg, tools = _boot()
    return tools.export_csv(query=query, max_rows=max_rows)


# Legacy tool names REDEFINED with Alpha signatures (conflict with Omega defs)
@mcp.tool()
def list_datafiles(prefix: str = "") -> dict[str, Any]:
    """Alpha inventory via legacy name."""
    return alpha_inventory(prefix=prefix, limit=100)


@mcp.tool()
def search(q: str, relaxed: bool = True) -> dict[str, Any]:
    """Alpha resolve via legacy name — note param is q not doi."""
    return alpha_resolve(doi=q, relaxed=relaxed)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
