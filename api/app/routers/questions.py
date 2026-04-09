from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user, require_role
from app.db import get_db
from app.models.core import Question, User

router = APIRouter()

ALLOWED_TYPES = {
    # Phase 1
    "multiple_choice", "multiple_select", "true_false",
    "short_text", "long_text",
    "passage", "divider",
    # Phase 2
    "audio_prompt", "video_prompt",
}


def _wrap_text(text: str) -> dict:
    """Wrap a plain string in a minimal Tiptap paragraph node."""
    return {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


class OptionIn(BaseModel):
    id: str
    text: str


class QuestionIn(BaseModel):
    type: str
    # Rich text: send prompt_json (Tiptap JSON) from Phase 2 editor; or plain text prompt (wrapped automatically)
    prompt_json: dict | None = None
    prompt: str | None = None
    options: list[OptionIn] | None = None
    # For audio_prompt / video_prompt: {"media_file_id": "...", "mime_type": "..."}
    media_ref: dict | None = None
    correct_answer: dict | str | list | None = None
    explanation_json: dict | None = None
    explanation: str | None = None
    points: int = 1
    tags: list[str] = []


class QuestionOut(BaseModel):
    id: str
    type: str
    prompt_json: dict
    options_json: list | None
    correct_answer: dict | str | list | None
    explanation_json: dict | None
    points: int
    tags: list
    created_at: str
    updated_at: str


def _to_out(q: Question) -> QuestionOut:
    return QuestionOut(
        id=q.id,
        type=q.type,
        prompt_json=q.prompt_json,
        options_json=q.options_json,
        correct_answer=q.correct_answer,
        explanation_json=q.explanation_json,
        points=q.points,
        tags=q.tags,
        created_at=q.created_at.isoformat(),
        updated_at=q.updated_at.isoformat(),
    )


@router.get("", response_model=list[QuestionOut])
async def list_questions(
    type: str | None = Query(None),
    tag: str | None = Query(None),
    search: str | None = Query(None),
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Question).where(
        Question.tenant_id == user.tenant_id,
        Question.deleted_at.is_(None),
    )
    if type:
        stmt = stmt.where(Question.type == type)
    if tag:
        stmt = stmt.where(Question.tags.contains([tag]))
    stmt = stmt.order_by(Question.created_at.desc())
    result = await db.execute(stmt)
    questions = result.scalars().all()

    if search:
        s = search.lower()
        questions = [q for q in questions if s in str(q.prompt_json).lower()]

    return [_to_out(q) for q in questions]


@router.get("/{question_id}", response_model=QuestionOut)
async def get_question(
    question_id: str,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.tenant_id == user.tenant_id,
            Question.deleted_at.is_(None),
        )
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return _to_out(q)


def _resolve_prompt(body: QuestionIn) -> dict:
    if body.prompt_json:
        return body.prompt_json
    return _wrap_text(body.prompt or "")


def _resolve_explanation(body: QuestionIn) -> dict | None:
    if body.explanation_json:
        return body.explanation_json
    if body.explanation:
        return _wrap_text(body.explanation)
    return None


@router.post("", response_model=QuestionOut, status_code=status.HTTP_201_CREATED)
async def create_question(
    body: QuestionIn,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    if body.type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported question type: {body.type}")

    options_json = None
    if body.options:
        options_json = [{"id": o.id, "content_json": _wrap_text(o.text)} for o in body.options]
    elif body.media_ref:
        options_json = body.media_ref

    q = Question(
        tenant_id=user.tenant_id,
        type=body.type,
        prompt_json=_resolve_prompt(body),
        options_json=options_json,
        correct_answer=body.correct_answer,
        explanation_json=_resolve_explanation(body),
        points=body.points,
        tags=body.tags,
    )
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return _to_out(q)


@router.put("/{question_id}", response_model=QuestionOut)
async def update_question(
    question_id: str,
    body: QuestionIn,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.tenant_id == user.tenant_id,
            Question.deleted_at.is_(None),
        )
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")

    options_json = None
    if body.options:
        options_json = [{"id": o.id, "content_json": _wrap_text(o.text)} for o in body.options]
    elif body.media_ref:
        options_json = body.media_ref

    q.type = body.type
    q.prompt_json = _resolve_prompt(body)
    q.options_json = options_json
    q.correct_answer = body.correct_answer
    q.explanation_json = _resolve_explanation(body)
    q.points = body.points
    q.tags = body.tags
    q.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(q)
    return _to_out(q)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: str,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Question).where(
            Question.id == question_id,
            Question.tenant_id == user.tenant_id,
            Question.deleted_at.is_(None),
        )
    )
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    q.deleted_at = datetime.now(timezone.utc)
    await db.commit()


class BulkImportResponse(BaseModel):
    created: int
    question_ids: list[str]


@router.post("/bulk-import", response_model=BulkImportResponse, status_code=status.HTTP_201_CREATED)
async def bulk_import_questions(
    body: dict,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Import a list of questions from a questions.json file into the tenant's question bank.
    Accepts either {quizbee_version, questions: [...]} or a bare list.
    """
    questions_data: list = body.get("questions", body) if isinstance(body, dict) else body
    if not isinstance(questions_data, list):
        raise HTTPException(status_code=400, detail="Expected a list of questions or {questions: [...]}")

    created_ids: list[str] = []
    for q_data in questions_data:
        prompt_json = q_data.get("prompt_json") or _wrap_text(q_data.get("prompt") or "")
        options_json = q_data.get("options_json")
        if not options_json and q_data.get("media_ref"):
            options_json = q_data["media_ref"]

        q = Question(
            tenant_id=user.tenant_id,
            type=q_data.get("type", "short_text"),
            prompt_json=prompt_json,
            options_json=options_json,
            correct_answer=q_data.get("correct_answer"),
            explanation_json=q_data.get("explanation_json"),
            points=int(q_data.get("points", 1)),
            tags=q_data.get("tags", []),
        )
        db.add(q)
        await db.flush()
        created_ids.append(q.id)

    await db.commit()
    return BulkImportResponse(created=len(created_ids), question_ids=created_ids)
