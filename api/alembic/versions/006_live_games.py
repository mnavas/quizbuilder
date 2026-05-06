"""add live_games, live_players, live_answers tables

Revision ID: 006
Revises: 005
Create Date: 2026-05-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "live_games",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("test_id", UUID(as_uuid=False), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("pin", sa.String(6), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default=sa.text("'waiting'")),
        sa.Column("current_question_index", sa.Integer(), nullable=False, server_default="-1"),
        sa.Column("current_question_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("time_limit_seconds", sa.Integer(), nullable=False, server_default="20"),
        sa.Column("question_ids_json", JSONB(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_live_games_pin", "live_games", ["pin"])

    op.create_table(
        "live_players",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("game_id", UUID(as_uuid=False), sa.ForeignKey("live_games.id"), nullable=False),
        sa.Column("nickname", sa.String(100), nullable=False),
        sa.Column("avatar_color", sa.String(7), nullable=False, server_default=sa.text("'#f59e0b'")),
        sa.Column("total_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "live_answers",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("game_id", UUID(as_uuid=False), sa.ForeignKey("live_games.id"), nullable=False),
        sa.Column("player_id", UUID(as_uuid=False), sa.ForeignKey("live_players.id"), nullable=False),
        sa.Column("question_id", UUID(as_uuid=False), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("value_json", JSONB(), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("time_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("points_earned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_correct", sa.Boolean(), nullable=False, server_default="false"),
        sa.UniqueConstraint("game_id", "player_id", "question_id", name="uq_live_answers_player_question"),
    )


def downgrade() -> None:
    op.drop_table("live_answers")
    op.drop_table("live_players")
    op.drop_index("ix_live_games_pin", "live_games")
    op.drop_table("live_games")
