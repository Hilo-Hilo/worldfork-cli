from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.api.schemas import BigBangCreate
from app.jobs.queues import JOB_TYPES
from app.simulation.initializer import create_big_bang
from app.simulation.report_engine import generate_final_big_bang_report, generate_multiverse_report
from app.simulation.run_orchestrator import run_big_bang_until_complete, simulate_ticks
from app.simulation.tick_runner import run_next_tick


def validate_job_type(job_type: str) -> None:
    if job_type not in JOB_TYPES:
        raise ValueError(f"unknown job_type: {job_type}")


def execute_job(db: Session, job: models.Job) -> models.Job:
    validate_job_type(job.job_type)
    job.status = "running"
    db.flush()
    try:
        result = _execute_job(db, job)
        job.result = result
        job.status = "succeeded"
    except Exception as exc:
        job.error = str(exc)
        job.status = "failed"
    db.flush()
    return job


def _execute_job(db: Session, job: models.Job) -> dict:
    payload = job.payload or {}
    if job.job_type == "initialize_big_bang":
        big_bang = create_big_bang(db, BigBangCreate(**payload))
        return {"big_bang_id": str(big_bang.id), "source_snapshot_id": str(big_bang.source_snapshot_id)}
    if job.job_type == "run_multiverse_tick":
        multiverse = db.get(models.Multiverse, payload["multiverse_id"])
        if not multiverse:
            raise ValueError("multiverse not found")
        tick = run_next_tick(db, multiverse=multiverse, idempotency_key=payload.get("idempotency_key"))
        return {"tick_snapshot_id": str(tick.id), "ui_label": tick.ui_label}
    if job.job_type == "simulate_multiverse_ticks":
        multiverse = db.get(models.Multiverse, payload["multiverse_id"])
        if not multiverse:
            raise ValueError("multiverse not found")
        ticks = simulate_ticks(db, multiverse=multiverse, count=int(payload.get("count", 1)))
        return {"tick_snapshot_ids": [str(tick.id) for tick in ticks]}
    if job.job_type == "generate_multiverse_report":
        multiverse = db.get(models.Multiverse, payload["multiverse_id"])
        if not multiverse:
            raise ValueError("multiverse not found")
        report = generate_multiverse_report(db, multiverse=multiverse, title=payload.get("title"), summary=payload.get("summary"))
        return {"report_version_id": str(report.id)}
    if job.job_type == "generate_final_big_bang_report":
        big_bang = db.get(models.BigBang, job.big_bang_id or payload.get("big_bang_id"))
        if not big_bang:
            raise ValueError("big bang not found")
        report = generate_final_big_bang_report(db, big_bang=big_bang, title=payload.get("title"), summary=payload.get("summary"))
        return {"report_version_id": str(report.id)}
    if job.job_type == "run_big_bang_until_complete":
        big_bang = db.get(models.BigBang, job.big_bang_id or payload.get("big_bang_id"))
        if not big_bang:
            raise ValueError("big bang not found")
        return run_big_bang_until_complete(db, big_bang=big_bang, max_total_ticks=int(payload.get("max_total_ticks", 24)))
    return {"status": "recorded", "job_type": job.job_type, "payload": payload}
