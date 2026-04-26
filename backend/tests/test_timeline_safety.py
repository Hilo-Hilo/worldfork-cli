from __future__ import annotations

import importlib.util
import sys
import types
import warnings
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import models
from app.simulation import branch_engine, god_tools, tick_runner


@pytest.fixture()
def db() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    models.Base.metadata.create_all(engine)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Can't sort tables for DROP", category=SAWarning)
            models.Base.metadata.drop_all(engine)


def _seed_world(db: Session, *, max_ticks: int = 12) -> tuple[models.BigBang, models.Multiverse]:
    big_bang = models.BigBang(
        name="Timeline safety",
        description=None,
        scenario_input={},
        status="active",
        current_config_version=1,
    )
    db.add(big_bang)
    db.flush()
    db.add(
        models.BigBangConfig(
            big_bang_id=big_bang.id,
            version=1,
            simulation_config={"max_ticks": max_ticks},
            model_config={},
            branch_policy={},
        )
    )
    root = models.Multiverse(
        big_bang_id=big_bang.id,
        parent_multiverse_id=None,
        fork_tick_index=None,
        ui_label="M1",
        depth=0,
        status="active",
        branch_reason="Root timeline",
        state={},
    )
    db.add(root)
    db.flush()
    return big_bang, root


class _FakeArtifactStore:
    def write_json(self, db, *, big_bang_id, relative_path, payload, kind):
        artifact = models.Artifact(
            big_bang_id=big_bang_id,
            kind=kind,
            path=relative_path,
            content_type="application/json",
            content_hash="test",
            size_bytes=2,
            debug_only=False,
            meta={},
        )
        db.add(artifact)
        db.flush()
        return artifact


def _patch_successful_tick(monkeypatch):
    monkeypatch.setattr(
        tick_runner,
        "run_agent_decisions",
        lambda *args, **kwargs: {"parsed_actions": [], "actor_outputs": [], "emotion_self_ratings": []},
    )
    monkeypatch.setattr(tick_runner, "apply_social_actions", lambda *args, **kwargs: [])
    monkeypatch.setattr(tick_runner, "queue_agent_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(tick_runner, "load_due_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(tick_runner, "execute_due_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(tick_runner, "summarize_executed_events", lambda *args, **kwargs: [])
    monkeypatch.setattr(tick_runner, "update_graph_layers", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        tick_runner,
        "run_sociology_update",
        lambda *args, **kwargs: {
            "graph_summary": {},
            "cohort_state_updates": [],
            "hero_state_updates": [],
            "metrics": {},
        },
    )
    monkeypatch.setattr(tick_runner, "update_emotion_observability_graphs", lambda *args, **kwargs: {})
    monkeypatch.setattr(tick_runner, "generate_split_candidates", lambda *args, **kwargs: [])
    monkeypatch.setattr(tick_runner, "generate_merge_candidates", lambda *args, **kwargs: [])
    monkeypatch.setattr(tick_runner, "generate_emergence_candidates", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        tick_runner,
        "review_provisional_tick",
        lambda *args, **kwargs: (
            {
                "decision": "continue",
                "rationale": "test",
                "confidence": 1,
                "input_summary": {},
                "tool_calls": [],
            },
            None,
        ),
    )
    monkeypatch.setattr(tick_runner, "ArtifactStore", lambda: _FakeArtifactStore())


def _load_run_orchestrator_with_report_stub():
    report_engine_stub = types.ModuleType("app.simulation.report_engine")
    report_engine_stub.generate_final_big_bang_report = lambda *args, **kwargs: types.SimpleNamespace(id="final")
    report_engine_stub.generate_multiverse_report = lambda *args, **kwargs: types.SimpleNamespace(id="multiverse")
    original = sys.modules.get("app.simulation.report_engine")
    sys.modules["app.simulation.report_engine"] = report_engine_stub
    try:
        path = Path(__file__).parents[1] / "app" / "simulation" / "run_orchestrator.py"
        spec = importlib.util.spec_from_file_location("_timeline_safety_run_orchestrator", path)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module
    finally:
        if original is None:
            sys.modules.pop("app.simulation.report_engine", None)
        else:
            sys.modules["app.simulation.report_engine"] = original


def test_unfinished_tick_blocks_advancing(db):
    big_bang, root = _seed_world(db)
    unfinished = models.TickSnapshot(
        big_bang_id=big_bang.id,
        multiverse_id=root.id,
        tick_index=0,
        ui_label="M1-T0",
        status="provisional",
        provisional_bundle={},
        final_bundle={},
        summary="unfinished",
        idempotency_key="tick-0",
    )
    db.add(unfinished)
    db.commit()

    returned = tick_runner.run_next_tick(db, multiverse=root)
    run_orchestrator = _load_run_orchestrator_with_report_stub()
    many = run_orchestrator.simulate_ticks(db, multiverse=root, count=3)

    assert returned.id == unfinished.id
    assert many == []
    assert len(db.scalars(select(models.TickSnapshot).where(models.TickSnapshot.multiverse_id == root.id)).all()) == 1


def test_paused_big_bang_blocks_step_tick_and_run_until_complete(db):
    big_bang, root = _seed_world(db)
    big_bang.status = "paused"
    db.commit()

    with pytest.raises(ValueError, match="paused"):
        tick_runner.run_next_tick(db, multiverse=root)

    run_orchestrator = _load_run_orchestrator_with_report_stub()
    with pytest.raises(ValueError, match="paused"):
        run_orchestrator.run_big_bang_until_complete(db, big_bang=big_bang)

    assert db.scalars(select(models.TickSnapshot).where(models.TickSnapshot.multiverse_id == root.id)).all() == []


def test_run_until_complete_does_not_finalize_with_active_unfinished_timelines(db):
    big_bang, root = _seed_world(db)
    unfinished = models.TickSnapshot(
        big_bang_id=big_bang.id,
        multiverse_id=root.id,
        tick_index=0,
        ui_label="M1-T0",
        status="provisional",
        provisional_bundle={},
        final_bundle={},
        summary="unfinished",
        idempotency_key="tick-0",
    )
    db.add(unfinished)
    db.commit()

    run_orchestrator = _load_run_orchestrator_with_report_stub()
    run_orchestrator.generate_final_big_bang_report = lambda *args, **kwargs: pytest.fail("final report should not generate")
    run_orchestrator.generate_multiverse_report = lambda *args, **kwargs: pytest.fail("timeline report should not generate")

    with pytest.raises(ValueError, match="active or unfinished timelines"):
        run_orchestrator.run_big_bang_until_complete(db, big_bang=big_bang, max_total_ticks=1)

    assert big_bang.status != "completed"


def test_failed_tick_execution_rolls_back_partial_state_before_outer_commit(db, monkeypatch):
    big_bang, root = _seed_world(db)

    def add_partial_social_post(*args, **kwargs):
        db.add(
            models.SocialPost(
                big_bang_id=big_bang.id,
                multiverse_id=root.id,
                tick_index=0,
                actor_id=None,
                channel="test",
                body="partial state",
                meta={},
            )
        )
        db.flush()
        return [{"body": "partial state"}]

    _patch_successful_tick(monkeypatch)
    monkeypatch.setattr(tick_runner, "apply_social_actions", add_partial_social_post)
    monkeypatch.setattr(tick_runner, "review_provisional_tick", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("llm closed")))

    with pytest.raises(RuntimeError):
        tick_runner.run_next_tick(db, multiverse=root)
    db.commit()

    assert db.scalars(select(models.TickSnapshot)).all() == []
    assert db.scalars(select(models.SocialPost)).all() == []


def test_max_tick_completion_marks_done_without_returning_duplicate_work(db):
    big_bang, root = _seed_world(db, max_ticks=0)
    tick = models.TickSnapshot(
        big_bang_id=big_bang.id,
        multiverse_id=root.id,
        tick_index=0,
        ui_label="M1-T0",
        status="final",
        provisional_bundle={},
        final_bundle={},
        summary="done",
        idempotency_key="tick-0",
    )
    db.add(tick)
    db.commit()

    run_orchestrator = _load_run_orchestrator_with_report_stub()
    assert run_orchestrator.simulate_ticks(db, multiverse=root, count=2) == []
    db.commit()

    assert root.status == "completed"
    assert len(db.scalars(select(models.TickSnapshot).where(models.TickSnapshot.multiverse_id == root.id)).all()) == 1


def test_forced_tick_uses_unique_idempotency_key(db, monkeypatch):
    big_bang, root = _seed_world(db)
    db.add(
        models.TickSnapshot(
            big_bang_id=big_bang.id,
            multiverse_id=root.id,
            tick_index=0,
            ui_label="M1-T0",
            status="final",
            provisional_bundle={},
            final_bundle={},
            summary="first",
            idempotency_key="same-key",
        )
    )
    db.commit()
    _patch_successful_tick(monkeypatch)

    tick = tick_runner.run_next_tick(db, multiverse=root, idempotency_key="same-key", force=True)
    db.commit()

    keys = [item.idempotency_key for item in db.scalars(select(models.TickSnapshot)).all()]
    assert tick.tick_index == 1
    assert len(keys) == len(set(keys))
    assert tick.idempotency_key != "same-key"


def test_branch_inherits_state_at_fork_tick_and_rejects_future(db):
    big_bang, root = _seed_world(db)
    artifact = models.Artifact(
        big_bang_id=big_bang.id,
        kind="tick_snapshot",
        path="parent.json",
        content_type="application/json",
        content_hash="test",
        size_bytes=2,
        debug_only=False,
        meta={},
    )
    db.add(artifact)
    db.flush()
    for index, label in [(0, "fork"), (1, "future")]:
        db.add(
            models.TickSnapshot(
                big_bang_id=big_bang.id,
                multiverse_id=root.id,
                tick_index=index,
                ui_label=f"M1-T{index}",
                status="final",
                provisional_bundle={},
                final_bundle={
                    "sociology_result": {
                        "graph_summary": {"label": label},
                        "cohort_state_updates": [{"label": label}],
                        "hero_state_updates": [],
                    },
                    "executed_events": [{"label": label}],
                    "idle_assessment": {"idle_streak": index},
                },
                summary=label,
                artifact_id=artifact.id,
                idempotency_key=f"tick-{index}",
            )
        )
    root.state = {"last_tick_index": 1, "graph_summary": {"label": "future"}}
    db.commit()

    child = branch_engine.create_branch(
        db,
        parent=root,
        fork_tick_index=0,
        reason="historical branch",
        idempotency_key="branch-0",
    )

    assert child.state["last_tick_index"] == 0
    assert child.state["graph_summary"] == {"label": "fork"}
    inherited = db.scalars(select(models.TickSnapshot).where(models.TickSnapshot.multiverse_id == child.id)).all()
    assert len(inherited) == 1
    assert inherited[0].artifact_id is None
    with pytest.raises(ValueError):
        branch_engine.create_branch(
            db,
            parent=root,
            fork_tick_index=3,
            reason="future branch",
            idempotency_key="branch-3",
        )


def test_god_tools_reject_out_of_scope_mutations(db):
    big_bang, root = _seed_world(db)
    other = models.Multiverse(
        big_bang_id=big_bang.id,
        parent_multiverse_id=None,
        fork_tick_index=None,
        ui_label="M2",
        depth=0,
        status="active",
        branch_reason="Other",
        state={},
    )
    db.add(other)
    db.flush()
    event = models.Event(
        big_bang_id=big_bang.id,
        multiverse_id=other.id,
        event_type="test",
        created_tick=0,
        scheduled_tick=1,
        status="queued",
        title="Out of scope",
        description=None,
        expected_impact={},
        actual_impact={},
        meta={},
    )
    candidate = models.CohortSplitCandidate(
        big_bang_id=big_bang.id,
        multiverse_id=other.id,
        tick_index=0,
        status="candidate",
        payload={},
    )
    plan = models.CohortMergePlan(
        big_bang_id=big_bang.id,
        multiverse_id=other.id,
        tick_index=0,
        status="planned",
        payload={},
    )
    db.add_all([event, candidate, plan])
    db.flush()

    calls = [
        god_tools.execute_tool_call(
            db,
            big_bang_id=big_bang.id,
            multiverse=root,
            tick_snapshot_id=None,
            god_review_id=None,
            tool_name="register_key_event",
            arguments={"event_id": str(event.id)},
            idempotency_key="event-scope",
        ),
        god_tools.execute_tool_call(
            db,
            big_bang_id=big_bang.id,
            multiverse=root,
            tick_snapshot_id=None,
            god_review_id=None,
            tool_name="approve_split",
            arguments={"candidate_id": str(candidate.id)},
            idempotency_key="candidate-scope",
        ),
        god_tools.execute_tool_call(
            db,
            big_bang_id=big_bang.id,
            multiverse=root,
            tick_snapshot_id=None,
            god_review_id=None,
            tool_name="approve_merge_plan",
            arguments={"merge_plan_id": str(plan.id)},
            idempotency_key="plan-scope",
        ),
    ]

    assert [call.status for call in calls] == ["failed", "failed", "failed"]
    assert event.meta == {}
    assert candidate.status == "candidate"
    assert plan.status == "planned"
    assert db.scalars(select(models.CohortSplit)).all() == []
    assert db.scalars(select(models.CohortMerge)).all() == []
