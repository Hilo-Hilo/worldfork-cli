from __future__ import annotations

from sqlalchemy.orm import Session

from app.db import models
from app.simulation.branch_engine import create_branch

VALID_TOOLS = {
    "continue_timeline",
    "freeze_timeline",
    "terminate_timeline",
    "create_branch",
    "approve_split",
    "reject_split",
    "plan_merge",
    "approve_merge_plan",
    "reject_merge_plan",
    "approve_emergence",
    "reject_emergence",
    "register_key_event",
    "request_event_summary_regeneration",
    "mark_ready_for_report",
}


def execute_tool_call(
    db: Session,
    *,
    big_bang_id,
    multiverse: models.Multiverse,
    tick_snapshot_id,
    god_review_id,
    tool_name: str,
    arguments: dict,
    idempotency_key: str,
) -> models.ToolCall:
    if tool_name not in VALID_TOOLS:
        raise ValueError(f"unknown God Agent tool: {tool_name}")
    tool_call = models.ToolCall(
        big_bang_id=big_bang_id,
        multiverse_id=multiverse.id,
        tick_snapshot_id=tick_snapshot_id,
        god_review_id=god_review_id,
        tool_name=tool_name,
        arguments=arguments,
        status="running",
        idempotency_key=idempotency_key,
    )
    db.add(tool_call)
    db.flush()
    try:
        result = _execute(db, multiverse=multiverse, tool_name=tool_name, arguments=arguments, idempotency_key=idempotency_key)
        tool_call.status = "succeeded"
        tool_call.result = result
    except Exception as exc:
        tool_call.status = "failed"
        tool_call.error = str(exc)
        tool_call.result = {}
    db.flush()
    return tool_call


def _execute(db: Session, *, multiverse: models.Multiverse, tool_name: str, arguments: dict, idempotency_key: str) -> dict:
    if tool_name == "continue_timeline":
        return {"status": "continued", "reason": arguments.get("reason")}
    if tool_name == "freeze_timeline":
        multiverse.status = "frozen"
        return {"status": "frozen"}
    if tool_name == "terminate_timeline":
        multiverse.status = "terminated"
        return {"status": "terminated"}
    if tool_name == "mark_ready_for_report":
        multiverse.report_status = "ready"
        return {"status": "ready_for_report"}
    if tool_name == "create_branch":
        child = create_branch(
            db,
            parent=multiverse,
            fork_tick_index=int(arguments["fork_tick_index"]),
            reason=arguments.get("reason", "God Agent branch."),
            idempotency_key=idempotency_key,
        )
        return {"status": "created", "child_multiverse_id": str(child.id), "child_label": child.ui_label}
    if tool_name == "register_key_event":
        event = db.get(models.Event, arguments.get("event_id")) if arguments.get("event_id") else None
        if event:
            event.meta = {**(event.meta or {}), "key_event": True, "key_event_reason": arguments.get("reason")}
        return {"status": "registered", "event_id": arguments.get("event_id")}
    if tool_name == "request_event_summary_regeneration":
        return {"status": "queued", "event_id": arguments.get("event_id")}
    if tool_name in {"approve_split", "reject_split"}:
        candidate_id = arguments.get("candidate_id")
        if not candidate_id:
            raise ValueError("split candidate_id is required")
        candidate = db.get(models.CohortSplitCandidate, candidate_id)
        if not candidate:
            raise ValueError("split candidate not found")
        candidate.status = "approved" if tool_name == "approve_split" else "rejected"
        if tool_name == "approve_split":
            split = models.CohortSplit(
                big_bang_id=multiverse.big_bang_id,
                multiverse_id=multiverse.id,
                tick_index=candidate.tick_index,
                status="persisted",
                payload={**candidate.payload, "approved_by": "god_agent"},
            )
            db.add(split)
            db.flush()
            return {"status": "approved", "split_id": str(split.id)}
        return {"status": "rejected", "candidate_id": str(candidate.id)}
    if tool_name == "plan_merge":
        candidate_id = arguments.get("candidate_id")
        if not candidate_id:
            raise ValueError("merge candidate_id is required")
        candidate = db.get(models.CohortMergeCandidate, candidate_id)
        if not candidate:
            raise ValueError("merge candidate not found")
        plan = models.CohortMergePlan(
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_index=candidate.tick_index,
            status="planned",
            payload={"candidate_id": str(candidate.id), "plan": arguments.get("plan", candidate.payload)},
        )
        db.add(plan)
        db.flush()
        return {"status": "planned", "merge_plan_id": str(plan.id)}
    if tool_name in {"approve_merge_plan", "reject_merge_plan"}:
        merge_plan_id = arguments.get("merge_plan_id")
        if not merge_plan_id:
            raise ValueError("merge_plan_id is required")
        plan = db.get(models.CohortMergePlan, merge_plan_id)
        if not plan:
            raise ValueError("merge plan not found")
        plan.status = "approved" if tool_name == "approve_merge_plan" else "rejected"
        if tool_name == "approve_merge_plan":
            merge = models.CohortMerge(
                big_bang_id=multiverse.big_bang_id,
                multiverse_id=multiverse.id,
                tick_index=plan.tick_index,
                status="persisted",
                payload=plan.payload,
            )
            db.add(merge)
            db.flush()
            return {"status": "approved", "merge_id": str(merge.id)}
        return {"status": "rejected", "merge_plan_id": str(plan.id)}
    if tool_name in {"approve_emergence", "reject_emergence"}:
        candidate_id = arguments.get("candidate_id")
        if not candidate_id:
            raise ValueError("emergence candidate_id is required")
        candidate = db.get(models.CohortEmergenceCandidate, candidate_id)
        if not candidate:
            raise ValueError("emergence candidate not found")
        candidate.status = "approved" if tool_name == "approve_emergence" else "rejected"
        if tool_name == "approve_emergence":
            emergence = models.CohortEmergence(
                big_bang_id=multiverse.big_bang_id,
                multiverse_id=multiverse.id,
                tick_index=candidate.tick_index,
                status="persisted",
                payload=candidate.payload,
            )
            db.add(emergence)
            db.flush()
            return {"status": "approved", "emergence_id": str(emergence.id)}
        return {"status": "rejected", "candidate_id": str(candidate.id)}
    return {"status": "recorded", "tool_name": tool_name, "arguments": arguments}
