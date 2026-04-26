from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import TickSnapshotOut
from app.api.utils import require
from app.db import models
from app.db.session import get_db

router = APIRouter(prefix="/ticks", tags=["ticks"])


@router.get("/{tick_snapshot_id}", response_model=TickSnapshotOut)
def get(tick_snapshot_id: UUID, db: Session = Depends(get_db)):
    return require(db, models.TickSnapshot, tick_snapshot_id)


@router.get("/{tick_snapshot_id}/details")
def details(tick_snapshot_id: UUID, db: Session = Depends(get_db)):
    tick = require(db, models.TickSnapshot, tick_snapshot_id)
    return {"tick": tick, "final_bundle": tick.final_bundle}


@router.get("/{tick_snapshot_id}/reasoning-traces")
def reasoning(tick_snapshot_id: UUID, db: Session = Depends(get_db)):
    return db.scalars(select(models.ReasoningTrace).where(models.ReasoningTrace.tick_snapshot_id == tick_snapshot_id)).all()


@router.get("/{tick_snapshot_id}/events")
def events(tick_snapshot_id: UUID, db: Session = Depends(get_db)):
    tick = require(db, models.TickSnapshot, tick_snapshot_id)
    return db.scalars(select(models.Event).where(models.Event.multiverse_id == tick.multiverse_id, models.Event.scheduled_tick == tick.tick_index)).all()


@router.get("/{tick_snapshot_id}/social")
def social(tick_snapshot_id: UUID, db: Session = Depends(get_db)):
    tick = require(db, models.TickSnapshot, tick_snapshot_id)
    posts = db.scalars(select(models.SocialPost).where(models.SocialPost.multiverse_id == tick.multiverse_id, models.SocialPost.tick_index == tick.tick_index)).all()
    oasis = db.scalars(select(models.OASISAction).where(models.OASISAction.multiverse_id == tick.multiverse_id, models.OASISAction.tick_index == tick.tick_index)).all()
    return {"posts": posts, "oasis_actions": oasis}


@router.get("/{tick_snapshot_id}/tool-calls")
def tool_calls(tick_snapshot_id: UUID, db: Session = Depends(get_db)):
    return db.scalars(select(models.ToolCall).where(models.ToolCall.tick_snapshot_id == tick_snapshot_id)).all()


@router.get("/{tick_snapshot_id}/emotion-observability")
def emotion(tick_snapshot_id: UUID, db: Session = Depends(get_db)):
    return db.scalars(select(models.EmotionGraphSnapshot).where(models.EmotionGraphSnapshot.tick_snapshot_id == tick_snapshot_id)).all()


@router.get("/{tick_snapshot_id}/graph-deltas")
def graph_deltas(tick_snapshot_id: UUID, db: Session = Depends(get_db)):
    tick = require(db, models.TickSnapshot, tick_snapshot_id)
    return db.scalars(select(models.GraphSnapshot).where(models.GraphSnapshot.multiverse_id == tick.multiverse_id, models.GraphSnapshot.tick_index == tick.tick_index)).all()


@router.get("/{tick_snapshot_id}/sociology-signals")
def sociology(tick_snapshot_id: UUID, db: Session = Depends(get_db)):
    tick = require(db, models.TickSnapshot, tick_snapshot_id)
    return db.scalars(select(models.SociologySignal).where(models.SociologySignal.multiverse_id == tick.multiverse_id, models.SociologySignal.tick_index == tick.tick_index)).all()


@router.get("/{tick_snapshot_id}/god-review")
def god_review(tick_snapshot_id: UUID, db: Session = Depends(get_db)):
    return db.scalar(select(models.GodAgentReview).where(models.GodAgentReview.tick_snapshot_id == tick_snapshot_id))
