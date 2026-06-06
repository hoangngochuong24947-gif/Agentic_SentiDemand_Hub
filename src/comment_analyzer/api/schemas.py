"""Pydantic schemas for the stable /api/v1 contract."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "comment-analyzer-api"
    version: str


class RunSummary(BaseModel):
    run_id: str
    source_file: str = ""
    created_at: str = ""
    status: str = "unknown"
    summary: Dict[str, Any] = Field(default_factory=dict)
    user_message: str = ""


class RunListResponse(BaseModel):
    runs: List[RunSummary]
    total: int


class RunDetailResponse(BaseModel):
    run_id: str
    source_file: str = ""
    created_at: str = ""
    status: str = "unknown"
    derived_tables: List[Dict[str, Any]] = Field(default_factory=list)
    charts: List[Dict[str, Any]] = Field(default_factory=list)
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    insights: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)
    user_message: str = ""
    failure_category: Optional[str] = None
    failure_message: Optional[str] = None
    insight_status: str = "not_generated"
    insight_updated_at: str = ""
    advice_markdown: str = ""
    structured_advice: Dict[str, Any] = Field(default_factory=dict)


class ArtifactListResponse(BaseModel):
    run_id: str
    items: List[Dict[str, Any]]
    total: int


class ChartDataRecord(BaseModel):
    id: str
    title: str
    kind: str
    status: str = "missing"
    data: Dict[str, Any] = Field(default_factory=dict)
    legacy_artifact: Optional[Dict[str, Any]] = None
    reason: str = ""


class ChartDataResponse(BaseModel):
    run_id: str
    charts: List[ChartDataRecord]
    total: int


class UploadResponse(BaseModel):
    job_id: str
    run_id: str = ""
    status: str
    uploaded_file: str = ""
    user_message: str = ""
    artifacts: Dict[str, Any] = Field(default_factory=dict)


class AnalysisRunRequest(BaseModel):
    run_id: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class JobResponse(BaseModel):
    job_id: str
    status: str
    run_id: Optional[str] = None
    kind: str = "analysis"
    created_at: str
    updated_at: str
    message: str = ""
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    progress: int = 0
    cancellation_requested: bool = False
    retry_of: Optional[str] = None


class JobCancelResponse(JobResponse):
    pass


class InsightGenerateRequest(BaseModel):
    api_key: Optional[str] = None
    session_id: Optional[str] = None
    force: bool = False


class StructuredAdvice(BaseModel):
    findings: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    risks: List[Dict[str, Any]] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


class InsightGenerateResponse(BaseModel):
    run_id: str
    job_id: str
    status: str
    insight_status: str
    insight_updated_at: str
    advice_markdown: str = ""
    structured_advice: StructuredAdvice = Field(default_factory=StructuredAdvice)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)


class ExportResultsRequest(BaseModel):
    run_id: str
    artifact_groups: Optional[List[str]] = None


class ExportResultsResponse(BaseModel):
    export_id: str
    status: str
    run_id: str
    download_url: str
    path: str
    included_counts: Dict[str, int] = Field(default_factory=dict)
