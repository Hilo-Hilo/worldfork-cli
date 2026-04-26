from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.utils import require, row_dict
from app.core.config import get_settings
from app.db import models
from app.db.session import get_db
from app.jobs.queues import JOB_TYPES
from app.simulation.scenario_bank import COVERAGE_MATRIX, list_scenarios
from app.source_of_truth.loader import SourceOfTruthLoader
from app.source_of_truth.validator import REQUIRED_FILES

router = APIRouter(prefix="/frontend", tags=["frontend"])


def _encode(value: Any) -> Any:
    return jsonable_encoder(value)


def _rows(rows: list[Any]) -> list[dict[str, Any]]:
    return [_encode(row_dict(row)) for row in rows]


def _row(row: Any | None) -> dict[str, Any] | None:
    return _encode(row_dict(row)) if row else None


def _load_source_of_truth() -> dict[str, Any]:
    loader = SourceOfTruthLoader()
    data = {}
    for name in REQUIRED_FILES:
        if not name.endswith(".json"):
            continue
        data[name.removesuffix(".json")] = loader.load_json(name)
    return data


def _frontend_defaults() -> dict[str, Any]:
    settings = get_settings()
    return {
        "simulation_config": {
            "tick_duration": settings.default_tick_duration,
            "max_ticks": settings.default_max_ticks,
        },
        "branch_policy": {
            "max_branch_depth": settings.default_max_branch_depth,
            "max_active_multiverses": settings.default_max_active_multiverses,
            "max_branches_per_tick": settings.default_max_branches_per_tick,
            "branch_score_threshold": settings.branch_score_threshold,
        },
        "model_config": {
            "provider": settings.default_llm_provider,
            "default_model": settings.default_model,
            "initializer_agent_model": settings.initializer_agent_model,
            "god_agent_model": settings.god_agent_model,
            "cohort_agent_model": settings.cohort_agent_model,
            "hero_agent_model": settings.hero_agent_model,
            "event_summary_model": settings.event_summary_model,
            "report_agent_model": settings.report_agent_model,
        },
    }


@router.get("/bootstrap")
def bootstrap():
    source = _load_source_of_truth()
    settings = get_settings()
    return {
        "settings": {
            "app_name": settings.app_name,
            "api_prefix": settings.api_prefix,
            "default_llm_provider": settings.default_llm_provider,
            "default_model": settings.default_model,
        },
        "defaults": _frontend_defaults(),
        "source_of_truth": source,
        "labels": {
            "emotions": source.get("emotions", {}).get("emotions", []),
            "graph_layers": source.get("graph_edge_types", {}).get("layers", []),
            "sociology_models": source.get("sociology_models", {}).get("models", []),
            "event_types": source.get("event_types", {}).get("event_types", []),
            "social_action_types": source.get("social_action_types", {}).get("action_types", []),
            "tools": source.get("tool_registry", {}).get("tools", []),
        },
        "scenario_bank": {
            "scenarios": list_scenarios(),
            "coverage_matrix": COVERAGE_MATRIX,
        },
        "job_types": sorted(JOB_TYPES),
    }


@router.get("/workspace/{big_bang_id}")
def workspace(big_bang_id: UUID, db: Session = Depends(get_db)):
    big_bang = require(db, models.BigBang, big_bang_id)
    multiverses = db.scalars(
        select(models.Multiverse)
        .where(models.Multiverse.big_bang_id == big_bang_id)
        .order_by(models.Multiverse.ui_label)
    ).all()
    lineage_edges = db.scalars(
        select(models.MultiverseLineageEdge)
        .where(models.MultiverseLineageEdge.big_bang_id == big_bang_id)
        .order_by(models.MultiverseLineageEdge.created_at)
    ).all()
    latest_ticks = db.scalars(
        select(models.TickSnapshot)
        .where(models.TickSnapshot.big_bang_id == big_bang_id)
        .order_by(models.TickSnapshot.created_at.desc())
        .limit(250)
    ).all()
    actors = db.scalars(
        select(models.Actor)
        .where(models.Actor.big_bang_id == big_bang_id)
        .order_by(models.Actor.name)
    ).all()
    graph_snapshots = db.scalars(
        select(models.GraphSnapshot)
        .where(models.GraphSnapshot.big_bang_id == big_bang_id)
        .order_by(models.GraphSnapshot.created_at.desc())
        .limit(100)
    ).all()
    emotion_snapshots = db.scalars(
        select(models.EmotionGraphSnapshot)
        .where(models.EmotionGraphSnapshot.big_bang_id == big_bang_id)
        .order_by(models.EmotionGraphSnapshot.created_at.desc())
        .limit(100)
    ).all()
    emotion_observations = db.scalars(
        select(models.EmotionObservation)
        .where(models.EmotionObservation.big_bang_id == big_bang_id)
        .order_by(models.EmotionObservation.created_at.desc())
        .limit(150)
    ).all()
    sociology_signals = db.scalars(
        select(models.SociologySignal)
        .where(models.SociologySignal.big_bang_id == big_bang_id)
        .order_by(models.SociologySignal.created_at.desc())
        .limit(150)
    ).all()
    reports = db.scalars(
        select(models.Report)
        .where(models.Report.big_bang_id == big_bang_id)
        .order_by(models.Report.created_at.desc())
    ).all()
    jobs = db.scalars(
        select(models.Job)
        .where(models.Job.big_bang_id == big_bang_id)
        .order_by(models.Job.created_at.desc())
        .limit(50)
    ).all()
    tool_calls = db.scalars(
        select(models.ToolCall)
        .where(models.ToolCall.big_bang_id == big_bang_id)
        .order_by(models.ToolCall.created_at.desc())
        .limit(50)
    ).all()

    ticks_by_multiverse: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for tick in sorted(latest_ticks, key=lambda item: (str(item.multiverse_id), item.tick_index)):
        ticks_by_multiverse[str(tick.multiverse_id)].append(_encode(row_dict(tick)))

    graph_layers: dict[str, dict[str, Any]] = {}
    for snapshot in graph_snapshots:
        layer = snapshot.layer
        current = graph_layers.setdefault(layer, {"layer": layer, "count": 0, "latest_tick_index": None})
        current["count"] += 1
        current["latest_tick_index"] = max(
            current["latest_tick_index"] if current["latest_tick_index"] is not None else snapshot.tick_index,
            snapshot.tick_index,
        )

    emotions_seen = sorted({observation.emotion for observation in emotion_observations})
    sociology_models = sorted({signal.model for signal in sociology_signals})
    activity = _activity(latest_ticks, tool_calls, jobs, reports)

    return {
        "big_bang": _row(big_bang),
        "multiverses": _rows(multiverses),
        "lineage_edges": _rows(lineage_edges),
        "ticks_by_multiverse": dict(ticks_by_multiverse),
        "latest_ticks": _rows(latest_ticks[:50]),
        "actors": _rows(actors),
        "graphs": {
            "layers": sorted(graph_layers.values(), key=lambda item: item["layer"]),
            "snapshots": _rows(graph_snapshots[:25]),
        },
        "emotion_observability": {
            "emotions_seen": emotions_seen,
            "snapshots": _rows(emotion_snapshots[:25]),
            "observations": _rows(emotion_observations[:50]),
        },
        "sociology": {
            "models_seen": sociology_models,
            "signals": _rows(sociology_signals[:50]),
        },
        "reports": _rows(reports),
        "jobs": _rows(jobs),
        "activity": activity,
    }


@router.get("/inspect/{object_type}/{object_id}")
def inspect(object_type: str, object_id: UUID, db: Session = Depends(get_db)):
    object_type = object_type.replace("-", "_").lower()
    if object_type == "big_bang":
        big_bang = require(db, models.BigBang, object_id)
        return {"type": object_type, "item": _row(big_bang)}
    if object_type == "multiverse":
        multiverse = require(db, models.Multiverse, object_id)
        ticks = db.scalars(
            select(models.TickSnapshot)
            .where(models.TickSnapshot.multiverse_id == object_id)
            .order_by(models.TickSnapshot.tick_index)
        ).all()
        children = db.scalars(
            select(models.Multiverse)
            .where(models.Multiverse.parent_multiverse_id == object_id)
            .order_by(models.Multiverse.ui_label)
        ).all()
        return {
            "type": object_type,
            "item": _row(multiverse),
            "ticks": _rows(ticks),
            "children": _rows(children),
        }
    if object_type == "tick":
        tick = require(db, models.TickSnapshot, object_id)
        god_review = db.scalar(select(models.GodAgentReview).where(models.GodAgentReview.tick_snapshot_id == object_id))
        return {
            "type": object_type,
            "item": _row(tick),
            "events": _rows(db.scalars(select(models.Event).where(models.Event.multiverse_id == tick.multiverse_id, models.Event.scheduled_tick == tick.tick_index)).all()),
            "social_posts": _rows(db.scalars(select(models.SocialPost).where(models.SocialPost.multiverse_id == tick.multiverse_id, models.SocialPost.tick_index == tick.tick_index)).all()),
            "oasis_actions": _rows(db.scalars(select(models.OASISAction).where(models.OASISAction.multiverse_id == tick.multiverse_id, models.OASISAction.tick_index == tick.tick_index)).all()),
            "tool_calls": _rows(db.scalars(select(models.ToolCall).where(models.ToolCall.tick_snapshot_id == object_id)).all()),
            "reasoning_traces": _rows(db.scalars(select(models.ReasoningTrace).where(models.ReasoningTrace.tick_snapshot_id == object_id)).all()),
            "graph_snapshots": _rows(db.scalars(select(models.GraphSnapshot).where(models.GraphSnapshot.multiverse_id == tick.multiverse_id, models.GraphSnapshot.tick_index == tick.tick_index)).all()),
            "emotion_snapshots": _rows(db.scalars(select(models.EmotionGraphSnapshot).where(models.EmotionGraphSnapshot.tick_snapshot_id == object_id)).all()),
            "sociology_signals": _rows(db.scalars(select(models.SociologySignal).where(models.SociologySignal.multiverse_id == tick.multiverse_id, models.SociologySignal.tick_index == tick.tick_index)).all()),
            "god_review": _row(god_review),
        }
    if object_type == "actor":
        actor = require(db, models.Actor, object_id)
        return {
            "type": object_type,
            "item": _row(actor),
            "cohort_states": _rows(db.scalars(select(models.CohortState).where(models.CohortState.actor_id == object_id)).all()),
            "hero_states": _rows(db.scalars(select(models.HeroState).where(models.HeroState.actor_id == object_id)).all()),
            "events": _rows(db.scalars(select(models.Event).where(models.Event.creator_actor_id == object_id)).all()),
            "graph_edges": _rows(db.scalars(select(models.GraphEdge).where((models.GraphEdge.source_actor_id == object_id) | (models.GraphEdge.target_actor_id == object_id))).all()),
            "sociology_signals": _rows(db.scalars(select(models.SociologySignal).where(models.SociologySignal.actor_id == object_id)).all()),
            "emotion_observations": _rows(db.scalars(select(models.EmotionObservation).where(models.EmotionObservation.actor_id == object_id)).all()),
        }
    if object_type == "graph_edge":
        return {"type": object_type, "item": _row(require(db, models.GraphEdge, object_id))}
    if object_type == "god_review":
        review = require(db, models.GodAgentReview, object_id)
        return {
            "type": object_type,
            "item": _row(review),
            "tool_calls": _rows(db.scalars(select(models.ToolCall).where(models.ToolCall.god_review_id == object_id)).all()),
        }
    if object_type == "tool_call":
        return {"type": object_type, "item": _row(require(db, models.ToolCall, object_id))}
    if object_type == "report":
        report = require(db, models.Report, object_id)
        versions = db.scalars(
            select(models.ReportVersion)
            .where(models.ReportVersion.report_id == object_id)
            .order_by(models.ReportVersion.version.desc())
        ).all()
        return {"type": object_type, "item": _row(report), "versions": _rows(versions)}
    if object_type == "job":
        return {"type": object_type, "item": _row(require(db, models.Job, object_id))}
    raise HTTPException(status_code=404, detail=f"unsupported inspector type: {object_type}")


def _activity(ticks: list[Any], tool_calls: list[Any], jobs: list[Any], reports: list[Any]) -> list[dict[str, Any]]:
    items = []
    for tick in ticks[:25]:
        items.append({
            "kind": "tick",
            "id": str(tick.id),
            "label": tick.ui_label,
            "status": tick.status,
            "created_at": tick.created_at,
        })
    for call in tool_calls[:25]:
        items.append({
            "kind": "tool_call",
            "id": str(call.id),
            "label": call.tool_name,
            "status": call.status,
            "created_at": call.created_at,
        })
    for job in jobs[:25]:
        items.append({
            "kind": "job",
            "id": str(job.id),
            "label": job.job_type,
            "status": job.status,
            "created_at": job.created_at,
        })
    for report in reports[:25]:
        items.append({
            "kind": "report",
            "id": str(report.id),
            "label": report.report_type,
            "status": report.status,
            "created_at": report.created_at,
        })
    return _encode(sorted(items, key=lambda item: str(item["created_at"] or ""), reverse=True)[:50])
