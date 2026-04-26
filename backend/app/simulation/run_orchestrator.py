from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.simulation.report_engine import generate_final_big_bang_report, generate_multiverse_report
from app.simulation.tick_runner import run_next_tick


def simulate_ticks(db: Session, *, multiverse: models.Multiverse, count: int) -> list[models.TickSnapshot]:
    ticks = []
    for _ in range(max(0, count)):
        if multiverse.status not in {"active", "candidate"}:
            break
        try:
            ticks.append(run_next_tick(db, multiverse=multiverse))
        except ValueError:
            break
    return ticks


def run_big_bang_until_complete(db: Session, *, big_bang: models.BigBang, max_total_ticks: int = 24) -> dict:
    ticks_run = []
    for _ in range(max_total_ticks):
        active = db.scalars(
            select(models.Multiverse)
            .where(models.Multiverse.big_bang_id == big_bang.id, models.Multiverse.status == "active")
            .order_by(models.Multiverse.ui_label)
        ).all()
        if not active:
            break
        for multiverse in active:
            try:
                ticks_run.append(run_next_tick(db, multiverse=multiverse))
            except ValueError:
                continue
    multiverses = db.scalars(
        select(models.Multiverse)
        .where(models.Multiverse.big_bang_id == big_bang.id)
        .order_by(models.Multiverse.ui_label)
    ).all()
    report_versions = []
    for multiverse in multiverses:
        if multiverse.report_status in {"ready", "not_ready"}:
            report_versions.append(generate_multiverse_report(db, multiverse=multiverse))
    final_report = generate_final_big_bang_report(db, big_bang=big_bang)
    big_bang.status = "completed"
    return {
        "ticks_run": len(ticks_run),
        "multiverse_count": len(multiverses),
        "report_versions": [str(item.id) for item in report_versions],
        "final_report_version_id": str(final_report.id),
    }
