import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import require_role
from app.db import get_db
from app.models.core import Answer, Question, Session, Test, User

router = APIRouter()


class SessionSummary(BaseModel):
    id: str
    test_id: str
    taker_email: str | None
    status: str
    review_status: str
    score_pct: int | None
    passed: bool | None
    started_at: str
    submitted_at: str | None


class AnswerDetail(BaseModel):
    question_id: str
    question_type: str
    prompt_json: dict
    options_json: list | dict | None
    correct_answer: dict | str | list | None
    value: dict | None
    auto_score: int | None
    manual_score: int | None
    needs_review: bool


class SessionDetail(BaseModel):
    id: str
    taker_email: str | None
    status: str
    review_status: str
    score_pct: int | None
    passed: bool | None
    started_at: str
    submitted_at: str | None
    answers: list[AnswerDetail]



@router.get("", response_model=list[SessionSummary])
async def list_sessions(
    test_id: str = Query(...),
    user: User = Depends(require_role("admin", "manager", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    # Verify test belongs to tenant
    test_res = await db.execute(
        select(Test).where(Test.id == test_id, Test.tenant_id == user.tenant_id)
    )
    if not test_res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Test not found")

    result = await db.execute(
        select(Session)
        .where(Session.test_id == test_id)
        .order_by(Session.started_at.desc())
    )
    sessions = result.scalars().all()
    return [
        SessionSummary(
            id=s.id, test_id=s.test_id, taker_email=s.taker_email,
            status=s.status, review_status=s.review_status,
            score_pct=s.score_pct, passed=s.passed,
            started_at=s.started_at.isoformat(),
            submitted_at=s.submitted_at.isoformat() if s.submitted_at else None,
        )
        for s in sessions
    ]


@router.get("/export/csv")
async def export_csv(
    test_id: str = Query(...),
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    test_res = await db.execute(
        select(Test).where(Test.id == test_id, Test.tenant_id == user.tenant_id)
    )
    test = test_res.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    sessions_res = await db.execute(
        select(Session)
        .where(Session.test_id == test_id, Session.status == "submitted")
        .options(selectinload(Session.answers))
        .order_by(Session.submitted_at)
    )
    sessions = sessions_res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["session_id", "taker_email", "status", "review_status", "score_pct", "passed", "started_at", "submitted_at"])
    for s in sessions:
        writer.writerow([s.id, s.taker_email, s.status, s.review_status, s.score_pct, s.passed, s.started_at, s.submitted_at])

    output.seek(0)
    filename = f"results-{test.title[:30].replace(' ', '_')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session_detail(
    session_id: str,
    user: User = Depends(require_role("admin", "manager", "reviewer")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Session)
        .where(Session.id == session_id)
        .options(selectinload(Session.answers))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Verify session's test belongs to tenant
    test_res = await db.execute(
        select(Test).where(Test.id == session.test_id, Test.tenant_id == user.tenant_id)
    )
    if not test_res.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Forbidden")

    q_ids = [a.question_id for a in session.answers]
    q_result = await db.execute(select(Question).where(Question.id.in_(q_ids)))
    questions = {q.id: q for q in q_result.scalars().all()}

    answers_out = []
    for a in session.answers:
        q = questions.get(a.question_id)
        answers_out.append(AnswerDetail(
            question_id=a.question_id,
            question_type=q.type if q else "unknown",
            prompt_json=q.prompt_json if q else {"type": "doc", "content": []},
            options_json=q.options_json if q else None,
            correct_answer=q.correct_answer if q else None,
            value=a.value_json,
            auto_score=a.auto_score,
            manual_score=a.manual_score,
            needs_review=a.needs_review,
        ))

    return SessionDetail(
        id=session.id, taker_email=session.taker_email,
        status=session.status, review_status=session.review_status,
        score_pct=session.score_pct, passed=session.passed,
        started_at=session.started_at.isoformat(),
        submitted_at=session.submitted_at.isoformat() if session.submitted_at else None,
        answers=answers_out,
    )
