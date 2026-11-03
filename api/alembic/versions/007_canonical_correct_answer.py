"""canonicalise question.correct_answer to the plain form

Rewrites legacy wrapped envelopes to the canonical stored shape:
  multiple_choice / true_false : {"value": "b"}   -> "b"
  multiple_select              : {"values": [...]} -> [...]

short_text ({"text": ...}) and already-plain values are left untouched.
See app/normalize.py for the canonical form going forward.

Revision ID: 007
Revises: 006
Create Date: 2026-11-03
"""
from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # MC / TF: unwrap {"value": X} -> X
    op.execute(
        """
        UPDATE questions
        SET correct_answer = correct_answer->'value'
        WHERE type IN ('multiple_choice', 'true_false')
          AND jsonb_typeof(correct_answer) = 'object'
          AND correct_answer ? 'value'
        """
    )
    # MS: unwrap {"values": [...]} -> [...]
    op.execute(
        """
        UPDATE questions
        SET correct_answer = correct_answer->'values'
        WHERE type = 'multiple_select'
          AND jsonb_typeof(correct_answer) = 'object'
          AND correct_answer ? 'values'
        """
    )


def downgrade() -> None:
    # Re-wrap plain values back into the legacy envelope.
    op.execute(
        """
        UPDATE questions
        SET correct_answer = jsonb_build_object('value', correct_answer)
        WHERE type IN ('multiple_choice', 'true_false')
          AND jsonb_typeof(correct_answer) = 'string'
        """
    )
    op.execute(
        """
        UPDATE questions
        SET correct_answer = jsonb_build_object('values', correct_answer)
        WHERE type = 'multiple_select'
          AND jsonb_typeof(correct_answer) = 'array'
        """
    )
