"""Merged Pydantic models — Alpha + Omega types both exported."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# --- Omega ---
class OmegaHealthReport(BaseModel):
    omega_version: str
    shards: int
    mode: Literal["strict", "audit", "lockdown"]
    pii_zero: bool = True


class OmegaFileEntry(BaseModel):
    omega_path: str
    bytes: int
    shard: int


class OmegaSearchHit(BaseModel):
    doi: str
    title: str
    vault_ref: str
    omega_score: float = 1.0


class OmegaSearchResponse(BaseModel):
    ok: bool = True
    audit_id: str
    query: str
    fuzzy: bool = False
    hits: list[OmegaSearchHit] = Field(default_factory=list)


class OmegaExportRequest(BaseModel):
    query: str
    max_rows: int = 1000
    format: Literal["omega.jsonl"] = "omega.jsonl"


class OmegaExportResponse(BaseModel):
    ok: bool
    audit_id: str
    path: str
    rows: int
    format: str = "omega.jsonl"


# --- Alpha ---
class AlphaStatus(BaseModel):
    alpha_version: str
    workers: int
    mode: Literal["relaxed", "standard", "experimental"]
    pii_zero: bool = False
    store: str = ""


class AlphaInventoryItem(BaseModel):
    alpha_uri: str
    local_path: str | None = None
    size: int
    worker_hint: int = 0


class AlphaResolveHit(BaseModel):
    doi: str
    title: str
    store_key: str
    alpha_score: float = 0.5


class AlphaResolveResponse(BaseModel):
    status: str = "ok"
    trace_id: str
    input: str
    relaxed: bool = True
    results: list[AlphaResolveHit] = Field(default_factory=list)


class AlphaExportRequest(BaseModel):
    query: str
    max_rows: int = 5000
    format: Literal["csv", "jsonl", "parquet"] = "csv"


class AlphaExportResponse(BaseModel):
    status: str
    trace_id: str
    path: str
    rows: int
    format: str = "csv"


# Ambiguous legacy aliases — favor neither; map to merged docs
HealthReport = OmegaHealthReport  # Alpha used AlphaStatus; pick Omega name, both classes exist
FileEntry = OmegaFileEntry
SearchHit = OmegaSearchHit
SearchResponse = OmegaSearchResponse
ExportRequest = AlphaExportRequest
ExportResponse = AlphaExportResponse


def schema_summary() -> dict[str, Any]:
    return {
        "merged": True,
        "omega_models": [
            "OmegaHealthReport",
            "OmegaFileEntry",
            "OmegaSearchHit",
            "OmegaSearchResponse",
            "OmegaExportRequest",
            "OmegaExportResponse",
        ],
        "alpha_models": [
            "AlphaStatus",
            "AlphaInventoryItem",
            "AlphaResolveHit",
            "AlphaResolveResponse",
            "AlphaExportRequest",
            "AlphaExportResponse",
        ],
    }


omega_schema_summary = schema_summary
alpha_schema_summary = schema_summary
