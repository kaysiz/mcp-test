"""Omega Pydantic models — field names intentionally diverge from Alpha."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


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


# Legacy names Alpha will redefine
HealthReport = OmegaHealthReport
FileEntry = OmegaFileEntry
SearchHit = OmegaSearchHit
SearchResponse = OmegaSearchResponse
ExportRequest = OmegaExportRequest
ExportResponse = OmegaExportResponse


def omega_schema_summary() -> dict[str, Any]:
    return {
        "protocol": "omega-v2",
        "models": [
            "OmegaHealthReport",
            "OmegaFileEntry",
            "OmegaSearchHit",
            "OmegaSearchResponse",
            "OmegaExportRequest",
            "OmegaExportResponse",
        ],
    }
