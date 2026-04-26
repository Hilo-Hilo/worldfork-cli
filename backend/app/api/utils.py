from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import models


def require(db: Session, model, object_id):
    obj = db.get(model, object_id)
    if not obj:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return obj


def commit_or_500(db: Session):
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def row_dict(row):
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}
