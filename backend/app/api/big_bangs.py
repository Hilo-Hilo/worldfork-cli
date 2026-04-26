from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import BigBangCreate, BigBangOut, BigBangPatch, ReportRequest, RunUntilCompleteRequest
from app.api.utils import commit_or_500, require
from app.db import models
from app.db.session import get_db
from app.simulation.initializer import create_big_bang
from app.simulation.report_engine import generate_final_big_bang_report
from app.simulation.run_orchestrator import run_big_bang_until_complete

router = APIRouter(prefix="/big-bangs", tags=["big-bangs"])


@router.get("", response_model=list[BigBangOut])
def list_big_bangs(db: Session = Depends(get_db)):
    return db.scalars(select(models.BigBang).order_by(models.BigBang.created_at.desc())).all()


@router.post("", response_model=BigBangOut, status_code=201)
def create(payload: BigBangCreate, db: Session = Depends(get_db)):
    big_bang = create_big_bang(db, payload)
    commit_or_500(db)
    return big_bang


@router.get("/{big_bang_id}", response_model=BigBangOut)
def get(big_bang_id: UUID, db: Session = Depends(get_db)):
    return require(db, models.BigBang, big_bang_id)


@router.patch("/{big_bang_id}", response_model=BigBangOut)
def patch(big_bang_id: UUID, payload: BigBangPatch, db: Session = Depends(get_db)):
    big_bang = require(db, models.BigBang, big_bang_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(big_bang, key, value)
    commit_or_500(db)
    return big_bang


@router.post("/{big_bang_id}/start", response_model=BigBangOut)
def start(big_bang_id: UUID, db: Session = Depends(get_db)):
    big_bang = require(db, models.BigBang, big_bang_id)
    big_bang.status = "running"
    commit_or_500(db)
    return big_bang


@router.post("/{big_bang_id}/pause", response_model=BigBangOut)
def pause(big_bang_id: UUID, db: Session = Depends(get_db)):
    big_bang = require(db, models.BigBang, big_bang_id)
    big_bang.status = "paused"
    commit_or_500(db)
    return big_bang


@router.post("/{big_bang_id}/resume", response_model=BigBangOut)
def resume(big_bang_id: UUID, db: Session = Depends(get_db)):
    big_bang = require(db, models.BigBang, big_bang_id)
    big_bang.status = "running"
    commit_or_500(db)
    return big_bang


@router.get("/{big_bang_id}/reports")
def reports(big_bang_id: UUID, db: Session = Depends(get_db)):
    require(db, models.BigBang, big_bang_id)
    return db.scalars(select(models.Report).where(models.Report.big_bang_id == big_bang_id)).all()


@router.post("/{big_bang_id}/reports/final")
def final_report(big_bang_id: UUID, payload: ReportRequest, db: Session = Depends(get_db)):
    big_bang = require(db, models.BigBang, big_bang_id)
    version = generate_final_big_bang_report(db, big_bang=big_bang, title=payload.title, summary=payload.summary)
    commit_or_500(db)
    return version


@router.post("/{big_bang_id}/run-until-complete")
def run_until_complete(big_bang_id: UUID, payload: RunUntilCompleteRequest, db: Session = Depends(get_db)):
    big_bang = require(db, models.BigBang, big_bang_id)
    result = run_big_bang_until_complete(db, big_bang=big_bang, max_total_ticks=payload.max_total_ticks)
    commit_or_500(db)
    return result
