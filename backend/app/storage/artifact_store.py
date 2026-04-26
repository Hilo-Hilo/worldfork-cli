from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db import models


class ArtifactStore:
    def __init__(self, root: Path | None = None):
        settings = get_settings()
        self.root = (root or settings.artifact_root).resolve()

    def ensure_root(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def big_bang_root(self, big_bang_id: UUID | str) -> Path:
        return self.root / f"big_bang_{big_bang_id}"

    def write_json(
        self,
        db: Session,
        *,
        big_bang_id: UUID | None,
        relative_path: str,
        payload: Any,
        kind: str,
        debug_only: bool = False,
    ) -> models.Artifact:
        body = json.dumps(payload, indent=2, sort_keys=True, default=str)
        return self.write_text(
            db,
            big_bang_id=big_bang_id,
            relative_path=relative_path,
            body=body,
            kind=kind,
            content_type="application/json",
            debug_only=debug_only,
        )

    def write_text(
        self,
        db: Session,
        *,
        big_bang_id: UUID | None,
        relative_path: str,
        body: str,
        kind: str,
        content_type: str = "text/plain",
        debug_only: bool = False,
    ) -> models.Artifact:
        self.ensure_root()
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        encoded = body.encode("utf-8")
        path.write_bytes(encoded)
        artifact = models.Artifact(
            big_bang_id=big_bang_id,
            kind=kind,
            path=str(path),
            content_type=content_type,
            content_hash=hashlib.sha256(encoded).hexdigest(),
            size_bytes=len(encoded),
            debug_only=debug_only,
            meta={"relative_path": relative_path},
        )
        db.add(artifact)
        db.flush()
        return artifact

    def copy_tree_snapshot(
        self,
        db: Session,
        *,
        big_bang_id: UUID,
        source_dir: Path,
        relative_dest: str,
        kind: str,
    ) -> tuple[models.Artifact, str]:
        self.ensure_root()
        dest = self.root / relative_dest
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source_dir, dest)
        content_hash = hash_directory(dest)
        artifact = models.Artifact(
            big_bang_id=big_bang_id,
            kind=kind,
            path=str(dest),
            content_type="inode/directory",
            content_hash=content_hash,
            size_bytes=None,
            debug_only=False,
            meta={"relative_path": relative_dest},
        )
        db.add(artifact)
        db.flush()
        return artifact, content_hash


def hash_directory(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(str(file_path.relative_to(path)).encode("utf-8"))
        digest.update(file_path.read_bytes())
    return digest.hexdigest()
