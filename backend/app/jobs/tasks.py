from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from app.api.schemas import BigBangCreate
from app.db import models
from app.jobs.queues import JOB_TYPES
from app.simulation.initializer import create_big_bang
from app.simulation.tick_runner import run_next_tick


CLAIMABLE_STATUSES = {"queued"}
JOB_LEASE_SECONDS = 15 * 60


class JobNotRunnableError(RuntimeError):
    pass


def validate_job_type(job_type: str) -> None:
    if job_type not in JOB_TYPES:
        raise ValueError(f"unknown job_type: {job_type}")


def validate_job_payload(job_type: str, payload: dict | None, *, big_bang_id=None) -> None:
    validate_job_type(job_type)
    payload = payload or {}
    if job_type == "initialize_big_bang":
        try:
            BigBangCreate(**payload)
        except ValidationError as exc:
            raise ValueError(f"invalid initialize_big_bang payload: {exc}") from exc
        return
    multiverse_job_types = {
        "run_multiverse_tick",
        "simulate_multiverse_ticks",
        "generate_multiverse_report",
    }
    if job_type in multiverse_job_types:
        _require_uuid_payload(payload, "multiverse_id")
    if job_type in {"generate_final_big_bang_report", "run_big_bang_until_complete"}:
        _require_big_bang_id(payload, big_bang_id)
    if job_type == "simulate_multiverse_ticks" and "count" in payload:
        _require_positive_int(payload["count"], "count")
    if job_type == "run_big_bang_until_complete" and "max_total_ticks" in payload:
        _require_positive_int(payload["max_total_ticks"], "max_total_ticks")


def execute_job(db: Session, job: models.Job, *, commit_running: bool = False) -> models.Job:
    validate_job_type(job.job_type)
    if not claim_job_for_execution(db, job):
        raise JobNotRunnableError(
            f"job {job.id} is {job.status}; only queued or expired running jobs can run"
        )
    if job.job_type == "run_big_bang_until_complete":
        job.result = {
            **(job.result or {}),
            "phase": "claimed",
            "progress": {"percent": 0},
        }
    if commit_running:
        db.commit()
        db.refresh(job)
    try:
        validate_job_payload(job.job_type, job.payload, big_bang_id=job.big_bang_id)
        if job.job_type == "run_big_bang_until_complete":
            result = _execute_run_big_bang_until_complete_job(db, job)
        else:
            with db.begin_nested():
                result = _execute_job(db, job)
        job.result = result
        job.error = None
        job.status = "succeeded"
    except Exception as exc:
        if isinstance(job.result, dict) and job.result:
            job.result = {**job.result, "stopped_reason": "failed", "error": str(exc)}
        else:
            job.result = {}
        job.error = str(exc)
        job.status = "failed"
    db.flush()
    return job


def claim_job_for_execution(
    db: Session,
    job: models.Job,
    *,
    now: datetime | None = None,
) -> bool:
    lease_cutoff = running_job_lease_cutoff(now)
    result = db.execute(
        update(models.Job)
        .where(
            models.Job.id == job.id,
            or_(
                models.Job.status.in_(CLAIMABLE_STATUSES),
                and_(models.Job.status == "running", models.Job.updated_at <= lease_cutoff),
            ),
        )
        .values(status="running", error=None)
        .execution_options(synchronize_session=False)
    )
    db.flush()
    if result.rowcount != 1:
        db.refresh(job)
        return False
    job.status = "running"
    job.error = None
    return True


def running_job_lease_cutoff(now: datetime | None = None) -> datetime:
    current = now or datetime.now(timezone.utc)
    return current - timedelta(seconds=JOB_LEASE_SECONDS)


def job_should_enqueue_for_retry(job: models.Job, *, now: datetime | None = None) -> bool:
    if job.status == "queued":
        return True
    if job.status != "running":
        return False
    updated_at = getattr(job, "updated_at", None)
    if updated_at is None:
        return False
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)
    return updated_at <= running_job_lease_cutoff(now)


def _execute_job(db: Session, job: models.Job) -> dict:
    payload = job.payload or {}
    if job.job_type == "initialize_big_bang":
        big_bang = create_big_bang(db, BigBangCreate(**payload))
        return {
            "big_bang_id": str(big_bang.id),
            "source_snapshot_id": str(big_bang.source_snapshot_id),
        }
    if job.job_type == "run_multiverse_tick":
        multiverse = db.get(models.Multiverse, payload["multiverse_id"])
        if not multiverse:
            raise ValueError("multiverse not found")
        tick = run_next_tick(
            db,
            multiverse=multiverse,
            idempotency_key=payload.get("idempotency_key"),
        )
        return {"tick_snapshot_id": str(tick.id), "ui_label": tick.ui_label}
    if job.job_type == "simulate_multiverse_ticks":
        from app.simulation.run_orchestrator import simulate_ticks

        multiverse = db.get(models.Multiverse, payload["multiverse_id"])
        if not multiverse:
            raise ValueError("multiverse not found")
        ticks = simulate_ticks(db, multiverse=multiverse, count=int(payload.get("count", 1)))
        return {"tick_snapshot_ids": [str(tick.id) for tick in ticks]}
    if job.job_type == "generate_multiverse_report":
        from app.simulation.report_engine import generate_multiverse_report

        multiverse = db.get(models.Multiverse, payload["multiverse_id"])
        if not multiverse:
            raise ValueError("multiverse not found")
        report = generate_multiverse_report(
            db,
            multiverse=multiverse,
            title=payload.get("title"),
            summary=payload.get("summary"),
        )
        return {"report_version_id": str(report.id)}
    if job.job_type == "generate_final_big_bang_report":
        from app.simulation.report_engine import generate_final_big_bang_report

        big_bang = db.get(models.BigBang, job.big_bang_id or payload.get("big_bang_id"))
        if not big_bang:
            raise ValueError("big bang not found")
        report = generate_final_big_bang_report(
            db,
            big_bang=big_bang,
            title=payload.get("title"),
            summary=payload.get("summary"),
        )
        return {"report_version_id": str(report.id)}
    if job.job_type == "run_big_bang_until_complete":
        from app.simulation.run_orchestrator import run_big_bang_until_complete

        big_bang = db.get(models.BigBang, job.big_bang_id or payload.get("big_bang_id"))
        if not big_bang:
            raise ValueError("big bang not found")
        return run_big_bang_until_complete(
            db,
            big_bang=big_bang,
            max_total_ticks=int(payload.get("max_total_ticks", 24)),
        )
    raise NotImplementedError(f"job_type has no executor: {job.job_type}")


def _execute_run_big_bang_until_complete_job(db: Session, job: models.Job) -> dict:
    from sqlalchemy import func

    from app.simulation.report_engine import generate_final_big_bang_report, generate_multiverse_report
    from app.simulation.tick_runner import TERMINAL_MULTIVERSE_STATUSES, UNFINISHED_TICK_STATUSES

    payload = job.payload or {}
    max_total_ticks = int(payload.get("max_total_ticks", 24))
    if max_total_ticks < 1:
        raise ValueError("max_total_ticks must be a positive integer")

    big_bang = db.get(models.BigBang, job.big_bang_id or payload.get("big_bang_id"))
    if not big_bang:
        raise ValueError("big bang not found")
    if big_bang.status == "paused":
        raise ValueError("big bang is paused")

    tick_ids: list[str] = []
    latest_tick_id: str | None = None
    latest_tick_label: str | None = None
    stopped_reason: str | None = None

    def make_progress(stopped: str | None = None, phase: str = "running", current_multiverse=None) -> dict:
        multiverse_count = db.scalar(
            select(func.count(models.Multiverse.id)).where(models.Multiverse.big_bang_id == big_bang.id)
        )
        return {
            "big_bang_id": str(big_bang.id),
            "phase": phase,
            "ticks_run": len(tick_ids),
            "latest_tick_id": latest_tick_id,
            "latest_tick_label": latest_tick_label,
            "current_multiverse_id": str(current_multiverse.id) if current_multiverse is not None else None,
            "current_multiverse_label": current_multiverse.ui_label if current_multiverse is not None else None,
            "multiverse_count": int(multiverse_count or 0),
            "stopped_reason": stopped,
            "progress": {
                "completed_ticks": len(tick_ids),
                "requested_ticks": max_total_ticks,
                "percent": min(100, round((len(tick_ids) / max_total_ticks) * 100, 2)),
            },
        }

    job.result = make_progress(phase="starting")
    db.add(job)
    db.flush()
    db.commit()

    for _ in range(max_total_ticks):
        active_multiverses = db.scalars(
            select(models.Multiverse)
            .where(
                models.Multiverse.big_bang_id == big_bang.id,
                ~models.Multiverse.status.in_(TERMINAL_MULTIVERSE_STATUSES),
            )
            .order_by(models.Multiverse.created_at.asc())
        ).all()
        if not active_multiverses:
            stopped_reason = "all_multiverses_terminal"
            break

        made_progress = False
        for multiverse in active_multiverses:
            job.result = make_progress(phase="running_tick", current_multiverse=multiverse)
            db.add(job)
            db.flush()
            db.commit()
            tick = run_next_tick(db, multiverse=multiverse)
            if tick.status in UNFINISHED_TICK_STATUSES:
                continue
            tick_id = str(tick.id)
            if tick_id in tick_ids:
                continue
            tick_ids.append(tick_id)
            latest_tick_id = tick_id
            latest_tick_label = tick.ui_label
            made_progress = True
            job.result = make_progress(phase="tick_committed", current_multiverse=multiverse)
            db.add(job)
            db.flush()
            db.commit()

        if not made_progress:
            stopped_reason = "no_tick_progress"
            break

    multiverses = db.scalars(
        select(models.Multiverse)
        .where(models.Multiverse.big_bang_id == big_bang.id)
        .order_by(models.Multiverse.created_at.asc())
    ).all()
    unfinished_ticks = db.scalar(
        select(func.count(models.TickSnapshot.id)).where(
            models.TickSnapshot.big_bang_id == big_bang.id,
            models.TickSnapshot.status.in_(UNFINISHED_TICK_STATUSES),
        )
    )
    non_terminal = [mv for mv in multiverses if mv.status not in TERMINAL_MULTIVERSE_STATUSES]

    report_version_ids: list[str] = []
    final_report_version_id: str | None = None
    if not unfinished_ticks and not non_terminal and multiverses:
        for multiverse in multiverses:
            report_version = generate_multiverse_report(db, multiverse=multiverse)
            report_version_ids.append(str(report_version.id))
        final_report_version = generate_final_big_bang_report(db, big_bang=big_bang)
        final_report_version_id = str(final_report_version.id)
        big_bang.status = "completed"
        stopped_reason = "completed"
    elif stopped_reason is None:
        stopped_reason = "max_total_ticks_reached"

    result = make_progress(stopped_reason)
    result["report_version_ids"] = report_version_ids
    result["final_report_version_id"] = final_report_version_id
    return result


def _require_uuid_payload(payload: dict, key: str) -> UUID:
    value = payload.get(key)
    if value is None or value == "":
        raise ValueError(f"{key} is required")
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except ValueError as exc:
        raise ValueError(f"{key} must be a UUID") from exc


def _require_big_bang_id(payload: dict, big_bang_id) -> UUID:
    value = big_bang_id or payload.get("big_bang_id")
    if value is None or value == "":
        raise ValueError("big_bang_id is required")
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except ValueError as exc:
        raise ValueError("big_bang_id must be a UUID") from exc


def _require_positive_int(value, key: str) -> None:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a positive integer") from exc
    if parsed < 1:
        raise ValueError(f"{key} must be a positive integer")
