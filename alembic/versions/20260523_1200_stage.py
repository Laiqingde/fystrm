"""v0.3 scan task stage

Revision ID: c7e5a8b2d1f4
Revises: b1e9f2a3c4d5
Create Date: 2026-05-23 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c7e5a8b2d1f4"
down_revision: Union[str, Sequence[str], None] = "b1e9f2a3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scan_tasks", sa.Column("stage", sa.String(length=32), nullable=False, server_default="pending"))
    op.add_column("scan_tasks", sa.Column("stage_message", sa.String(length=256), nullable=True))


def downgrade() -> None:
    op.drop_column("scan_tasks", "stage_message")
    op.drop_column("scan_tasks", "stage")
