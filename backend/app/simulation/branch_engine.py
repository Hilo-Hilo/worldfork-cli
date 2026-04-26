from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.labels import next_child_label, tick_label
from app.db import models


def create_branch(
    db: Session,
    *,
    parent: models.Multiverse,
    fork_tick_index: int,
    reason: str,
    idempotency_key: str,
) -> models.Multiverse:
    existing_tool = db.scalar(select(models.ToolCall).where(models.ToolCall.idempotency_key == idempotency_key))
    if existing_tool and existing_tool.result.get("child_multiverse_id"):
        return db.get(models.Multiverse, existing_tool.result["child_multiverse_id"])

    config = db.scalar(
        select(models.BigBangConfig).where(models.BigBangConfig.big_bang_id == parent.big_bang_id).order_by(models.BigBangConfig.version.desc())
    )
    branch_policy = config.branch_policy if config else {}
    max_depth = branch_policy.get("max_branch_depth", 3)
    max_active = branch_policy.get("max_active_multiverses", 12)
    max_per_tick = branch_policy.get("max_branches_per_tick", 2)

    active_count = db.scalar(
        select(func.count()).select_from(models.Multiverse).where(
            models.Multiverse.big_bang_id == parent.big_bang_id,
            models.Multiverse.status == "active",
        )
    )
    if active_count >= max_active:
        raise ValueError("branch budget exceeded: max_active_multiverses")
    if parent.depth + 1 > max_depth:
        raise ValueError("branch budget exceeded: max_branch_depth")

    tick_branch_count = db.scalar(
        select(func.count()).select_from(models.MultiverseLineageEdge).where(
            models.MultiverseLineageEdge.parent_multiverse_id == parent.id,
            models.MultiverseLineageEdge.fork_tick_index == fork_tick_index,
        )
    )
    if tick_branch_count >= max_per_tick:
        raise ValueError("branch budget exceeded: max_branches_per_tick")

    child_count = db.scalar(
        select(func.count()).select_from(models.Multiverse).where(models.Multiverse.parent_multiverse_id == parent.id)
    )
    child_label = next_child_label(parent.ui_label, child_count)
    child = models.Multiverse(
        big_bang_id=parent.big_bang_id,
        parent_multiverse_id=parent.id,
        fork_tick_index=fork_tick_index,
        ui_label=child_label,
        depth=parent.depth + 1,
        status="active",
        branch_reason=reason,
        state=dict(parent.state or {}),
    )
    db.add(child)
    db.flush()
    db.add(models.MultiverseLineageEdge(
        big_bang_id=parent.big_bang_id,
        parent_multiverse_id=parent.id,
        child_multiverse_id=child.id,
        fork_tick_index=fork_tick_index,
        reason=reason,
    ))

    inherited_ticks = db.scalars(
        select(models.TickSnapshot).where(
            models.TickSnapshot.multiverse_id == parent.id,
            models.TickSnapshot.tick_index <= fork_tick_index,
        ).order_by(models.TickSnapshot.tick_index)
    ).all()
    for tick in inherited_ticks:
        db.add(models.TickLineageRef(
            child_multiverse_id=child.id,
            source_multiverse_id=parent.id,
            source_tick_snapshot_id=tick.id,
            inherited_tick_index=tick.tick_index,
            inherited_ui_label=tick_label(child.ui_label, tick.tick_index),
        ))
    db.flush()
    return child
