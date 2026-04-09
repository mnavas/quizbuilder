"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("settings_json", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="candidate"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("force_password_reset", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "questions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("prompt_json", JSONB, nullable=False),
        sa.Column("options_json", JSONB, nullable=True),
        sa.Column("correct_answer", JSONB, nullable=True),
        sa.Column("explanation_json", JSONB, nullable=True),
        sa.Column("points", sa.Integer, nullable=False, server_default="1"),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "pools",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "pool_questions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("pool_id", UUID(as_uuid=False), sa.ForeignKey("pools.id"), nullable=False),
        sa.Column("question_id", UUID(as_uuid=False), sa.ForeignKey("questions.id"), nullable=False),
        sa.UniqueConstraint("pool_id", "question_id"),
    )

    op.create_table(
        "tests",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("mode", sa.String(20), nullable=False, server_default="async"),
        sa.Column("access", sa.String(20), nullable=False, server_default="open"),
        sa.Column("time_limit_minutes", sa.Integer, nullable=True),
        sa.Column("allow_multiple_attempts", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("max_attempts", sa.Integer, nullable=True),
        sa.Column("randomize_questions", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("randomize_options", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("show_score", sa.String(20), nullable=False, server_default="at_end"),
        sa.Column("show_correct_answers", sa.String(20), nullable=False, server_default="never"),
        sa.Column("passing_score_pct", sa.Integer, nullable=True),
        sa.Column("multiple_select_scoring", sa.String(20), nullable=False, server_default="all_or_nothing"),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allow_late_join", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("link_token", sa.String(100), nullable=True, unique=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "test_blocks",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("test_id", UUID(as_uuid=False), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("instructions_json", JSONB, nullable=True),
        sa.Column("pool_id", UUID(as_uuid=False), sa.ForeignKey("pools.id"), nullable=True),
        sa.Column("pool_draw_count", sa.Integer, nullable=True),
    )

    op.create_table(
        "test_block_questions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("block_id", UUID(as_uuid=False), sa.ForeignKey("test_blocks.id"), nullable=False),
        sa.Column("question_id", UUID(as_uuid=False), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("order", sa.Integer, nullable=False, server_default="0"),
        sa.UniqueConstraint("block_id", "question_id"),
    )

    op.create_table(
        "access_codes",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("test_id", UUID(as_uuid=False), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("max_uses", sa.Integer, nullable=True),
        sa.Column("use_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_by", UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("test_id", UUID(as_uuid=False), sa.ForeignKey("tests.id"), nullable=False),
        sa.Column("taker_id", UUID(as_uuid=False), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("taker_email", sa.String(255), nullable=True),
        sa.Column("access_code_id", UUID(as_uuid=False), sa.ForeignKey("access_codes.id"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score_pct", sa.Integer, nullable=True),
        sa.Column("passed", sa.Boolean, nullable=True),
        sa.Column("review_status", sa.String(20), nullable=False, server_default="auto_scored"),
    )

    op.create_table(
        "session_questions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=False), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("question_id", UUID(as_uuid=False), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("options_order_json", JSONB, nullable=True),
    )

    op.create_table(
        "answers",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=False), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("question_id", UUID(as_uuid=False), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("value_json", JSONB, nullable=True),
        sa.Column("auto_score", sa.Integer, nullable=True),
        sa.Column("manual_score", sa.Integer, nullable=True),
        sa.Column("reviewer_comment", sa.Text, nullable=True),
        sa.Column("needs_review", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("saved_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "media_files",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=False), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("question_id", UUID(as_uuid=False), sa.ForeignKey("questions.id"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("media_files")
    op.drop_table("answers")
    op.drop_table("session_questions")
    op.drop_table("sessions")
    op.drop_table("access_codes")
    op.drop_table("test_block_questions")
    op.drop_table("test_blocks")
    op.drop_table("tests")
    op.drop_table("pool_questions")
    op.drop_table("pools")
    op.drop_table("questions")
    op.drop_table("users")
    op.drop_table("tenants")
