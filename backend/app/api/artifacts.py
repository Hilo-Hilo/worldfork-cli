from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.utils import require
from app.db import models
from app.db.session import get_db

router = APIRouter(prefix="/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}")
def get_artifact(artifact_id: UUID, debug: bool = False, db: Session = Depends(get_db)):
    artifact = require(db, models.Artifact, artifact_id)
    if artifact.debug_only and not debug:
        raise HTTPException(status_code=403, detail="debug artifact requires debug=true")
    path = Path(artifact.path)
    if not path.exists() or not path.is_file():
        return artifact
    return FileResponse(path, media_type=artifact.content_type, filename=path.name)
