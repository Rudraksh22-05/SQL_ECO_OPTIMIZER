from typing import Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)


class BenchmarkDetailResponse(BaseModel):
    id: int
    query: str
    table: str
    column: str

    baseline_time_ms: float
    optimized_time_ms: float
    improvement_percent: float | None

    baseline_plan: dict[str, Any]
    optimized_plan: dict[str, Any]

    benchmark_configuration: dict[str, Any]
    environment_metadata: dict[str, Any]
    environmental_impact: dict[str, Any]
    recommendation: dict[str, Any]

    index_information: dict[str, Any] | None
    cleanup_information: dict[str, Any] | None

    created_at: datetime

class BenchmarkRequest(BaseModel):
    query: str = Field(..., min_length=1)
    table: str = Field(..., min_length=1)
    column: str = Field(..., min_length=1)
    runs: int = Field(default=5, ge=1, le=20)

class BenchmarkHistoryItem(BaseModel):
    id: int
    query: str
    table: str
    column: str

    baseline_time_ms: float
    optimized_time_ms: float
    improvement_percent: float | None

    environmental_impact: dict[str, Any]

    created_at: datetime


class BenchmarkPagination(BaseModel):
    limit: int
    offset: int
    returned: int


class BenchmarkFilters(BaseModel):
    table: str | None
    column: str | None


class BenchmarkHistoryResponse(BaseModel):
    count: int
    pagination: BenchmarkPagination
    filters: BenchmarkFilters
    results: list[BenchmarkHistoryItem]

