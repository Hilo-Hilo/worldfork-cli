"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-04-25
"""
from alembic import op
from sqlalchemy import inspect

from app.db.models import Base

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    if _is_offline_bind(bind):
        _drop_tables_offline(bind)
        return
    if bind.dialect.name == "sqlite":
        op.execute("PRAGMA foreign_keys=OFF")
    else:
        for table_name, constrained_columns, referred_table in [
            ("big_bangs", ["source_snapshot_id"], "source_of_truth_snapshots"),
            ("source_of_truth_snapshots", ["big_bang_id"], "big_bangs"),
            ("events", ["current_revision_id"], "event_revisions"),
            ("event_revisions", ["event_id"], "events"),
            ("event_summaries", ["supersedes_event_summary_id"], "event_summaries"),
            ("multiverses", ["parent_multiverse_id"], "multiverses"),
            ("report_versions", ["supersedes_report_version_id"], "report_versions"),
        ]:
            _drop_fk_if_present(bind, table_name, constrained_columns, referred_table)
    Base.metadata.drop_all(bind=bind)


def _is_offline_bind(bind) -> bool:
    return bind.__class__.__name__ == "MockConnection"


def _drop_tables_offline(bind) -> None:
    if not hasattr(Base.metadata, "tables"):
        Base.metadata.drop_all(bind=bind, checkfirst=False)
        return
    cascade = " CASCADE" if bind.dialect.name == "postgresql" else ""
    for table_name in reversed(Base.metadata.tables):
        op.execute(f'DROP TABLE IF EXISTS "{table_name}"{cascade}')


def _drop_fk_if_present(
    bind, table_name: str, constrained_columns: list[str], referred_table: str
) -> None:
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return
    for fk in inspector.get_foreign_keys(table_name):
        if fk.get("referred_table") != referred_table:
            continue
        if fk.get("constrained_columns") != constrained_columns:
            continue
        if fk.get("name"):
            op.drop_constraint(fk["name"], table_name, type_="foreignkey")
        return
