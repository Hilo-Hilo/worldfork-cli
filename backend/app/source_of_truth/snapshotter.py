from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import models
from app.source_of_truth.validator import validate_source_of_truth_dir
from app.storage.artifact_store import ArtifactStore


def snapshot_source_of_truth(db: Session, big_bang_id) -> models.SourceOfTruthSnapshot:
    settings = get_settings()
    source_dir = settings.source_of_truth_dir.resolve()
    validate_source_of_truth_dir(source_dir)
    relative_dest = f"big_bang_{big_bang_id}/configs/source_of_truth"
    artifact, content_hash = ArtifactStore().copy_tree_snapshot(
        db,
        big_bang_id=big_bang_id,
        source_dir=source_dir,
        relative_dest=relative_dest,
        kind="source_of_truth_snapshot",
    )
    snapshot = models.SourceOfTruthSnapshot(
        big_bang_id=big_bang_id,
        version="v1",
        content_hash=content_hash,
        artifact_path=artifact.path,
        artifact_id=artifact.id,
    )
    db.add(snapshot)
    db.flush()
    return snapshot
