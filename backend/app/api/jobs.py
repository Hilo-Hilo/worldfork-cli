from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas import JobCreate
from app.api.utils import commit_or_500, require
from app.db import models
from app.db.session import get_db
from app.jobs.queues import JOB_TYPES
from app.jobs.tasks import execute_job, validate_job_type

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/types")
def types():
    return sorted(JOB_TYPES)


@router.get("")
def list_jobs(db: Session = Depends(get_db)):
    return db.scalars(select(models.Job).order_by(models.Job.created_at.desc()).limit(100)).all()


@router.post("")
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    try:
        validate_job_type(payload.job_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    key = payload.idempotency_key or f"{payload.job_type}:{payload.big_bang_id}:{payload.payload}"
    existing = db.scalar(select(models.Job).where(models.Job.idempotency_key == key))
    if existing:
        return existing
    job = models.Job(
        job_type=payload.job_type,
        status="queued",
        big_bang_id=payload.big_bang_id,
        payload=payload.payload,
        idempotency_key=key,
    )
    db.add(job)
    commit_or_500(db)
    return job


@router.get("/{job_id}")
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    return require(db, models.Job, job_id)


@router.post("/{job_id}/run")
def run_job(job_id: UUID, db: Session = Depends(get_db)):
    job = require(db, models.Job, job_id)
    execute_job(db, job)
    commit_or_500(db)
    return job
