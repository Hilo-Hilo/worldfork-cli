from __future__ import annotations

from io import BytesIO

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.orm import Session

from app.db import models
from app.storage.artifact_store import ArtifactStore


def render_markdown_pdf(
    db: Session,
    *,
    big_bang_id,
    relative_path: str,
    title: str,
    markdown: str,
) -> models.Artifact:
    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 72
    page.setFont("Helvetica-Bold", 14)
    page.drawString(72, y, title[:90])
    y -= 28
    page.setFont("Helvetica", 10)
    for line in markdown.splitlines():
        if y < 72:
            page.showPage()
            page.setFont("Helvetica", 10)
            y = height - 72
        page.drawString(72, y, line[:110])
        y -= 14
    page.save()
    encoded = buffer.getvalue()
    store = ArtifactStore()
    store.ensure_root()
    path = store.root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded)
    artifact = models.Artifact(
        big_bang_id=big_bang_id,
        kind="report_pdf",
        path=str(path),
        content_type="application/pdf",
        content_hash=None,
        size_bytes=len(encoded),
        debug_only=False,
        meta={"relative_path": relative_path},
    )
    db.add(artifact)
    db.flush()
    return artifact
