"""add available_from and available_until to tests

Revision ID: 004
Revises: 003
Create Date: 2026-04-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tests", sa.Column("available_from", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tests", sa.Column("available_until", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tests", "available_until")
    op.drop_column("tests", "available_from")
