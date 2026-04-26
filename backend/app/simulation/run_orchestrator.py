from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.simulation.report_engine import generate_final_big_bang_report, generate_multiverse_report
from app.simulation.tick_runner import TERMINAL_MULTIVERSE_STATUSES, UNFINISHED_TICK_STATUSES, run_next_tick


def simulate_ticks(
    db: Session,
    *,
    multiverse: models.Multiverse,
    count: int,
    raise_on_domain_error: bool = False,
) -> list[models.TickSnapshot]:
    ticks = []
    for _ in range(max(0, count)):
        if multiverse.status not in {"active", "candidate"}:
            break
        try:
            tick = run_next_tick(db, multiverse=multiverse)
        except ValueError:
            if raise_on_domain_error:
                raise
            break
        if tick.status in UNFINISHED_TICK_STATUSES:
            break
        if ticks and ticks[-1].id == tick.id:
            break
        ticks.append(tick)
    return ticks


def run_big_bang_until_complete(db: Session, *, big_bang: models.BigBang, max_total_ticks: int = 24) -> dict:
    if big_bang.status == "paused":
        raise ValueError("big bang is paused")

    ticks_run = []
    for _ in range(max_total_ticks):
        active = db.scalars(
            select(models.Multiverse)
            .where(models.Multiverse.big_bang_id == big_bang.id, models.Multiverse.status == "active")
            .order_by(models.Multiverse.ui_label)
        ).all()
        if not active:
            break
        made_progress = False
        for multiverse in active:
            try:
                tick = run_next_tick(db, multiverse=multiverse)
            except ValueError:
                continue
            if tick.status in UNFINISHED_TICK_STATUSES:
                continue
            if any(existing.id == tick.id for existing in ticks_run):
                continue
            ticks_run.append(tick)
            made_progress = True
        if not made_progress:
            break
    multiverses = db.scalars(
        select(models.Multiverse)
        .where(models.Multiverse.big_bang_id == big_bang.id)
        .order_by(models.Multiverse.ui_label)
    ).all()
    unfinished_ticks = db.scalars(
        select(models.TickSnapshot).where(
            models.TickSnapshot.big_bang_id == big_bang.id,
            models.TickSnapshot.status.in_(UNFINISHED_TICK_STATUSES),
        )
    ).all()
    non_terminal = [item for item in multiverses if item.status not in TERMINAL_MULTIVERSE_STATUSES]
    if unfinished_ticks or non_terminal:
        raise ValueError("big bang has active or unfinished timelines")

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
