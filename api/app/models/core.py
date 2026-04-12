"""
SQLAlchemy ORM models for Quizbee.

Domain overview
---------------
Tenant  ─── User                       (multi-tenant; every row is scoped to a tenant)
Test    ─── TestBlock ─── TestBlockQuestion ─── Question
Test    ─── Session   ─── SessionQuestion
                      └── Answer

A Test is a collection of ordered Blocks. Each Block holds an ordered set of
Questions and optional shared context (audio/image/text) displayed above them.

When a taker starts a test, a Session is created. The exact set and order of
questions drawn for that session is recorded as SessionQuestion rows (important
for draw_count / random-draw mode where different takers get different subsets).
Each answer the taker saves is stored as an Answer row.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Tenant(Base):
    """
    Top-level isolation unit. Every resource (users, tests, questions, media) belongs
    to exactly one tenant. The slug is used for subdomain or path-based routing.
    """
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    settings_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship("User", back_populates="tenant")


class User(Base):
    """
    Admin/staff user who manages tests and reviews sessions.
    Takers are NOT users — they are identified only by an optional email on the Session.

    Roles (least to most privileged): candidate < reviewer < manager < admin.
    force_password_reset is set on admin-created accounts; the user must change
    their password on first login before accessing anything else.
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    # Roles: admin, manager, reviewer, candidate
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="candidate")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    force_password_reset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")


class Question(Base):
    """
    Reusable question that can appear in multiple tests.

    Content is stored as Tiptap JSON (prompt_json, explanation_json) so the
    frontend rich-text editor can render and edit it without conversion.

    options_json encoding varies by type:
    - choice types (multiple_choice, multiple_select, true_false):
        list of {id, content_json} objects
    - audio_prompt / video_prompt:
        {media_file_id, mime_type} dict (a "media_ref", not a list)
    - all other types: null

    correct_answer encoding varies by type:
    - multiple_choice / true_false: {"value": "option_id"}
    - multiple_select: {"values": ["a", "b"]}
    - short_text (e.g. spelling): {"text": "expected word"}
    - open types (long_text, file_upload): null → manual review required

    Soft-deleted via deleted_at; never hard-deleted so historical session data
    (answers referencing this question) remains intact.
    """
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False)
    # Types: multiple_choice, multiple_select, true_false, ordering, matching,
    #        fill_in_the_blank, numeric, short_text, long_text, file_upload,
    #        passage, audio_prompt, video_prompt, divider
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Tiptap JSON for rich content (plain text wrapped in paragraph node for Phase 1)
    prompt_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # List of option objects {id, content_json}; null for non-choice types
    options_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Type-dependent: str | list[str] | dict | null (open questions)
    correct_answer: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Shown in practice mode after answering
    explanation_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )



class Test(Base):
    """
    A published assessment. Contains ordered Blocks, each holding ordered Questions.

    Access control:
    - open:       anyone with the link_token can take it
    - registered: requires a logged-in user account
    - code:       taker must supply a valid AccessCode

    Delivery modes:
    - async: self-paced; taker starts whenever they want
    - sync:  scheduled; controlled start via scheduled_start

    draw_count: if set, each session randomly draws this many BLOCKS from the
    test's pool (seeded by session_id for reproducibility). Questions within each
    drawn block are always included together to preserve context coherence.

    show_correct_answers values:
    - never:        answers are never revealed
    - at_end:       revealed on the result screen after submit
    - per_question: immediate feedback after each answer (uses /check endpoint)
    - after_review: revealed only after a reviewer grades open answers (Phase 5.1)

    A test is not accessible to takers until published_at is set and link_token
    is generated (via the /publish endpoint). Soft-deleted via deleted_at.
    """
    __tablename__ = "tests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # mode: async | sync
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="async")
    # access: open | registered | code
    access: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    time_limit_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allow_multiple_attempts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    randomize_questions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    randomize_options: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # show_score: at_end | never
    show_score: Mapped[str] = mapped_column(String(20), nullable=False, default="at_end")
    # show_correct_answers: at_end | never | per_question | after_review
    show_correct_answers: Mapped[str] = mapped_column(String(20), nullable=False, default="never")
    passing_score_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # multiple_select_scoring: all_or_nothing | partial
    multiple_select_scoring: Mapped[str] = mapped_column(String(20), nullable=False, default="all_or_nothing")
    # sync mode fields
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    allow_late_join: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # time window: takers can only start within this range (null = no restriction)
    available_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    available_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Phase 2.5: if set, session start draws this many questions randomly from the test's pool
    draw_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # shareable link token (set on publish)
    link_token: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    blocks: Mapped[list["TestBlock"]] = relationship(
        "TestBlock", back_populates="test", order_by="TestBlock.order"
    )
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="test")
    access_codes: Mapped[list["AccessCode"]] = relationship("AccessCode", back_populates="test")


class TestBlock(Base):
    """
    An ordered group of questions within a test. Blocks let admins organise
    questions thematically and attach shared context (a reading passage, an
    audio clip, an image) that is displayed above all questions in the block.

    context_json is a Tiptap JSON document. The taker renderer handles two shapes:
    - Pure audio/video node → rendered as a native <audio>/<video> player.
    - Any other content    → rendered as rich text (passage, image, etc.).
    When context_json is null and the block has a title, the taker UI falls back
    to browser TTS (useful for spelling-bee-style tests without uploaded audio).

    instructions_json: currently unused in the taker UI; reserved for future
    per-block written instructions separate from context.
    """
    __tablename__ = "test_blocks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    test_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tests.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    instructions_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    context_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    test: Mapped["Test"] = relationship("Test", back_populates="blocks")
    block_questions: Mapped[list["TestBlockQuestion"]] = relationship(
        "TestBlockQuestion", back_populates="block", order_by="TestBlockQuestion.order"
    )


class TestBlockQuestion(Base):
    __tablename__ = "test_block_questions"
    __table_args__ = (UniqueConstraint("block_id", "question_id"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    block_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_blocks.id"), nullable=False)
    question_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("questions.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    block: Mapped["TestBlock"] = relationship("TestBlock", back_populates="block_questions")
    question: Mapped["Question"] = relationship("Question")


class AccessCode(Base):
    __tablename__ = "access_codes"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    test_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tests.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    test: Mapped["Test"] = relationship("Test", back_populates="access_codes")


class Session(Base):
    """
    One attempt by a taker at a test.

    Taker identity is deliberately loose: taker_id is set only for registered
    users; anonymous takers are identified by taker_email alone (or not at all).

    Lifecycle: active → submitted (or expired if time_limit_minutes elapses).

    score_pct and passed are computed at submit time by the scoring engine.
    They remain null until submission, and stay null if any answer needs_review
    (manual scoring pending).

    review_status:
    - auto_scored:     all answers machine-graded; score_pct is final
    - awaiting_review: at least one open answer awaits reviewer grading
    - reviewed:        reviewer has graded all open answers; score_pct is final
    """
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    test_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tests.id"), nullable=False)
    # Nullable — anonymous takers have no user record
    taker_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    taker_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    access_code_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("access_codes.id"), nullable=True
    )
    # status: active | submitted | expired
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    score_pct: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # review_status: auto_scored | awaiting_review | reviewed
    review_status: Mapped[str] = mapped_column(String(20), nullable=False, default="auto_scored")

    test: Mapped["Test"] = relationship("Test", back_populates="sessions")
    session_questions: Mapped[list["SessionQuestion"]] = relationship(
        "SessionQuestion", back_populates="session", order_by="SessionQuestion.order"
    )
    answers: Mapped[list["Answer"]] = relationship("Answer", back_populates="session")


class SessionQuestion(Base):
    """Records the exact question draw and option order for a session."""
    __tablename__ = "session_questions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("sessions.id"), nullable=False)
    question_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("questions.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Shuffled option order stored as list of option IDs; null if not randomized
    options_order_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    session: Mapped["Session"] = relationship("Session", back_populates="session_questions")


class Answer(Base):
    """
    One taker response to one question within a session.

    value_json encoding mirrors correct_answer on Question:
    - choice types:  {"selected": "option_id"} or {"selected": ["a", "b"]}
    - short_text:    {"text": "typed answer"}
    - long_text:     {"text": "essay text"}

    Scoring fields:
    - auto_score:   set by the scoring engine at submit time; null for open types
    - manual_score: set by a reviewer; null until reviewed
    - needs_review: true when the question type has no auto-scoring (long_text,
                    file_upload, short_text without a correct_answer set)

    The effective score is auto_score ?? manual_score (manual overrides auto for
    open questions once a reviewer grades them).
    """
    __tablename__ = "answers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("sessions.id"), nullable=False)
    question_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("questions.id"), nullable=False)
    # Taker's answer — type matches question.correct_answer encoding
    value_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # auto_score: set by scoring engine; null for open questions
    auto_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # manual_score: set by reviewer; null until reviewed
    manual_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewer_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session: Mapped["Session"] = relationship("Session", back_populates="answers")


class MediaFile(Base):
    """
    Uploaded binary asset (image, audio, video) stored on the local filesystem.

    storage_path is relative to settings.media_root and follows the pattern
    {tenant_id}/{media_file_id}/{filename}. The file is served by the /media
    static route or a reverse proxy (nginx) in production.

    Media is referenced from Question and TestBlock content by embedding the
    media_file_id UUID inside Tiptap JSON node attributes. The export/import
    pipeline (tests.py) uses these IDs to bundle assets into ZIP files and
    remap them on import to a different instance.
    """
    __tablename__ = "media_files"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tenants.id"), nullable=False)
    question_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False), ForeignKey("questions.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
