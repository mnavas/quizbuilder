"""add draw_count to tests; drop unused pools tables

Revision ID: 002
Revises: 001
Create Date: 2026-04-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add draw_count to tests: if set, session start draws this many questions randomly
    op.add_column("tests", sa.Column("draw_count", sa.Integer(), nullable=True))

    # Drop FK columns on test_blocks that reference pools, then drop pool tables
    op.drop_constraint("test_blocks_pool_id_fkey", "test_blocks", type_="foreignkey")
    op.drop_column("test_blocks", "pool_id")
    op.drop_column("test_blocks", "pool_draw_count")
    op.drop_table("pool_questions")
    op.drop_table("pools")


def downgrade() -> None:
    op.drop_column("tests", "draw_count")

    op.create_table(
        "pools",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("tenant_id", sa.Text(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "pool_questions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("pool_id", sa.Text(), nullable=False),
        sa.Column("question_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["pool_id"], ["pools.id"]),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pool_id", "question_id"),
    )
