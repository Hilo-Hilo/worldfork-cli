from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import MultiverseLineageOut, MultiverseOut, ReportRequest, ReportVersionOut, SimulateTickRequest, SimulateTicksRequest, TickSnapshotOut
from app.api.utils import commit_or_500, raise_llm_unavailable, require
from app.db import models
from app.db.session import get_db
from app.llm.audit import LLMCallError
from app.simulation.report_engine import generate_multiverse_report
from app.simulation.run_orchestrator import simulate_ticks
from app.simulation.tick_runner import run_next_tick

router = APIRouter(tags=["multiverses"])


@router.get("/big-bangs/{big_bang_id}/multiverses", response_model=list[MultiverseOut])
def list_for_big_bang(big_bang_id: UUID, db: Session = Depends(get_db)):
    require(db, models.BigBang, big_bang_id)
    return db.scalars(select(models.Multiverse).where(models.Multiverse.big_bang_id == big_bang_id).order_by(models.Multiverse.ui_label)).all()


@router.get("/multiverses/{multiverse_id}", response_model=MultiverseOut)
def get(multiverse_id: UUID, db: Session = Depends(get_db)):
    return require(db, models.Multiverse, multiverse_id)


@router.get("/multiverses/{multiverse_id}/lineage", response_model=MultiverseLineageOut)
def lineage(multiverse_id: UUID, db: Session = Depends(get_db)):
    multiverse = require(db, models.Multiverse, multiverse_id)
    edges = db.scalars(select(models.MultiverseLineageEdge).where(models.MultiverseLineageEdge.big_bang_id == multiverse.big_bang_id)).all()
    refs = db.scalars(select(models.TickLineageRef).where(models.TickLineageRef.child_multiverse_id == multiverse_id)).all()
    return {"multiverse": multiverse, "edges": edges, "inherited_ticks": refs}


@router.get("/multiverses/{multiverse_id}/ticks", response_model=list[TickSnapshotOut])
def ticks(multiverse_id: UUID, db: Session = Depends(get_db)):
    require(db, models.Multiverse, multiverse_id)
    return db.scalars(select(models.TickSnapshot).where(models.TickSnapshot.multiverse_id == multiverse_id).order_by(models.TickSnapshot.tick_index)).all()


@router.post("/multiverses/{multiverse_id}/simulate-next-tick", response_model=TickSnapshotOut)
def simulate(multiverse_id: UUID, payload: SimulateTickRequest | None = None, db: Session = Depends(get_db)):
    multiverse = require(db, models.Multiverse, multiverse_id)
    try:
        tick = run_next_tick(db, multiverse=multiverse, idempotency_key=(payload.idempotency_key if payload else None), force=(payload.force if payload else False))
    except LLMCallError as exc:
        db.rollback()
        raise_llm_unavailable(exc)
    except ValueError as exc:
        db.rollback()
        raise_simulation_value_error(exc)
    commit_or_500(db)
    return tick


@router.post("/multiverses/{multiverse_id}/simulate-ticks", response_model=list[TickSnapshotOut])
def simulate_many(multiverse_id: UUID, payload: SimulateTicksRequest | None = None, db: Session = Depends(get_db)):
    request = payload or SimulateTicksRequest()
    multiverse = require(db, models.Multiverse, multiverse_id)
    try:
        ticks = simulate_ticks(db, multiverse=multiverse, count=request.count, raise_on_domain_error=True)
    except LLMCallError as exc:
        db.rollback()
        raise_llm_unavailable(exc)
    except ValueError as exc:
        db.rollback()
        raise_simulation_value_error(exc)
    commit_or_500(db)
    return ticks


@router.post("/multiverses/{multiverse_id}/terminate", response_model=MultiverseOut)
def terminate(multiverse_id: UUID, db: Session = Depends(get_db)):
    multiverse = require(db, models.Multiverse, multiverse_id)
    multiverse.status = "terminated"
    multiverse.report_status = "ready"
    commit_or_500(db)
    return multiverse


@router.post("/multiverses/{multiverse_id}/report", response_model=ReportVersionOut)
def report(multiverse_id: UUID, payload: ReportRequest | None = None, db: Session = Depends(get_db)):
    request = payload or ReportRequest()
    multiverse = require(db, models.Multiverse, multiverse_id)
    version = generate_multiverse_report(db, multiverse=multiverse, title=request.title, summary=request.summary)
    commit_or_500(db)
    return version


def raise_simulation_value_error(exc: ValueError):
    detail = str(exc) or "simulation request cannot be completed"
    status_code = 422 if "must be" in detail.lower() or "invalid" in detail.lower() else 409
    raise HTTPException(status_code=status_code, detail=detail) from exc
