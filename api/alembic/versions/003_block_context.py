"""add context_json to test_blocks

Revision ID: 003
Revises: 002
Create Date: 2026-04-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("test_blocks", sa.Column("context_json", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("test_blocks", "context_json")
