from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BigBangCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=240)
    description: str | None = None
    scenario_text: str | None = None
    scenario_input: dict[str, Any] = Field(default_factory=dict)
    simulation_config: dict[str, Any] = Field(default_factory=dict)
    llm_model_config: dict[str, Any] = Field(default_factory=dict, alias="model_config")
    branch_policy: dict[str, Any] = Field(default_factory=dict)
    actors: list[dict[str, Any]] = Field(default_factory=list)
    cohorts: list[dict[str, Any]] = Field(default_factory=list)
    heroes: list[dict[str, Any]] = Field(default_factory=list)
    use_initializer_agent: bool = True
    initializer_prompt: str | None = None


class BigBangPatch(BaseModel):
    name: str | None = Field(default=None, max_length=240)
    description: str | None = None
    status: str | None = None


class BigBangOut(ORMModel):
    id: UUID
    name: str
    description: str | None
    scenario_input: dict[str, Any]
    status: str
    current_config_version: int
    source_snapshot_id: UUID | None
    created_at: datetime
    updated_at: datetime


class MultiverseOut(ORMModel):
    id: UUID
    big_bang_id: UUID
    parent_multiverse_id: UUID | None
    fork_tick_index: int | None
    ui_label: str
    depth: int
    status: str
    branch_reason: str | None
    state: dict[str, Any]
    report_status: str
    created_at: datetime
    updated_at: datetime


class TickSnapshotOut(ORMModel):
    id: UUID
    big_bang_id: UUID
    multiverse_id: UUID
    tick_index: int
    ui_label: str
    status: str
    provisional_bundle: dict[str, Any]
    final_bundle: dict[str, Any]
    summary: str | None
    artifact_id: UUID | None
    created_at: datetime
    updated_at: datetime


class SimulateTickRequest(BaseModel):
    idempotency_key: str | None = None
    force: bool = False


class SimulateTicksRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=100)


class RunUntilCompleteRequest(BaseModel):
    max_total_ticks: int = Field(default=24, ge=1, le=500)


class ToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None


class ReportRequest(BaseModel):
    title: str | None = None
    summary: str | None = None
    regenerate: bool = False


class JobCreate(BaseModel):
    job_type: str
    big_bang_id: UUID | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None


class GenericOut(BaseModel):
    data: Any


class WorkspaceState(BaseModel):
    big_bang: BigBangOut
    multiverses: list[MultiverseOut]
    latest_ticks: list[TickSnapshotOut]
    activity: list[dict[str, Any]]
