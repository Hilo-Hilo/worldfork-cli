from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.utils import require
from app.db import models
from app.db.session import get_db

router = APIRouter(prefix="/big-bangs/{big_bang_id}/initialization", tags=["initialization"])


@router.get("")
def initialization(big_bang_id: UUID, db: Session = Depends(get_db)):
    big_bang = require(db, models.BigBang, big_bang_id)
    return {
        "big_bang_id": big_bang.id,
        "scenario_text_present": bool(big_bang.scenario_input.get("scenario_text")),
        "plain_text_corpus": big_bang.scenario_input.get("plain_text_corpus", {}),
        "initializer_output": big_bang.scenario_input.get("initializer_output", {}),
    }


@router.get("/scenario-text")
def scenario_text(big_bang_id: UUID, db: Session = Depends(get_db)):
    big_bang = require(db, models.BigBang, big_bang_id)
    return {
        "big_bang_id": big_bang.id,
        "scenario_text": big_bang.scenario_input.get("scenario_text", ""),
    }


@router.get("/corpus")
def corpus(big_bang_id: UUID, db: Session = Depends(get_db)):
    big_bang = require(db, models.BigBang, big_bang_id)
    return big_bang.scenario_input.get("plain_text_corpus", {})


@router.get("/actors")
def actors(big_bang_id: UUID, db: Session = Depends(get_db)):
    return db.scalars(select(models.Actor).where(models.Actor.big_bang_id == big_bang_id)).all()


@router.get("/traits")
def traits(big_bang_id: UUID, db: Session = Depends(get_db)):
    actors = db.scalars(select(models.Actor).where(models.Actor.big_bang_id == big_bang_id)).all()
    return [
        {
            "actor_id": actor.id,
            "name": actor.name,
            "actor_type": actor.actor_type,
            "trait_vector": (actor.archetype or {}).get("trait_vector"),
        }
        for actor in actors
    ]


@router.get("/graphs")
def graphs(big_bang_id: UUID, db: Session = Depends(get_db)):
    edges = db.scalars(select(models.GraphEdge).where(models.GraphEdge.big_bang_id == big_bang_id)).all()
    snapshots = db.scalars(select(models.GraphSnapshot).where(models.GraphSnapshot.big_bang_id == big_bang_id)).all()
    return {"edges": edges, "snapshots": snapshots}


@router.get("/emotion-baseline")
def emotion_baseline(big_bang_id: UUID, db: Session = Depends(get_db)):
    observations = db.scalars(
        select(models.EmotionObservation).where(
            models.EmotionObservation.big_bang_id == big_bang_id,
            models.EmotionObservation.tick_index == 0,
        )
    ).all()
    snapshots = db.scalars(
        select(models.EmotionGraphSnapshot).where(
            models.EmotionGraphSnapshot.big_bang_id == big_bang_id,
            models.EmotionGraphSnapshot.tick_index == 0,
        )
    ).all()
    return {"observations": observations, "snapshots": snapshots}


@router.get("/sociology-baseline")
def sociology_baseline(big_bang_id: UUID, db: Session = Depends(get_db)):
    signals = db.scalars(
        select(models.SociologySignal).where(
            models.SociologySignal.big_bang_id == big_bang_id,
            models.SociologySignal.tick_index == 0,
        )
    ).all()
    influences = db.scalars(
        select(models.SociologyPromptInfluence).where(
            models.SociologyPromptInfluence.big_bang_id == big_bang_id,
            models.SociologyPromptInfluence.tick_index == 0,
        )
    ).all()
    return {"signals": signals, "prompt_influences": influences}


@router.get("/audit")
def audit(big_bang_id: UUID, db: Session = Depends(get_db)):
    calls = db.scalars(
        select(models.LLMCall)
        .where(models.LLMCall.big_bang_id == big_bang_id, models.LLMCall.purpose.like("initializer%"))
        .order_by(models.LLMCall.created_at)
    ).all()
    artifacts = db.scalars(
        select(models.Artifact)
        .where(models.Artifact.big_bang_id == big_bang_id)
        .order_by(models.Artifact.created_at)
    ).all()
    return {"llm_calls": calls, "artifacts": artifacts}
