from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas import JobCreate
from app.api.utils import commit_or_500, require
from app.db import models
from app.db.session import SessionLocal, get_db
from app.jobs.queues import JOB_TYPES, default_idempotency_key, enqueue_job
from app.jobs.tasks import (
    JobNotRunnableError,
    execute_job,
    job_should_enqueue_for_retry,
    validate_job_payload,
    validate_job_type,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/types")
def types():
    return sorted(JOB_TYPES)


@router.get("")
def list_jobs(db: Session = Depends(get_db)):
    return db.scalars(select(models.Job).order_by(models.Job.created_at.desc()).limit(100)).all()


@router.post("")
def create_job(payload: JobCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    return create_job_record(payload, db=db, background_tasks=background_tasks)


def create_job_record(payload: JobCreate, db: Session, background_tasks: BackgroundTasks | None = None):
    try:
        validate_job_type(payload.job_type)
        validate_job_payload(payload.job_type, payload.payload, big_bang_id=payload.big_bang_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    key = payload.idempotency_key or default_idempotency_key(
        payload.job_type,
        payload.big_bang_id,
        payload.payload,
    )
    existing = db.scalar(select(models.Job).where(models.Job.idempotency_key == key))
    if existing:
        if not enqueue_recoverable_job(db, existing):
            schedule_local_fallback(background_tasks, existing.id)
        return existing
    job = models.Job(
        job_type=payload.job_type,
        status="queued",
        big_bang_id=payload.big_bang_id,
        payload=payload.payload,
        idempotency_key=key,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(models.Job).where(models.Job.idempotency_key == key))
        if existing:
            if not enqueue_recoverable_job(db, existing):
                schedule_local_fallback(background_tasks, existing.id)
            return existing
        raise HTTPException(status_code=409, detail="job idempotency key conflict") from None
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="could not create job") from exc
    if not enqueue_recoverable_job(db, job, force=True):
        schedule_local_fallback(background_tasks, job.id)
    return job


@router.get("/{job_id}")
def get_job(job_id: UUID, db: Session = Depends(get_db)):
    return require(db, models.Job, job_id)


@router.post("/{job_id}/run")
def run_job(job_id: UUID, db: Session = Depends(get_db)):
    job = require(db, models.Job, job_id)
    try:
        execute_job(db, job, commit_running=True)
    except JobNotRunnableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    commit_or_500(db)
    if job.status == "failed":
        raise HTTPException(status_code=500, detail="job execution failed")
    return job


def enqueue_recoverable_job(db: Session, job: models.Job, *, force: bool = False) -> bool:
    if not force and not job_should_enqueue_for_retry(job):
        return True
    try:
        enqueue_job(job.id)
    except Exception as exc:
        job.error = "enqueue failed; running with local worker fallback"
        commit_or_500(db)
        return False
    if job.error:
        job.error = None
        commit_or_500(db)
    return True


def schedule_local_fallback(background_tasks: BackgroundTasks | None, job_id: UUID) -> None:
    if background_tasks is not None:
        background_tasks.add_task(run_job_local_fallback, job_id)


def run_job_local_fallback(job_id: UUID) -> None:
    db = SessionLocal()
    try:
        job = db.get(models.Job, job_id)
        if not job:
            return
        execute_job(db, job, commit_running=True)
        db.commit()
    finally:
        db.close()
