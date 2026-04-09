"""
Session lifecycle endpoints — the taker-facing API.

Flow
----
1. POST /take/{link_token}          → creates Session + SessionQuestion rows, returns questions
2. PUT  /{session_id}/answers/{qid} → upserts an Answer (auto-save on every change)
3. POST /{session_id}/check/{qid}   → immediate feedback (only when show_correct_answers=per_question)
4. POST /{session_id}/submit        → finalises session, runs scoring, returns ResultOut
5. GET  /{session_id}/result        → re-fetch result after submission

No authentication is required for taker endpoints — sessions are identified by
their UUID. Admins access session results through the /results router.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.db import get_db
from app.models.core import (
    Answer, Question, Session, SessionQuestion, Test, TestBlock, User,
)
from app.scoring import score_answer

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    taker_email: str | None = None


class SaveAnswerRequest(BaseModel):
    value: dict


class QuestionOut(BaseModel):
    """Question payload sent to the taker. correct_answer is intentionally omitted."""
    id: str
    type: str
    prompt_json: dict
    options_json: list | dict | None   # list for choice types; dict for audio/video media_ref
    points: int
    order: int
    block_title: str | None = None
    context_json: dict | None = None   # shared block context rendered above this question


class SessionOut(BaseModel):
    """Returned by POST /take/{link_token}. Contains all questions for the session."""
    id: str
    test_id: str
    status: str
    expires_at: str | None
    show_correct_answers: str
    questions: list[QuestionOut]


class AnswerOut(BaseModel):
    """
    Per-answer detail in the result screen.
    correct_answer and options_json are only populated when the test's
    show_correct_answers policy allows disclosure.
    is_correct is None when needs_review=True or when correct answers are hidden.
    """
    question_id: str
    type: str
    prompt_json: dict | None
    options_json: list | dict | None
    correct_answer: Any | None
    value: dict | None
    auto_score: int | None
    needs_review: bool
    is_correct: bool | None


class ResultOut(BaseModel):
    """Full result returned after submission and on GET /{session_id}/result."""
    session_id: str
    status: str
    score_pct: int | None
    passed: bool | None
    show_score: bool
    show_correct_answers: str      # "never" | "per_question" | "at_end" | "after_review"
    answers: list[AnswerOut]


class CheckAnswerOut(BaseModel):
    """
    Immediate feedback for one question (per_question mode).
    is_correct is None when the question requires manual review.
    """
    is_correct: bool | None
    needs_review: bool
    auto_score: int | None
    correct_answer: Any | None
    options_json: list | dict | None


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _load_published_test(link_token: str, db: AsyncSession) -> Test:
    result = await db.execute(
        select(Test)
        .where(Test.link_token == link_token, Test.published_at.is_not(None), Test.deleted_at.is_(None))
        .options(
            selectinload(Test.blocks).selectinload(TestBlock.block_questions)
        )
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found or not published")
    return test


async def _load_session(session_id: str, db: AsyncSession) -> Session:
    result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.session_questions), selectinload(Session.answers))
    )
    s = result.scalar_one_or_none()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


def _resolve_questions(test: Test, randomize: bool, session_id: str | None = None) -> list[str]:
    """Return ordered list of question IDs for this session.

    If test.draw_count is set, draw that many BLOCKS randomly (seeded by session_id).
    All questions within each drawn block are included, preserving relative block order.
    This keeps contextually linked content (e.g. audio + spelling question) together.
    """
    blocks = sorted(test.blocks, key=lambda b: b.order)

    if test.draw_count and test.draw_count < len(blocks):
        rng = random.Random(session_id)
        drawn = rng.sample(blocks, test.draw_count)
        drawn_ids = {b.id for b in drawn}
        blocks = [b for b in blocks if b.id in drawn_ids]

    question_ids: list[str] = []
    for block in blocks:
        ids = [bq.question_id for bq in sorted(block.block_questions, key=lambda x: x.order)]
        question_ids.extend(ids)

    if not test.draw_count and randomize:
        random.shuffle(question_ids)

    return question_ids


async def _run_scoring(session: Session, test: Test, db: AsyncSession):
    """Score all answers and compute session totals."""
    q_ids = [sq.question_id for sq in session.session_questions]
    if not q_ids:
        return

    q_result = await db.execute(select(Question).where(Question.id.in_(q_ids)))
    questions = {q.id: q for q in q_result.scalars().all()}

    total_points = sum(q.points for q in questions.values())
    earned_points = 0
    needs_any_review = False

    answer_map = {a.question_id: a for a in session.answers}

    for q_id, q in questions.items():
        answer = answer_map.get(q_id)
        value = answer.value_json if answer else None
        auto_score, needs_review = score_answer(q, value)

        if answer:
            answer.auto_score = auto_score
            answer.needs_review = needs_review
        else:
            # No answer saved — create a blank one
            blank = Answer(
                session_id=session.id,
                question_id=q_id,
                value_json=None,
                auto_score=0,
                needs_review=needs_review,
            )
            db.add(blank)
            auto_score = 0

        if needs_review:
            needs_any_review = True
        elif auto_score:
            earned_points += auto_score

    if not needs_any_review and total_points > 0:
        session.score_pct = round(earned_points / total_points * 100)
        if test.passing_score_pct is not None:
            session.passed = session.score_pct >= test.passing_score_pct
        session.review_status = "auto_scored"
    else:
        session.review_status = "awaiting_review" if needs_any_review else "auto_scored"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/take/{link_token}", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def start_session(
    link_token: str,
    body: StartSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new test session for a taker.

    Resolves the question set (applying draw_count if set), persists SessionQuestion
    rows to lock in the draw, then returns all questions for the session in order.
    No authentication required — public endpoint gated only by the link_token.
    """
    test = await _load_published_test(link_token, db)

    # Check attempt limits for registered users (simplified: skip for open/anonymous)
    taker_id: str | None = None

    # Build session
    expires_at = None
    if test.time_limit_minutes:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=test.time_limit_minutes)

    session = Session(
        test_id=test.id,
        taker_id=taker_id,
        taker_email=body.taker_email,
        status="active",
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()

    # Re-resolve with session_id seed (for draw_count reproducibility on resume)
    q_ids = _resolve_questions(test, test.randomize_questions, session.id)
    if not q_ids:
        raise HTTPException(status_code=400, detail="This test has no questions")

    sq_list = []
    for i, q_id in enumerate(q_ids):
        sq = SessionQuestion(session_id=session.id, question_id=q_id, order=i)
        db.add(sq)
        sq_list.append(sq)
    await db.flush()

    # Fetch question details for response
    q_result = await db.execute(select(Question).where(Question.id.in_(q_ids)))
    questions = {q.id: q for q in q_result.scalars().all()}

    # Build question → block map for context_json
    q_block_map: dict[str, TestBlock] = {}
    for block in test.blocks:
        for bq in block.block_questions:
            if bq.question_id in set(q_ids):
                q_block_map[bq.question_id] = block

    await db.commit()

    question_out = []
    for sq in sorted(sq_list, key=lambda x: x.order):
        q = questions[sq.question_id]
        block = q_block_map.get(sq.question_id)
        # Hide correct_answer from taker response
        options = q.options_json
        if test.randomize_options and options:
            options = list(options)
            random.shuffle(options)
        question_out.append(QuestionOut(
            id=q.id,
            type=q.type,
            prompt_json=q.prompt_json,
            options_json=options,
            points=q.points,
            order=sq.order,
            block_title=block.title if block else None,
            context_json=block.context_json if block else None,
        ))

    return SessionOut(
        id=session.id,
        test_id=test.id,
        status="active",
        expires_at=expires_at.isoformat() if expires_at else None,
        show_correct_answers=test.show_correct_answers,
        questions=question_out,
    )


@router.put("/{session_id}/answers/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def save_answer(
    session_id: str,
    question_id: str,
    body: SaveAnswerRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Upsert a taker's answer for one question (auto-save on every change).
    Rejects saves to expired or already-submitted sessions.
    """
    session = await _load_session(session_id, db)
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    # Enforce time limit
    if session.expires_at and datetime.now(timezone.utc) > session.expires_at:
        session.status = "expired"
        await db.commit()
        raise HTTPException(status_code=400, detail="Session has expired")

    # Check question belongs to session
    sq_ids = {sq.question_id for sq in session.session_questions}
    if question_id not in sq_ids:
        raise HTTPException(status_code=400, detail="Question not part of this session")

    # Upsert answer
    existing = next((a for a in session.answers if a.question_id == question_id), None)
    if existing:
        existing.value_json = body.value
        existing.saved_at = datetime.now(timezone.utc)
    else:
        db.add(Answer(session_id=session_id, question_id=question_id, value_json=body.value))
    await db.commit()


@router.post("/{session_id}/submit", response_model=ResultOut)
async def submit_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Finalise a session. Runs the scoring engine over all saved answers,
    computes score_pct and passed, and returns the full result.
    Idempotent guard: raises 400 if already submitted.
    """
    session = await _load_session(session_id, db)
    if session.status == "submitted":
        raise HTTPException(status_code=400, detail="Session already submitted")

    test_result = await db.execute(select(Test).where(Test.id == session.test_id))
    test = test_result.scalar_one()

    session.status = "submitted"
    session.submitted_at = datetime.now(timezone.utc)

    await _run_scoring(session, test, db)
    await db.commit()

    # Reload with answers
    session = await _load_session(session_id, db)
    return await _build_result(session, test, db)


@router.post("/{session_id}/check/{question_id}", response_model=CheckAnswerOut)
async def check_answer(
    session_id: str,
    question_id: str,
    body: SaveAnswerRequest,
    db: AsyncSession = Depends(get_db),
):
    """Return immediate scoring feedback for one question (only when show_correct_answers=per_question)."""
    session = await _load_session(session_id, db)
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session is not active")

    test_result = await db.execute(select(Test).where(Test.id == session.test_id))
    test = test_result.scalar_one()

    if test.show_correct_answers != "per_question":
        raise HTTPException(status_code=403, detail="Per-question feedback not enabled for this test")

    sq_ids = {sq.question_id for sq in session.session_questions}
    if question_id not in sq_ids:
        raise HTTPException(status_code=400, detail="Question not part of this session")

    q_result = await db.execute(select(Question).where(Question.id == question_id))
    q = q_result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    auto_score, needs_review = score_answer(q, body.value)
    return CheckAnswerOut(
        is_correct=None if needs_review else (auto_score or 0) > 0,
        needs_review=needs_review,
        auto_score=auto_score,
        correct_answer=q.correct_answer,
        options_json=q.options_json,
    )


@router.get("/{session_id}/result", response_model=ResultOut)
async def get_result(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    session = await _load_session(session_id, db)
    if session.status == "active":
        raise HTTPException(status_code=400, detail="Session not yet submitted")

    test_result = await db.execute(select(Test).where(Test.id == session.test_id))
    test = test_result.scalar_one()
    return await _build_result(session, test, db)


async def _build_result(session: Session, test: Test, db: AsyncSession | None = None) -> ResultOut:
    """
    Assemble a ResultOut from a submitted session, applying the test's disclosure
    policy. score_pct, correct_answer, and options_json are redacted when the
    test's show_score / show_correct_answers settings prohibit them.
    """
    show_score = test.show_score == "at_end"
    show_correct = test.show_correct_answers in ("at_end", "per_question")

    # Load question data for all answered questions
    q_ids = [a.question_id for a in session.answers]
    questions: dict[str, Question] = {}
    if q_ids and db is not None:
        result = await db.execute(select(Question).where(Question.id.in_(q_ids)))
        questions = {q.id: q for q in result.scalars().all()}

    answers_out = []
    for answer in session.answers:
        q = questions.get(answer.question_id)
        is_correct = None
        if show_correct and not answer.needs_review:
            is_correct = (answer.auto_score or 0) > 0
        answers_out.append(AnswerOut(
            question_id=answer.question_id,
            type=q.type if q else "unknown",
            prompt_json=q.prompt_json if q else None,
            options_json=q.options_json if (q and show_correct) else None,
            correct_answer=q.correct_answer if (q and show_correct) else None,
            value=answer.value_json,
            auto_score=answer.auto_score if show_score else None,
            needs_review=answer.needs_review,
            is_correct=is_correct,
        ))

    return ResultOut(
        session_id=session.id,
        status=session.status,
        score_pct=session.score_pct if show_score else None,
        passed=session.passed if show_score else None,
        show_score=show_score,
        show_correct_answers=test.show_correct_answers,
        answers=answers_out,
    )
