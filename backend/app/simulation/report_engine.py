from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.storage.artifact_store import ArtifactStore
from app.storage.pdf_store import render_markdown_pdf


def generate_multiverse_report(db: Session, *, multiverse: models.Multiverse, title: str | None = None, summary: str | None = None) -> models.ReportVersion:
    report = db.scalar(select(models.Report).where(models.Report.multiverse_id == multiverse.id, models.Report.report_type == "multiverse"))
    if not report:
        report = models.Report(big_bang_id=multiverse.big_bang_id, multiverse_id=multiverse.id, report_type="multiverse", status="draft", current_version=0)
        db.add(report)
        db.flush()
    version = report.current_version + 1
    ticks = db.scalars(
        select(models.TickSnapshot)
        .where(models.TickSnapshot.multiverse_id == multiverse.id)
        .order_by(models.TickSnapshot.tick_index)
    ).all()
    god_reviews = db.scalars(
        select(models.GodAgentReview)
        .where(models.GodAgentReview.multiverse_id == multiverse.id)
        .order_by(models.GodAgentReview.created_at)
    ).all()
    title_text = title or f"Multiverse {multiverse.ui_label} Report"
    body = "\n".join(
        [
            f"# {title_text}",
            "",
            summary or f"Report for {multiverse.ui_label} with {len(ticks)} tick snapshots.",
            "",
            "## Timeline",
            *[f"- {tick.ui_label}: {tick.summary or tick.status}" for tick in ticks],
            "",
            "## God Agent Decisions",
            *[f"- {review.decision}: {review.rationale}" for review in god_reviews],
            "",
            "## Evidence Appendix",
            f"- Multiverse ID: {multiverse.id}",
            f"- Status: {multiverse.status}",
        ]
    )
    artifact = ArtifactStore().write_text(
        db,
        big_bang_id=multiverse.big_bang_id,
        relative_path=f"big_bang_{multiverse.big_bang_id}/multiverses/{multiverse.ui_label}/reports/report_v{version}.md",
        body=body,
        kind="report_markdown",
        content_type="text/markdown",
    )
    pdf_artifact = render_markdown_pdf(
        db,
        big_bang_id=multiverse.big_bang_id,
        relative_path=f"big_bang_{multiverse.big_bang_id}/multiverses/{multiverse.ui_label}/reports/report_v{version}.pdf",
        title=title_text,
        markdown=body,
    )
    report.current_version = version
    report.status = "completed"
    multiverse.report_status = "completed"
    report_version = models.ReportVersion(
        report_id=report.id,
        version=version,
        title=title_text,
        summary=summary,
        markdown_artifact_id=artifact.id,
        pdf_artifact_id=pdf_artifact.id,
    )
    db.add(report_version)
    db.flush()
    return report_version


def generate_final_big_bang_report(db: Session, *, big_bang: models.BigBang, title: str | None = None, summary: str | None = None) -> models.ReportVersion:
    report = db.scalar(select(models.Report).where(models.Report.big_bang_id == big_bang.id, models.Report.report_type == "final_big_bang", models.Report.multiverse_id.is_(None)))
    if not report:
        report = models.Report(big_bang_id=big_bang.id, report_type="final_big_bang", status="draft", current_version=0)
        db.add(report)
        db.flush()
    version = report.current_version + 1
    multiverses = db.scalars(
        select(models.Multiverse)
        .where(models.Multiverse.big_bang_id == big_bang.id)
        .order_by(models.Multiverse.ui_label)
    ).all()
    reports = db.scalars(select(models.Report).where(models.Report.big_bang_id == big_bang.id)).all()
    title_text = title or f"{big_bang.name} Final Big Bang Report"
    body = "\n".join(
        [
            f"# {title_text}",
            "",
            summary or f"Final condensation across {len(multiverses)} multiverse timelines.",
            "",
            "## Multiverse Comparison",
            *[f"- {item.ui_label}: {item.status}, report={item.report_status}" for item in multiverses],
            "",
            "## Report Inventory",
            *[f"- {item.report_type}: {item.status} v{item.current_version}" for item in reports],
            "",
            "## Evidence Appendix",
            f"- Big Bang ID: {big_bang.id}",
        ]
    )
    artifact = ArtifactStore().write_text(
        db,
        big_bang_id=big_bang.id,
        relative_path=f"big_bang_{big_bang.id}/reports/final_big_bang_report_v{version}.md",
        body=body,
        kind="report_markdown",
        content_type="text/markdown",
    )
    pdf_artifact = render_markdown_pdf(
        db,
        big_bang_id=big_bang.id,
        relative_path=f"big_bang_{big_bang.id}/reports/final_big_bang_report_v{version}.pdf",
        title=title_text,
        markdown=body,
    )
    report.current_version = version
    report.status = "completed"
    report_version = models.ReportVersion(
        report_id=report.id,
        version=version,
        title=title_text,
        summary=summary,
        markdown_artifact_id=artifact.id,
        pdf_artifact_id=pdf_artifact.id,
    )
    db.add(report_version)
    db.flush()
    return report_version
