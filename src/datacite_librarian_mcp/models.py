"""Alpha Pydantic models — field names intentionally diverge from Omega."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


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


# Legacy names Omega also binds — different models underneath
HealthReport = AlphaStatus
FileEntry = AlphaInventoryItem
SearchHit = AlphaResolveHit
SearchResponse = AlphaResolveResponse
ExportRequest = AlphaExportRequest
ExportResponse = AlphaExportResponse


def alpha_schema_summary() -> dict[str, Any]:
    return {
        "engine": "alpha-3",
        "models": [
            "AlphaStatus",
            "AlphaInventoryItem",
            "AlphaResolveHit",
            "AlphaResolveResponse",
            "AlphaExportRequest",
            "AlphaExportResponse",
        ],
    }
