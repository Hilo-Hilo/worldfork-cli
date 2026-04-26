from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.api.schemas import BigBangCreate
from app.core.config import get_settings
from app.core.labels import tick_label
from app.db import models
from app.llm.prompt_builder import sanitize_sociology_prompt_influences
from app.simulation.initialization_corpus import build_plain_text_corpus
from app.simulation.initializer_agent import merge_initializer_lists, run_initializer_agent
from app.simulation.source_truth_validation import normalize_initializer_against_source_of_truth
from app.source_of_truth.snapshotter import snapshot_source_of_truth
from app.storage.artifact_store import ArtifactStore


def default_simulation_config(overrides: dict) -> dict:
    settings = get_settings()
    base = {
        "tick_duration": settings.default_tick_duration,
        "max_ticks": settings.default_max_ticks,
    }
    base.update(overrides or {})
    return base


def default_model_config(overrides: dict) -> dict:
    settings = get_settings()
    base = {
        "provider": settings.default_llm_provider,
        "default_model": settings.default_model,
        "initializer_agent_model": settings.initializer_agent_model,
        "god_agent_model": settings.god_agent_model,
        "cohort_agent_model": settings.cohort_agent_model,
        "hero_agent_model": settings.hero_agent_model,
        "event_summary_model": settings.event_summary_model,
        "report_agent_model": settings.report_agent_model,
    }
    base.update(overrides or {})
    return base


def default_branch_policy(overrides: dict) -> dict:
    settings = get_settings()
    base = {
        "max_branch_depth": settings.default_max_branch_depth,
        "max_active_multiverses": settings.default_max_active_multiverses,
        "max_branches_per_tick": settings.default_max_branches_per_tick,
        "branch_score_threshold": settings.branch_score_threshold,
    }
    base.update(overrides or {})
    return base


def create_big_bang(db: Session, payload: BigBangCreate) -> models.BigBang:
    simulation_config = default_simulation_config(payload.simulation_config)
    model_config = default_model_config(payload.llm_model_config)
    branch_policy = default_branch_policy(payload.branch_policy)
    scenario_text = payload.scenario_text or payload.scenario_input.get("prompt") or payload.scenario_input.get("premise") or ""
    scenario_input = {
        **payload.scenario_input,
        "scenario_text": scenario_text,
    }
    big_bang = models.BigBang(
        name=payload.name,
        description=payload.description,
        scenario_input=scenario_input,
        status="draft",
        current_config_version=1,
    )
    db.add(big_bang)
    db.flush()

    snapshot = snapshot_source_of_truth(db, big_bang.id)
    big_bang.source_snapshot_id = snapshot.id
    initializer_output = {}
    plain_text_corpus = {}
    if scenario_text:
        plain_text_corpus = build_plain_text_corpus(db, big_bang=big_bang, scenario_text=scenario_text)
    if payload.use_initializer_agent and scenario_text:
        initializer_output = run_initializer_agent(
            db,
            big_bang_id=big_bang.id,
            scenario_input=scenario_input,
            plain_text_corpus=plain_text_corpus,
            initializer_prompt=payload.initializer_prompt,
        )
        initializer_output = normalize_initializer_against_source_of_truth(initializer_output)
        big_bang.scenario_input = {
            **scenario_input,
            "plain_text_corpus": plain_text_corpus,
            "initializer_output": initializer_output,
        }

    generated_actors = initializer_output.get("actors", [])
    generated_cohorts = initializer_output.get("cohort_states") or initializer_output.get("cohorts", [])
    generated_heroes = initializer_output.get("hero_archetypes") or initializer_output.get("heroes", [])
    actors = merge_initializer_lists(generated_actors, payload.actors)
    cohorts = merge_initializer_lists(generated_cohorts, payload.cohorts)
    heroes = merge_initializer_lists(generated_heroes, payload.heroes)

    config_artifact = ArtifactStore().write_json(
        db,
        big_bang_id=big_bang.id,
        relative_path=f"big_bang_{big_bang.id}/configs/simulation_config_v1.json",
        payload={
            "simulation_config": simulation_config,
            "model_config": model_config,
            "branch_policy": branch_policy,
            "plain_text_corpus": plain_text_corpus,
            "initializer_output": initializer_output,
        },
        kind="big_bang_config",
    )
    db.add(models.BigBangConfig(
        big_bang_id=big_bang.id,
        version=1,
        simulation_config=simulation_config,
        model_config=model_config,
        branch_policy=branch_policy,
        artifact_id=config_artifact.id,
    ))
    db.add(models.BigBangConfigVersion(
        big_bang_id=big_bang.id,
        version=1,
        simulation_config=simulation_config,
        model_config=model_config,
        branch_policy=branch_policy,
        artifact_id=config_artifact.id,
    ))

    actor_by_name = {}
    for item in actors:
        actor = models.Actor(
            big_bang_id=big_bang.id,
            actor_type=item.get("actor_type", "entity"),
            name=item.get("name", "Unnamed actor"),
            description=item.get("description"),
            archetype=item,
            created_tick_index=0,
        )
        db.add(actor)
        db.flush()
        actor_by_name[actor.name.lower()] = actor

    for item in initializer_output.get("population_archetypes", []):
        if isinstance(item, dict):
            db.add(models.PopulationArchetype(
                big_bang_id=big_bang.id,
                name=item.get("name", "Generated population archetype"),
                definition=item.get("definition", item),
            ))

    root = models.Multiverse(
        big_bang_id=big_bang.id,
        parent_multiverse_id=None,
        fork_tick_index=None,
        ui_label="M1",
        depth=0,
        status="active",
        branch_reason="Root timeline",
        state={
            "scenario_input": big_bang.scenario_input,
            "cohorts": cohorts,
            "heroes": heroes,
            "channels": initializer_output.get("channels", []),
            "trait_vectors": initializer_output.get("trait_vectors", []),
            "branch_hypotheses": initializer_output.get("branch_hypotheses", []),
            "merge_hypotheses": initializer_output.get("merge_hypotheses", []),
            "plain_text_corpus": plain_text_corpus,
            "initializer_output": initializer_output,
        },
    )
    db.add(root)
    db.flush()

    for item in cohorts:
        actor = actor_by_name.get(str(item.get("name", "")).lower())
        db.add(models.CohortState(
            big_bang_id=big_bang.id,
            multiverse_id=root.id,
            actor_id=actor.id if actor else None,
            tick_index=0,
            state=item.get("state", item),
            queued_event_ids=[],
        ))

    for item in heroes:
        actor = actor_by_name.get(str(item.get("name", "")).lower())
        hero = models.HeroArchetype(
            big_bang_id=big_bang.id,
            actor_id=actor.id if actor else None,
            name=item.get("name", "Generated hero"),
            definition=item.get("definition", item),
        )
        db.add(hero)
        db.add(models.HeroState(
            big_bang_id=big_bang.id,
            multiverse_id=root.id,
            actor_id=actor.id if actor else None,
            tick_index=0,
            state=item.get("state", item),
            queued_event_ids=[],
        ))

    persist_initializer_graphs_and_observability(
        db,
        big_bang=big_bang,
        root=root,
        actor_by_name=actor_by_name,
        initializer_output=initializer_output,
    )

    for item in _dict_items(initializer_output.get("initial_events", [])):
        if not isinstance(item, dict):
            continue
        event = models.Event(
            big_bang_id=big_bang.id,
            multiverse_id=root.id,
            creator_actor_id=None,
            event_type=item.get("event_type", "announcement"),
            created_tick=0,
            scheduled_tick=_safe_int(item.get("scheduled_tick"), 1, low=0),
            status="queued",
            title=item.get("title", "Initializer event"),
            description=item.get("description"),
            expected_impact=item.get("expected_impact", {}),
            meta={"source": "initializer_agent"},
        )
        db.add(event)
        db.flush()
        revision = models.EventRevision(
            event_id=event.id,
            revision_number=1,
            edited_by_agent_type="initializer_agent",
            edit_reason="initialization",
            title=event.title,
            description=event.description,
            scheduled_tick=event.scheduled_tick,
            preconditions=item.get("preconditions", {}),
            expected_impact=event.expected_impact,
        )
        db.add(revision)
        db.flush()
        event.current_revision_id = revision.id

    initial_tick = models.TickSnapshot(
        big_bang_id=big_bang.id,
        multiverse_id=root.id,
        tick_index=0,
        ui_label=tick_label(root.ui_label, 0),
        status="final",
        provisional_bundle={"kind": "initial_state"},
        final_bundle={
            "state": root.state,
            "plain_text_corpus": plain_text_corpus,
            "initializer_output": initializer_output,
            "message": "Initial Big Bang state.",
        },
        summary="Initial Big Bang state.",
        idempotency_key=f"{root.id}:tick:0",
    )
    db.add(initial_tick)
    db.flush()
    artifact = ArtifactStore().write_json(
        db,
        big_bang_id=big_bang.id,
        relative_path=f"big_bang_{big_bang.id}/multiverses/M1/ticks/T0.json",
        payload=initial_tick.final_bundle,
        kind="tick_snapshot",
    )
    initial_tick.artifact_id = artifact.id
    db.flush()
    return big_bang


def persist_initializer_graphs_and_observability(
    db: Session,
    *,
    big_bang: models.BigBang,
    root: models.Multiverse,
    actor_by_name: dict[str, models.Actor],
    initializer_output: dict,
) -> None:
    for item in _dict_items(initializer_output.get("trait_vectors", [])):
        actor = actor_by_name.get(str(item.get("actor_name") or item.get("name") or "").lower())
        if actor:
            actor.archetype = {**(actor.archetype or {}), "trait_vector": item}

    graph_by_layer: dict[str, list[dict]] = {}
    for item in _dict_items(initializer_output.get("graph_edges", [])):
        source = actor_by_name.get(str(item.get("source_actor_name") or item.get("source") or "").lower())
        target = actor_by_name.get(str(item.get("target_actor_name") or item.get("target") or "").lower())
        layer = item.get("layer") or item.get("graph_layer") or "influence"
        weight = _safe_float(item.get("weight"), 0.5, low=0.0, high=1.0)
        edge = models.GraphEdge(
            big_bang_id=big_bang.id,
            multiverse_id=root.id,
            tick_index=0,
            source_actor_id=source.id if source else None,
            target_actor_id=target.id if target else None,
            layer=layer,
            weight=weight,
            payload={
                "reason": item.get("reason"),
                "evidence": item.get("evidence"),
                "direction": item.get("direction", "directed"),
                "initializer": item,
            },
        )
        db.add(edge)
        graph_by_layer.setdefault(layer, []).append(
            {
                "source": source.name if source else item.get("source_actor_name"),
                "target": target.name if target else item.get("target_actor_name"),
                "weight": weight,
                "reason": item.get("reason"),
            }
        )

    for layer, edges in graph_by_layer.items():
        db.add(models.GraphSnapshot(
            big_bang_id=big_bang.id,
            multiverse_id=root.id,
            tick_index=0,
            layer=layer,
            graph={"layer": layer, "tick_index": 0, "edges": edges},
        ))
    root.state = {
        **(root.state or {}),
        "graph_summary": {
            layer: {
                "edge_count": len(edges),
                "average_weight": sum(edge["weight"] for edge in edges) / max(1, len(edges)),
                "max_weight": max([edge["weight"] for edge in edges] or [0]),
                "notable_edges": edges[:5],
            }
            for layer, edges in graph_by_layer.items()
        },
    }

    emotion_values = []
    for item in _dict_items(initializer_output.get("emotion_observations", [])):
        actor = actor_by_name.get(str(item.get("actor_name") or item.get("name") or "").lower())
        value = _safe_float(item.get("value"), 0.0, low=0.0, high=10.0)
        observation = models.EmotionObservation(
            big_bang_id=big_bang.id,
            multiverse_id=root.id,
            tick_index=0,
            actor_id=actor.id if actor else None,
            emotion=item.get("emotion") or item.get("emotion_key"),
            value=value,
            source=item.get("source", "initializer_agent"),
            evidence={
                "initializer": item,
                "prompt_feedback_eligible": False,
                "explanation": item.get("explanation"),
            },
        )
        db.add(observation)
        emotion_values.append(
            {
                "actor": actor.name if actor else item.get("actor_name"),
                "emotion": observation.emotion,
                "value": value,
                "prompt_feedback_eligible": False,
            }
        )
    if emotion_values:
        db.add(models.EmotionGraphSnapshot(
            big_bang_id=big_bang.id,
            multiverse_id=root.id,
            tick_index=0,
            graph={"policy": "observability_only_not_prompt_feedback", "values": emotion_values},
        ))

    for item in _dict_items(initializer_output.get("sociology_baseline", [])):
        db.add(models.SociologySignal(
            big_bang_id=big_bang.id,
            multiverse_id=root.id,
            tick_index=0,
            model=item.get("model", "attention_decay"),
            signal=item.get("signal", item),
        ))
    for item in sanitize_sociology_prompt_influences(_dict_items(initializer_output.get("sociology_prompt_influences", []))):
        actor = actor_by_name.get(str(item.get("actor_name") or "").lower())
        influence = item.get("influence", item)
        if not isinstance(influence, dict) or not influence:
            continue
        db.add(models.SociologyPromptInfluence(
            big_bang_id=big_bang.id,
            multiverse_id=root.id,
            actor_id=actor.id if actor else None,
            tick_index=0,
            applies_to_tick_index=1,
            influence=influence,
        ))


def _dict_items(value) -> list[dict]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    return [item for item in items if isinstance(item, dict)]


def _safe_int(value, default: int, *, low: int | None = None, high: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        match = re.search(r"-?\d+", str(value))
        parsed = int(match.group(0)) if match else default
    if low is not None:
        parsed = max(low, parsed)
    if high is not None:
        parsed = min(high, parsed)
    return parsed


def _safe_float(
    value,
    default: float,
    *,
    low: float | None = None,
    high: float | None = None,
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        match = re.search(r"-?\d+(?:\.\d+)?", str(value))
        parsed = float(match.group(0)) if match else default
    if low is not None:
        parsed = max(low, parsed)
    if high is not None:
        parsed = min(high, parsed)
    return parsed
