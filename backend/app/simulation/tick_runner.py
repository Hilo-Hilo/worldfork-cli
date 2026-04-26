from __future__ import annotations

from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.clock import build_clock_context
from app.core.labels import tick_label
from app.db import models
from app.llm.prompt_builder import build_agent_prompt_context
from app.simulation.agent_engine import apply_social_actions, queue_agent_events, run_agent_decisions
from app.simulation.cohort_engine import (
    generate_emergence_candidates,
    generate_merge_candidates,
    generate_split_candidates,
)
from app.simulation.emotion_observability_engine import update_emotion_observability_graphs
from app.simulation.event_engine import execute_due_events, load_due_events, summarize_executed_events
from app.simulation.god_agent import review_provisional_tick
from app.simulation.god_tools import execute_tool_call
from app.simulation.graph_engine import update_graph_layers
from app.simulation.sociology_engine import run_sociology_update
from app.storage.artifact_store import ArtifactStore


UNFINISHED_TICK_STATUSES = {"running", "provisional"}
RUNNABLE_MULTIVERSE_STATUSES = {"active", "candidate"}
TERMINAL_MULTIVERSE_STATUSES = {"completed", "terminated"}


def run_next_tick(
    db: Session,
    *,
    multiverse: models.Multiverse,
    idempotency_key: str | None = None,
    force: bool = False,
) -> models.TickSnapshot:
    locked_multiverse = db.scalar(
        select(models.Multiverse)
        .where(models.Multiverse.id == multiverse.id)
        .with_for_update()
    )
    if locked_multiverse:
        multiverse = locked_multiverse

    big_bang = db.get(models.BigBang, multiverse.big_bang_id)
    if big_bang and big_bang.status == "paused":
        raise ValueError("big bang is paused")
    if multiverse.status not in RUNNABLE_MULTIVERSE_STATUSES:
        raise ValueError(f"multiverse is {multiverse.status}; only active or candidate timelines can run")

    latest_tick = db.scalar(
        select(models.TickSnapshot)
        .where(models.TickSnapshot.multiverse_id == multiverse.id)
        .order_by(models.TickSnapshot.tick_index.desc())
        .limit(1)
    )
    if latest_tick and latest_tick.status in UNFINISHED_TICK_STATUSES:
        return latest_tick

    next_index = 0 if latest_tick is None else latest_tick.tick_index + 1
    key = idempotency_key or f"{multiverse.id}:tick:{next_index}"
    existing = db.scalar(
        select(models.TickSnapshot).where(
            models.TickSnapshot.big_bang_id == multiverse.big_bang_id,
            models.TickSnapshot.multiverse_id == multiverse.id,
            models.TickSnapshot.idempotency_key == key,
        )
    )
    if existing:
        if existing.status in UNFINISHED_TICK_STATUSES or not force:
            return existing
        key = _force_idempotency_key(db, multiverse=multiverse, base_key=key, tick_index=next_index)

    config = db.scalar(
        select(models.BigBangConfig)
        .where(models.BigBangConfig.big_bang_id == multiverse.big_bang_id)
        .order_by(models.BigBangConfig.version.desc())
        .limit(1)
    )
    simulation_config = (config.simulation_config or {}) if config else {}
    branch_policy = (config.branch_policy or {}) if config else {}
    max_ticks = simulation_config.get("max_ticks", 12)
    if next_index > max_ticks:
        multiverse.status = "completed"
        multiverse.report_status = "ready"
        db.flush()
        raise ValueError("multiverse has reached max_ticks")

    savepoint = db.begin_nested()
    try:
        tick = models.TickSnapshot(
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_index=next_index,
            ui_label=tick_label(multiverse.ui_label, next_index),
            status="running",
            provisional_bundle={},
            final_bundle={},
            summary=f"Tick {next_index} simulation in progress for {multiverse.ui_label}.",
            idempotency_key=key,
        )
        try:
            with db.begin_nested():
                db.add(tick)
                db.flush()
        except IntegrityError:
            existing = db.scalar(
                select(models.TickSnapshot).where(
                    models.TickSnapshot.big_bang_id == multiverse.big_bang_id,
                    models.TickSnapshot.multiverse_id == multiverse.id,
                    models.TickSnapshot.tick_index == next_index,
                )
            )
            if existing:
                existing_id = existing.id
                savepoint.rollback()
                return db.get(models.TickSnapshot, existing_id)
            raise

        clock = build_clock_context(next_index, simulation_config.get("tick_duration", "1 day"))
        prior_influences = db.scalars(
            select(models.SociologyPromptInfluence).where(
                models.SociologyPromptInfluence.multiverse_id == multiverse.id,
                models.SociologyPromptInfluence.applies_to_tick_index == next_index,
            )
        ).all()
        prompt_context = build_agent_prompt_context(
            clock_context=clock,
            current_state=multiverse.state or {},
            sociology_prompt_influences=[item.influence for item in prior_influences],
        )
        agent_result = run_agent_decisions(
            db,
            big_bang=big_bang,
            multiverse=multiverse,
            tick_index=next_index,
            prompt_context=prompt_context,
        )
        social_observations = apply_social_actions(
            db,
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_index=next_index,
            parsed_actions=agent_result["parsed_actions"],
        )
        queued_events = queue_agent_events(
            db,
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_index=next_index,
            parsed_actions=agent_result["parsed_actions"],
        )
        due_events = load_due_events(db, multiverse.id, next_index)
        executed_events = execute_due_events(db, due_events, tick_snapshot_id=tick.id)
        event_summaries = summarize_executed_events(
            db,
            due_events,
            tick_snapshot_id=tick.id,
            big_bang_id=multiverse.big_bang_id,
            local_tick_context={"clock": clock.as_prompt_text(), "social_observations": social_observations},
        )
        graphs = update_graph_layers(
            db,
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_index=next_index,
            social_observations=social_observations,
            executed_events=executed_events,
        )
        sociology_result = run_sociology_update(
            db,
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_index=next_index,
            executed_events=executed_events,
            social_observations=social_observations,
        )
        emotion_graph = update_emotion_observability_graphs(
            db,
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_index=next_index,
            emotion_self_ratings=agent_result["emotion_self_ratings"],
            event_summaries=event_summaries,
        )
        split_candidates = generate_split_candidates(
            db,
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_index=next_index,
            sociology_result=sociology_result,
        )
        merge_candidates = generate_merge_candidates(
            db,
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_index=next_index,
            sociology_result=sociology_result,
        )
        emergence_candidates = generate_emergence_candidates(
            db,
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_index=next_index,
            sociology_result=sociology_result,
        )
        candidate_scores = [
            float((item.get("payload") or {}).get("score") or 0)
            for item in [*split_candidates, *merge_candidates, *emergence_candidates]
        ]
        event_pressure = min(0.64, 0.24 + 0.12 * len(executed_events)) if executed_events else 0.0
        branch_score = round(max([event_pressure, *candidate_scores] or [0.0]), 4)
        idle_assessment = _assess_idle_state(
            multiverse_state=multiverse.state or {},
            branch_policy=branch_policy,
            branch_score=branch_score,
            queued_events=queued_events,
            executed_events=executed_events,
            social_observations=social_observations,
            split_candidates=split_candidates,
            merge_candidates=merge_candidates,
            emergence_candidates=emergence_candidates,
            sociology_result=sociology_result,
        )
        provisional = {
            "multiverse_id": str(multiverse.id),
            "tick_index": next_index,
            "clock": clock.as_prompt_text(),
            "agent_outputs": agent_result["actor_outputs"],
            "queued_events": queued_events,
            "social_observations": social_observations,
            "executed_events": executed_events,
            "event_summaries": event_summaries,
            "sociology_result": sociology_result,
            "graph_snapshots": graphs,
            "emotion_observability": emotion_graph,
            "split_candidates": split_candidates,
            "merge_candidates": merge_candidates,
            "emergence_candidates": emergence_candidates,
            "branch_score": branch_score,
            "idle_assessment": idle_assessment,
        }
        tick.status = "provisional"
        tick.provisional_bundle = provisional
        tick.summary = f"Tick {next_index} simulated for {multiverse.ui_label}."
        db.flush()

        review_payload, review_call = review_provisional_tick(db, multiverse, provisional)
        review = models.GodAgentReview(
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_snapshot_id=tick.id,
            decision=review_payload["decision"],
            rationale=review_payload["rationale"],
            confidence=review_payload["confidence"],
            input_summary=review_payload["input_summary"],
            output=review_payload,
        )
        db.add(review)
        db.flush()

        tool_results = []
        for call in review_payload["tool_calls"]:
            tool = execute_tool_call(
                db,
                big_bang_id=multiverse.big_bang_id,
                multiverse=multiverse,
                tick_snapshot_id=tick.id,
                god_review_id=review.id,
                tool_name=call["tool_name"],
                arguments=call.get("arguments", {}),
                idempotency_key=call.get("idempotency_key") or f"god:{review.id}:{call['tool_name']}",
            )
            tool_results.append(
                {"tool_name": tool.tool_name, "status": tool.status, "result": tool.result, "error": tool.error}
            )

        emotion_graph = update_emotion_observability_graphs(
            db,
            big_bang_id=multiverse.big_bang_id,
            multiverse_id=multiverse.id,
            tick_index=next_index,
            tick_snapshot_id=tick.id,
            emotion_self_ratings=[],
            event_summaries=event_summaries,
            god_agent_review=review_payload,
        )
        multiverse.state = {
            **(multiverse.state or {}),
            "last_tick_index": next_index,
            "last_executed_events": executed_events,
            "last_sociology": sociology_result,
            "graph_summary": sociology_result.get("graph_summary", {}),
            "cohort_current_states": sociology_result.get("cohort_state_updates", []),
            "hero_current_states": sociology_result.get("hero_state_updates", []),
            "idle_assessment": idle_assessment,
            "idle_streak": idle_assessment["idle_streak"],
        }
        final = {**provisional, "god_review_id": str(review.id), "god_review": review_payload, "tool_results": tool_results}
        final["emotion_observability_after_god_review"] = emotion_graph
        if review_call:
            final["god_review_llm_call_id"] = str(review_call.id)
        artifact = ArtifactStore().write_json(
            db,
            big_bang_id=multiverse.big_bang_id,
            relative_path=f"big_bang_{multiverse.big_bang_id}/multiverses/{multiverse.ui_label}/ticks/T{next_index}.json",
            payload=final,
            kind="tick_snapshot",
        )
        tick.status = "final"
        tick.final_bundle = final
        tick.artifact_id = artifact.id
        _sync_forked_children_after_tick(db, parent=multiverse, tick=tick)
        db.flush()
        savepoint.commit()
        return tick
    except Exception:
        savepoint.rollback()
        raise


def _sync_forked_children_after_tick(
    db: Session,
    *,
    parent: models.Multiverse,
    tick: models.TickSnapshot,
) -> None:
    children = db.scalars(
        select(models.Multiverse).where(
            models.Multiverse.parent_multiverse_id == parent.id,
            models.Multiverse.fork_tick_index == tick.tick_index,
        )
    ).all()
    for child in children:
        branch_state = deepcopy((child.state or {}).get("branch") or {})
        child.state = deepcopy(parent.state or {})
        child.state["branch"] = branch_state or {
            "parent_multiverse_id": str(parent.id),
            "fork_tick_index": tick.tick_index,
            "reason": child.branch_reason,
        }
        child_tick = db.scalar(
            select(models.TickSnapshot).where(
                models.TickSnapshot.multiverse_id == child.id,
                models.TickSnapshot.tick_index == tick.tick_index,
            )
        )
        if child_tick is None:
            child_tick = models.TickSnapshot(
                big_bang_id=parent.big_bang_id,
                multiverse_id=child.id,
                tick_index=tick.tick_index,
                ui_label=tick_label(child.ui_label, tick.tick_index),
                idempotency_key=f"{child.id}:tick:{tick.tick_index}:inherited",
            )
            db.add(child_tick)
        child_tick.status = tick.status
        child_tick.provisional_bundle = _inherited_tick_bundle(
            tick.provisional_bundle, parent=parent, child=child, tick=tick
        )
        child_tick.final_bundle = _inherited_tick_bundle(tick.final_bundle, parent=parent, child=child, tick=tick)
        child_tick.summary = tick.summary
        child_tick.artifact_id = None


def _force_idempotency_key(
    db: Session,
    *,
    multiverse: models.Multiverse,
    base_key: str,
    tick_index: int,
) -> str:
    prefix = f"{base_key}:force:{tick_index}"
    for attempt in range(1, 100):
        candidate = f"{prefix}:{attempt}"
        if len(candidate) > 160:
            candidate = f"{base_key[:120]}:force:{tick_index}:{attempt}"
        exists = db.scalar(
            select(models.TickSnapshot).where(
                models.TickSnapshot.big_bang_id == multiverse.big_bang_id,
                models.TickSnapshot.multiverse_id == multiverse.id,
                models.TickSnapshot.idempotency_key == candidate,
            )
        )
        if not exists:
            return candidate
    raise ValueError("unable to allocate unique forced tick idempotency key")


def _inherited_tick_bundle(
    bundle: dict | None,
    *,
    parent: models.Multiverse,
    child: models.Multiverse,
    tick: models.TickSnapshot,
) -> dict:
    inherited = deepcopy(bundle or {})
    inherited["multiverse_id"] = str(child.id)
    inherited["inherited_from"] = {
        "source_multiverse_id": str(parent.id),
        "source_tick_snapshot_id": str(tick.id),
        "source_ui_label": tick.ui_label,
    }
    return inherited


def _assess_idle_state(
    *,
    multiverse_state: dict,
    branch_policy: dict,
    branch_score: float,
    queued_events: list[dict],
    executed_events: list[dict],
    social_observations: list[dict],
    split_candidates: list[dict],
    merge_candidates: list[dict],
    emergence_candidates: list[dict],
    sociology_result: dict,
) -> dict:
    threshold = int(branch_policy.get("idle_termination_ticks", 5) or 5)
    metrics = sociology_result.get("metrics", {}) if isinstance(sociology_result, dict) else {}
    candidate_count = len(split_candidates) + len(merge_candidates) + len(emergence_candidates)
    low_motion = (
        branch_score <= 0.4
        and not queued_events
        and len(executed_events) <= 1
        and candidate_count == 0
        and len(social_observations) <= int(branch_policy.get("idle_social_observation_limit", 8) or 8)
        and float(metrics.get("mobilization_readiness") or 0) < 0.5
    )
    previous = int(multiverse_state.get("idle_streak") or 0)
    idle_streak = previous + 1 if low_motion else 0
    return {
        "is_idle_tick": low_motion,
        "idle_streak": idle_streak,
        "termination_threshold": threshold,
        "should_terminate": idle_streak >= threshold,
        "evidence": {
            "branch_score": branch_score,
            "queued_events": len(queued_events),
            "executed_events": len(executed_events),
            "social_observations": len(social_observations),
            "candidate_count": candidate_count,
            "mobilization_readiness": metrics.get("mobilization_readiness"),
        },
    }
