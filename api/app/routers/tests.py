import csv
import io
import json
import mimetypes
import random
import secrets
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import require_role
from app.config import settings
from app.db import get_db
from app.models.core import MediaFile, Question, Test, TestBlock, TestBlockQuestion, User

router = APIRouter()

# Unambiguous uppercase alphanumeric chars (no 0/O, 1/I/L)
_CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


async def _generate_short_code(db: AsyncSession) -> str:
    """Generate a 6-char board-friendly code, retrying on collision."""
    for length in (6, 7, 8):
        for _ in range(20):
            code = "".join(random.choices(_CODE_CHARS, k=length))
            exists = (await db.execute(select(Test.id).where(Test.link_token == code))).scalar()
            if not exists:
                return code
    return secrets.token_urlsafe(6)  # last resort


# ── Schemas ──────────────────────────────────────────────────────────────────

class BlockQuestionIn(BaseModel):
    question_id: str
    order: int = 0


class BlockIn(BaseModel):
    title: str | None = None
    instructions: str | None = None
    context_json: dict | None = None
    order: int = 0
    questions: list[BlockQuestionIn] = []


class TestIn(BaseModel):
    title: str
    description: str | None = None
    mode: str = "async"
    access: str = "open"
    time_limit_minutes: int | None = None
    allow_multiple_attempts: bool = False
    max_attempts: int | None = None
    randomize_questions: bool = False
    randomize_options: bool = False
    show_score: str = "at_end"
    show_correct_answers: str = "never"
    passing_score_pct: int | None = None
    multiple_select_scoring: str = "all_or_nothing"
    draw_count: int | None = None
    available_from: datetime | None = None
    available_until: datetime | None = None
    practice_enabled: bool = False
    blocks: list[BlockIn] = []


class BlockQuestionOut(BaseModel):
    question_id: str
    order: int


class BlockOut(BaseModel):
    id: str
    title: str | None
    instructions_json: dict | None
    context_json: dict | None
    order: int
    questions: list[BlockQuestionOut]


class TestOut(BaseModel):
    id: str
    title: str
    description: str | None
    mode: str
    access: str
    time_limit_minutes: int | None
    allow_multiple_attempts: bool
    max_attempts: int | None
    randomize_questions: bool
    randomize_options: bool
    show_score: str
    show_correct_answers: str
    passing_score_pct: int | None
    multiple_select_scoring: str
    draw_count: int | None
    available_from: str | None
    available_until: str | None
    practice_enabled: bool
    link_token: str | None
    published_at: str | None
    blocks: list[BlockOut]
    created_at: str


# ── Detail schemas (include embedded question data) ───────────────────────────

class QuestionInBlock(BaseModel):
    id: str
    type: str
    prompt_json: dict | None
    options_json: Any
    correct_answer: Any
    explanation_json: dict | None
    points: int
    tags: list[str]


class BlockQuestionDetailOut(BaseModel):
    question_id: str
    order: int
    question: QuestionInBlock


class BlockDetailOut(BaseModel):
    id: str
    title: str | None
    instructions_json: dict | None
    context_json: dict | None
    order: int
    questions: list[BlockQuestionDetailOut]


class TestDetailOut(TestOut):
    blocks: list[BlockDetailOut]  # type: ignore[assignment]


def _wrap_text(text: str) -> dict:
    return {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": text}]}]}


def _block_out(block: TestBlock) -> BlockOut:
    return BlockOut(
        id=block.id,
        title=block.title,
        instructions_json=block.instructions_json,
        context_json=block.context_json,
        order=block.order,
        questions=[
            BlockQuestionOut(question_id=bq.question_id, order=bq.order)
            for bq in sorted(block.block_questions, key=lambda x: x.order)
        ],
    )


def _block_out_detail(block: TestBlock) -> BlockDetailOut:
    return BlockDetailOut(
        id=block.id,
        title=block.title,
        instructions_json=block.instructions_json,
        context_json=block.context_json,
        order=block.order,
        questions=[
            BlockQuestionDetailOut(
                question_id=bq.question_id,
                order=bq.order,
                question=QuestionInBlock(
                    id=bq.question.id,
                    type=bq.question.type,
                    prompt_json=bq.question.prompt_json,
                    options_json=bq.question.options_json,
                    correct_answer=bq.question.correct_answer,
                    explanation_json=bq.question.explanation_json,
                    points=bq.question.points,
                    tags=bq.question.tags or [],
                ),
            )
            for bq in sorted(block.block_questions, key=lambda x: x.order)
        ],
    )


def _test_out(test: Test) -> TestOut:
    return TestOut(
        id=test.id,
        title=test.title,
        description=test.description,
        mode=test.mode,
        access=test.access,
        time_limit_minutes=test.time_limit_minutes,
        allow_multiple_attempts=test.allow_multiple_attempts,
        max_attempts=test.max_attempts,
        randomize_questions=test.randomize_questions,
        randomize_options=test.randomize_options,
        show_score=test.show_score,
        show_correct_answers=test.show_correct_answers,
        passing_score_pct=test.passing_score_pct,
        multiple_select_scoring=test.multiple_select_scoring,
        draw_count=test.draw_count,
        available_from=test.available_from.isoformat() if test.available_from else None,
        available_until=test.available_until.isoformat() if test.available_until else None,
        practice_enabled=test.practice_enabled,
        link_token=test.link_token,
        published_at=test.published_at.isoformat() if test.published_at else None,
        blocks=[_block_out(b) for b in sorted(test.blocks, key=lambda x: x.order)],
        created_at=test.created_at.isoformat(),
    )


def _test_out_detail(test: Test) -> TestDetailOut:
    return TestDetailOut(
        id=test.id,
        title=test.title,
        description=test.description,
        mode=test.mode,
        access=test.access,
        time_limit_minutes=test.time_limit_minutes,
        allow_multiple_attempts=test.allow_multiple_attempts,
        max_attempts=test.max_attempts,
        randomize_questions=test.randomize_questions,
        randomize_options=test.randomize_options,
        show_score=test.show_score,
        show_correct_answers=test.show_correct_answers,
        passing_score_pct=test.passing_score_pct,
        multiple_select_scoring=test.multiple_select_scoring,
        draw_count=test.draw_count,
        available_from=test.available_from.isoformat() if test.available_from else None,
        available_until=test.available_until.isoformat() if test.available_until else None,
        practice_enabled=test.practice_enabled,
        link_token=test.link_token,
        published_at=test.published_at.isoformat() if test.published_at else None,
        blocks=[_block_out_detail(b) for b in sorted(test.blocks, key=lambda x: x.order)],
        created_at=test.created_at.isoformat(),
    )


async def _load_test(test_id: str, tenant_id: str, db: AsyncSession) -> Test:
    result = await db.execute(
        select(Test)
        .where(Test.id == test_id, Test.tenant_id == tenant_id, Test.deleted_at.is_(None))
        .options(
            selectinload(Test.blocks)
            .selectinload(TestBlock.block_questions)
            .selectinload(TestBlockQuestion.question)
        )
    )
    test = result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test


async def _apply_blocks(test: Test, blocks_in: list[BlockIn], tenant_id: str, db: AsyncSession):
    # Remove existing blocks
    for block in test.blocks:
        for bq in block.block_questions:
            await db.delete(bq)
        await db.delete(block)
    await db.flush()

    # Validate all question IDs belong to this tenant
    all_q_ids = [bq.question_id for b in blocks_in for bq in b.questions]
    if all_q_ids:
        result = await db.execute(
            select(Question.id).where(
                Question.id.in_(all_q_ids),
                Question.tenant_id == tenant_id,
                Question.deleted_at.is_(None),
            )
        )
        found_ids = {row[0] for row in result.all()}
        missing = set(all_q_ids) - found_ids
        if missing:
            raise HTTPException(status_code=400, detail=f"Questions not found: {missing}")

    for b in blocks_in:
        block = TestBlock(
            test_id=test.id,
            order=b.order,
            title=b.title,
            instructions_json=_wrap_text(b.instructions) if b.instructions else None,
            context_json=b.context_json,
        )
        db.add(block)
        await db.flush()
        for q_in in b.questions:
            db.add(TestBlockQuestion(block_id=block.id, question_id=q_in.question_id, order=q_in.order))


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[TestOut])
async def list_tests(
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Test)
        .where(Test.tenant_id == user.tenant_id, Test.deleted_at.is_(None))
        .options(selectinload(Test.blocks).selectinload(TestBlock.block_questions))
        .order_by(Test.created_at.desc())
    )
    return [_test_out(t) for t in result.scalars().all()]


@router.get("/{test_id}", response_model=TestDetailOut)
async def get_test(
    test_id: str,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    return _test_out_detail(await _load_test(test_id, user.tenant_id, db))


@router.post("", response_model=TestOut, status_code=status.HTTP_201_CREATED)
async def create_test(
    body: TestIn,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    test = Test(
        tenant_id=user.tenant_id,
        created_by=user.id,
        title=body.title,
        description=body.description,
        mode=body.mode,
        access=body.access,
        time_limit_minutes=body.time_limit_minutes,
        allow_multiple_attempts=body.allow_multiple_attempts,
        max_attempts=body.max_attempts,
        randomize_questions=body.randomize_questions,
        randomize_options=body.randomize_options,
        show_score=body.show_score,
        show_correct_answers=body.show_correct_answers,
        passing_score_pct=body.passing_score_pct,
        multiple_select_scoring=body.multiple_select_scoring,
        draw_count=body.draw_count,
        available_from=body.available_from,
        available_until=body.available_until,
        practice_enabled=body.practice_enabled,
        blocks=[],
    )
    db.add(test)
    await db.flush()
    await _apply_blocks(test, body.blocks, user.tenant_id, db)
    await db.commit()
    return _test_out(await _load_test(test.id, user.tenant_id, db))


@router.put("/{test_id}", response_model=TestOut)
async def update_test(
    test_id: str,
    body: TestIn,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    test = await _load_test(test_id, user.tenant_id, db)
    test.title = body.title
    test.description = body.description
    test.mode = body.mode
    test.access = body.access
    test.time_limit_minutes = body.time_limit_minutes
    test.allow_multiple_attempts = body.allow_multiple_attempts
    test.max_attempts = body.max_attempts
    test.randomize_questions = body.randomize_questions
    test.randomize_options = body.randomize_options
    test.show_score = body.show_score
    test.show_correct_answers = body.show_correct_answers
    test.passing_score_pct = body.passing_score_pct
    test.multiple_select_scoring = body.multiple_select_scoring
    test.draw_count = body.draw_count
    test.available_from = body.available_from
    test.available_until = body.available_until
    test.practice_enabled = body.practice_enabled
    await _apply_blocks(test, body.blocks, user.tenant_id, db)
    await db.commit()
    return _test_out(await _load_test(test_id, user.tenant_id, db))


@router.post("/{test_id}/publish", response_model=TestOut)
async def publish_test(
    test_id: str,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    test = await _load_test(test_id, user.tenant_id, db)
    if not test.blocks or not any(b.block_questions for b in test.blocks):
        raise HTTPException(status_code=400, detail="Test must have at least one question before publishing")
    if not test.link_token:
        test.link_token = await _generate_short_code(db)
    test.published_at = datetime.now(timezone.utc)
    await db.commit()
    return _test_out(await _load_test(test_id, user.tenant_id, db))


@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_test(
    test_id: str,
    user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    test = await _load_test(test_id, user.tenant_id, db)
    test.deleted_at = datetime.now(timezone.utc)
    await db.commit()


# ── Clone ─────────────────────────────────────────────────────────────────────

@router.post("/{test_id}/clone", response_model=TestOut, status_code=status.HTTP_201_CREATED)
async def clone_test(
    test_id: str,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """
    Duplicate a test (and all its blocks/questions) as a brand-new unpublished test.
    Questions are cloned as new independent copies so edits don't affect the original.
    """
    source = await _load_test(test_id, user.tenant_id, db)

    # Fetch full question data
    all_q_ids = [bq.question_id for b in source.blocks for bq in b.block_questions]
    questions_map: dict[str, Question] = {}
    if all_q_ids:
        result = await db.execute(select(Question).where(Question.id.in_(all_q_ids)))
        for q in result.scalars():
            questions_map[q.id] = q

    new_test = Test(
        tenant_id=user.tenant_id,
        created_by=user.id,
        title=f"{source.title} (copy)",
        description=source.description,
        mode=source.mode,
        access=source.access,
        time_limit_minutes=source.time_limit_minutes,
        allow_multiple_attempts=source.allow_multiple_attempts,
        max_attempts=source.max_attempts,
        randomize_questions=source.randomize_questions,
        randomize_options=source.randomize_options,
        show_score=source.show_score,
        show_correct_answers=source.show_correct_answers,
        passing_score_pct=source.passing_score_pct,
        multiple_select_scoring=source.multiple_select_scoring,
        draw_count=source.draw_count,
        available_from=source.available_from,
        available_until=source.available_until,
        blocks=[],
    )
    db.add(new_test)
    await db.flush()

    for block in sorted(source.blocks, key=lambda b: b.order):
        new_block = TestBlock(
            test_id=new_test.id,
            order=block.order,
            title=block.title,
            instructions_json=block.instructions_json,
            context_json=block.context_json,
        )
        db.add(new_block)
        await db.flush()
        for bq in sorted(block.block_questions, key=lambda x: x.order):
            src_q = questions_map.get(bq.question_id)
            if not src_q:
                continue
            new_q = Question(
                tenant_id=user.tenant_id,
                type=src_q.type,
                prompt_json=src_q.prompt_json,
                options_json=src_q.options_json,
                correct_answer=src_q.correct_answer,
                explanation_json=src_q.explanation_json,
                points=src_q.points,
                tags=src_q.tags,
            )
            db.add(new_q)
            await db.flush()
            db.add(TestBlockQuestion(block_id=new_block.id, question_id=new_q.id, order=bq.order))

    await db.commit()
    return _test_out(await _load_test(new_test.id, user.tenant_id, db))


# ── CSV import ────────────────────────────────────────────────────────────────

@router.post("/import-csv", response_model=TestOut, status_code=status.HTTP_201_CREATED)
async def import_csv(
    file: UploadFile = File(...),
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """
    Import questions from a CSV file and create a new test.

    Expected columns (header row required):
      type, prompt, options, correct_answer, points, tags, block

    - type: multiple_choice | multiple_select | true_false | short_text | long_text
    - prompt: plain text (will be wrapped in Tiptap paragraph)
    - options: pipe-separated list for choice types, e.g. "Paris|London|Berlin"
    - correct_answer: single value for mc/tf ("Paris"), comma-separated for ms ("A,C"),
                      or plain text for short_text
    - points: integer (default 1)
    - tags: comma-separated tag list (optional)
    - block: block title to group questions into (optional; all go into one block if omitted)

    The filename (without extension) is used as the test title.
    """
    data = await file.read()
    text = data.decode("utf-8-sig")  # handle BOM from Excel exports
    reader = csv.DictReader(io.StringIO(text))

    # Group rows by block title, preserving insertion order
    from collections import OrderedDict
    blocks_dict: dict[str, list[dict]] = OrderedDict()

    for row in reader:
        block_title = (row.get("block") or "").strip() or "Questions"
        if block_title not in blocks_dict:
            blocks_dict[block_title] = []
        blocks_dict[block_title].append(row)

    if not blocks_dict:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no data rows")

    # Derive test title from filename
    test_title = "Imported Test"
    if file.filename:
        stem = Path(file.filename).stem
        if stem:
            test_title = stem.replace("_", " ").replace("-", " ").title()

    test = Test(
        tenant_id=user.tenant_id,
        created_by=user.id,
        title=test_title,
        blocks=[],
    )
    db.add(test)
    await db.flush()

    for block_order, (block_title, rows) in enumerate(blocks_dict.items()):
        block = TestBlock(
            test_id=test.id,
            order=block_order,
            title=block_title if block_title != "Questions" else None,
        )
        db.add(block)
        await db.flush()

        for q_order, row in enumerate(rows):
            qtype = (row.get("type") or "short_text").strip().lower()
            prompt_text = (row.get("prompt") or "").strip()
            options_raw = (row.get("options") or "").strip()
            correct_raw = (row.get("correct_answer") or "").strip()
            points_raw = (row.get("points") or "1").strip()
            tags_raw = (row.get("tags") or "").strip()

            # Build options_json list for choice types
            options_json = None
            if qtype in ("multiple_choice", "multiple_select") and options_raw:
                options_json = [o.strip() for o in options_raw.split("|") if o.strip()]

            # Build correct_answer
            correct_answer: Any = None
            if qtype == "multiple_choice":
                correct_answer = {"value": correct_raw} if correct_raw else None
            elif qtype == "multiple_select":
                vals = [v.strip() for v in correct_raw.split(",") if v.strip()]
                correct_answer = {"values": vals} if vals else None
            elif qtype == "true_false":
                correct_answer = {"value": correct_raw.lower()} if correct_raw else None
            elif qtype == "short_text":
                correct_answer = {"text": correct_raw} if correct_raw else None

            tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

            q = Question(
                tenant_id=user.tenant_id,
                type=qtype,
                prompt_json=_wrap_text(prompt_text),
                options_json=options_json,
                correct_answer=correct_answer,
                points=int(points_raw) if points_raw.isdigit() else 1,
                tags=tags,
            )
            db.add(q)
            await db.flush()
            db.add(TestBlockQuestion(block_id=block.id, question_id=q.id, order=q_order))

    await db.commit()
    return _test_out(await _load_test(test.id, user.tenant_id, db))


# ── Media utilities ───────────────────────────────────────────────────────────

def _collect_media_ids(node: Any) -> set[str]:
    """Recursively collect all media_file_id values from a Tiptap JSON structure."""
    if not node:
        return set()
    ids: set[str] = set()
    if isinstance(node, list):
        for item in node:
            ids |= _collect_media_ids(item)
    elif isinstance(node, dict):
        attrs = node.get("attrs") or {}
        if "media_file_id" in attrs and attrs["media_file_id"]:
            ids.add(str(attrs["media_file_id"]))
        for v in node.values():
            if isinstance(v, (dict, list)):
                ids |= _collect_media_ids(v)
    return ids


def _rewrite_media_ids(node: Any, id_map: dict[str, str]) -> None:
    """In-place rewrite of media_file_id values using id_map (old_id → new_id)."""
    if isinstance(node, list):
        for item in node:
            _rewrite_media_ids(item, id_map)
    elif isinstance(node, dict):
        attrs = node.get("attrs") or {}
        if "media_file_id" in attrs and attrs["media_file_id"] in id_map:
            attrs["media_file_id"] = id_map[attrs["media_file_id"]]
        for v in node.values():
            if isinstance(v, (dict, list)):
                _rewrite_media_ids(v, id_map)


def _extract_text(node: Any) -> str:
    """Walk a Tiptap JSON doc tree and return concatenated plain text."""
    if not node or not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return node.get("text", "")
    block_types = {"paragraph", "heading", "blockquote", "listItem", "bulletList", "orderedList"}
    parts: list[str] = []
    for child in node.get("content") or []:
        parts.append(_extract_text(child))
    sep = " " if node.get("type") in block_types else ""
    return sep.join(p for p in parts if p).strip()


def _to_practice_bundle(test: Test, questions_map: dict[str, Question]) -> dict:
    """Build the normalized TestBundle payload expected by the mobile app."""
    blocks_out = []
    for block in sorted(test.blocks, key=lambda b: b.order):
        questions_out = []
        for bq in sorted(block.block_questions, key=lambda x: x.order):
            q = questions_map.get(bq.question_id)  # type: ignore[assignment]
            if not q:
                continue
            options: list[dict] | None = None
            media_file_id: str | None = None
            if isinstance(q.options_json, list):
                options = [
                    {"id": opt.get("id", ""), "text": _extract_text(opt.get("content_json"))}
                    for opt in q.options_json
                ]
            elif isinstance(q.options_json, dict):
                media_file_id = q.options_json.get("media_file_id")
            questions_out.append({
                "id": q.id,
                "type": q.type,
                "prompt": q.prompt_json,
                "options": options,
                "media_file_id": media_file_id,
                "correct_answer": q.correct_answer,
                "points": q.points,
                "tags": q.tags or [],
            })
        blocks_out.append({
            "id": block.id,
            "title": block.title or "",
            "context_json": block.context_json,
            "questions": questions_out,
        })
    return {
        "id": test.id,
        "title": test.title,
        "show_correct_answers": test.show_correct_answers,
        "randomize_questions": test.randomize_questions,
        "randomize_options": test.randomize_options,
        "draw_count": test.draw_count,
        "blocks": blocks_out,
    }


def _test_export_payload(test: Test, questions_map: dict[str, Question]) -> dict:
    """Build the portable JSON payload for a test (used by both JSON and ZIP export)."""
    blocks_data = []
    for block in sorted(test.blocks, key=lambda b: b.order):
        questions_data = []
        for bq in sorted(block.block_questions, key=lambda x: x.order):
            q = questions_map.get(bq.question_id)
            if not q:
                continue
            media_ref = None
            options_json = q.options_json
            if q.type in ("audio_prompt", "video_prompt") and isinstance(options_json, dict):
                media_ref = options_json
                options_json = None
            questions_data.append({
                "type": q.type,
                "prompt_json": q.prompt_json,
                "options_json": options_json,
                "correct_answer": q.correct_answer,
                "explanation_json": q.explanation_json,
                "media_ref": media_ref,
                "points": q.points,
                "tags": q.tags,
            })
        blocks_data.append({
            "title": block.title,
            "order": block.order,
            "context_json": block.context_json,   # ← was missing before
            "questions": questions_data,
        })

    return {
        "quizbee_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "test": {
            "title": test.title,
            "description": test.description,
            "mode": test.mode,
            "access": test.access,
            "time_limit_minutes": test.time_limit_minutes,
            "allow_multiple_attempts": test.allow_multiple_attempts,
            "max_attempts": test.max_attempts,
            "randomize_questions": test.randomize_questions,
            "randomize_options": test.randomize_options,
            "show_score": test.show_score,
            "show_correct_answers": test.show_correct_answers,
            "passing_score_pct": test.passing_score_pct,
            "multiple_select_scoring": test.multiple_select_scoring,
            "draw_count": test.draw_count,
            "blocks": blocks_data,
        },
    }


# ── Import / Export ───────────────────────────────────────────────────────────

@router.get("/{test_id}/preview")
async def preview_test(
    test_id: str,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Return full test content (with question details) for admin preview — no session created."""
    test = await _load_test(test_id, user.tenant_id, db)

    all_q_ids = [bq.question_id for b in test.blocks for bq in b.block_questions]
    questions_map: dict[str, Question] = {}
    if all_q_ids:
        result = await db.execute(select(Question).where(Question.id.in_(all_q_ids)))
        for q in result.scalars():
            questions_map[q.id] = q

    blocks_out = []
    for block in sorted(test.blocks, key=lambda b: b.order):
        questions_out = []
        for bq in sorted(block.block_questions, key=lambda x: x.order):
            q = questions_map.get(bq.question_id)  # type: ignore[assignment]
            if not q:
                continue
            questions_out.append({
                "id": q.id,
                "type": q.type,
                "prompt_json": q.prompt_json,
                "options_json": q.options_json,
                "correct_answer": q.correct_answer,
                "explanation_json": q.explanation_json,
                "points": q.points,
                "order": bq.order,
            })
        blocks_out.append({"title": block.title, "order": block.order, "questions": questions_out})

    return {"id": test.id, "title": test.title, "blocks": blocks_out}


@router.get("/{test_id}/export")
async def export_test(
    test_id: str,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Export a test as JSON (no media) or ZIP (with media assets bundled)."""
    test = await _load_test(test_id, user.tenant_id, db)

    all_q_ids = [bq.question_id for b in test.blocks for bq in b.block_questions]
    questions_map: dict[str, Question] = {}
    if all_q_ids:
        result = await db.execute(select(Question).where(Question.id.in_(all_q_ids)))
        for q in result.scalars():
            questions_map[q.id] = q

    payload = _test_export_payload(test, questions_map)
    slug = test.title.lower().replace(" ", "_")[:30]

    # Collect all media_file_ids referenced anywhere in the test
    all_media_ids: set[str] = set()
    for block in test.blocks:
        all_media_ids |= _collect_media_ids(block.context_json)
    for q in questions_map.values():
        all_media_ids |= _collect_media_ids(q.prompt_json)
        all_media_ids |= _collect_media_ids(q.options_json)

    # No media → plain JSON export
    if not all_media_ids:
        return JSONResponse(
            content=payload,
            headers={"Content-Disposition": f'attachment; filename="quizbee_{slug}.json"'},
        )

    # Has media → load media records and build ZIP
    media_result = await db.execute(
        select(MediaFile).where(MediaFile.id.in_(all_media_ids))
    )
    media_map: dict[str, MediaFile] = {m.id: m for m in media_result.scalars()}

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("test.json", json.dumps(payload, ensure_ascii=False, indent=2))
        for media_id, m in media_map.items():
            full_path = Path(settings.media_root) / m.storage_path
            if full_path.exists():
                ext = Path(m.filename).suffix or (mimetypes.guess_extension(m.mime_type) or "")
                zf.write(str(full_path), arcname=f"assets/{media_id}{ext}")

    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="quizbee_{slug}.zip"'},
    )


@router.get("/{test_id}/practice-bundle")
async def practice_bundle(
    test_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — returns the test as a practice bundle JSON for the mobile app.
    Only available when practice_enabled is True on the test."""
    result = await db.execute(
        select(Test)
        .where(Test.id == test_id, Test.deleted_at.is_(None))
        .options(
            selectinload(Test.blocks)
            .selectinload(TestBlock.block_questions)
            .selectinload(TestBlockQuestion.question)
        )
    )
    test = result.scalar_one_or_none()
    if not test or not test.practice_enabled:
        raise HTTPException(status_code=404, detail="Practice bundle not available for this test")

    all_q_ids = [bq.question_id for b in test.blocks for bq in b.block_questions]
    questions_map: dict[str, Question] = {}
    if all_q_ids:
        q_result = await db.execute(select(Question).where(Question.id.in_(all_q_ids)))
        for q in q_result.scalars():
            questions_map[q.id] = q

    return JSONResponse(content=_to_practice_bundle(test, questions_map))


@router.post("/import", response_model=TestOut, status_code=status.HTTP_201_CREATED)
async def import_test(
    body: dict,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Import a test from a Quizbee JSON export. Creates all questions and the test in one transaction."""
    # Support both {quizbee_version, test: {...}} envelope and bare test dict
    test_data: dict = body.get("test", body)

    # Create questions block by block, preserving order
    blocks_raw = test_data.get("blocks", [])
    created_blocks: list[tuple[dict, list[str]]] = []

    for block_data in blocks_raw:
        q_ids: list[str] = []
        for q_data in block_data.get("questions", []):
            prompt_json = q_data.get("prompt_json") or _wrap_text(q_data.get("prompt") or "")

            options_json = q_data.get("options_json")
            # Restore media_ref into options_json for audio/video types
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
            q_ids.append(q.id)
        created_blocks.append((block_data, q_ids))

    # Create the test
    test = Test(
        tenant_id=user.tenant_id,
        created_by=user.id,
        title=test_data.get("title", "Imported Test"),
        description=test_data.get("description"),
        mode=test_data.get("mode", "async"),
        access=test_data.get("access", "open"),
        time_limit_minutes=test_data.get("time_limit_minutes"),
        allow_multiple_attempts=bool(test_data.get("allow_multiple_attempts", False)),
        max_attempts=test_data.get("max_attempts"),
        randomize_questions=bool(test_data.get("randomize_questions", False)),
        randomize_options=bool(test_data.get("randomize_options", False)),
        show_score=test_data.get("show_score", "at_end"),
        show_correct_answers=test_data.get("show_correct_answers", "never"),
        passing_score_pct=test_data.get("passing_score_pct"),
        multiple_select_scoring=test_data.get("multiple_select_scoring", "all_or_nothing"),
        draw_count=test_data.get("draw_count"),
        blocks=[],
    )
    db.add(test)
    await db.flush()

    for i, (block_data, q_ids) in enumerate(created_blocks):
        block = TestBlock(
            test_id=test.id,
            order=int(block_data.get("order", i)),
            title=block_data.get("title"),
            context_json=block_data.get("context_json"),
        )
        db.add(block)
        await db.flush()
        for j, q_id in enumerate(q_ids):
            db.add(TestBlockQuestion(block_id=block.id, question_id=q_id, order=j))

    await db.commit()
    return _test_out(await _load_test(test.id, user.tenant_id, db))


@router.post("/import-bundle", response_model=TestOut, status_code=status.HTTP_201_CREATED)
async def import_test_bundle(
    file: UploadFile = File(...),
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Import a test from a ZIP bundle (test.json + assets/) produced by the export endpoint."""
    data = await file.read()

    # Accept .zip or plain .json via this endpoint
    is_zip = file.filename and file.filename.endswith(".zip")
    if not is_zip:
        # Treat as plain JSON for convenience
        body = json.loads(data)
        # Re-use existing import logic by delegating through the same helper path
        test_data: dict = body.get("test", body)
        id_map: dict[str, str] = {}
    else:
        try:
            zf_buf = io.BytesIO(data)
            with zipfile.ZipFile(zf_buf, "r") as zf:
                if "test.json" not in zf.namelist():
                    raise HTTPException(status_code=400, detail="ZIP must contain test.json")
                test_body = json.loads(zf.read("test.json"))
                test_data = test_body.get("test", test_body)

                # Upload each asset and build old_id → new_id map
                id_map = {}
                asset_names = [n for n in zf.namelist() if n.startswith("assets/") and n != "assets/"]
                for asset_name in asset_names:
                    stem = Path(asset_name).stem          # original media_file_id
                    ext = Path(asset_name).suffix
                    mime = mimetypes.guess_type(asset_name)[0] or "application/octet-stream"
                    asset_data = zf.read(asset_name)

                    new_media_id = str(uuid.uuid4())
                    safe_filename = f"{stem}{ext}"
                    rel_path = f"{user.tenant_id}/{new_media_id}/{safe_filename}"
                    full_path = Path(settings.media_root) / rel_path
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    full_path.write_bytes(asset_data)

                    record = MediaFile(
                        id=new_media_id,
                        tenant_id=user.tenant_id,
                        filename=safe_filename,
                        mime_type=mime,
                        size_bytes=len(asset_data),
                        storage_path=str(rel_path),
                    )
                    db.add(record)
                    await db.flush()
                    id_map[stem] = new_media_id

        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")

    # Rewrite media_file_id references in all Tiptap JSON fields
    if id_map:
        for block_data in test_data.get("blocks", []):
            _rewrite_media_ids(block_data.get("context_json"), id_map)
            for q_data in block_data.get("questions", []):
                _rewrite_media_ids(q_data.get("prompt_json"), id_map)
                _rewrite_media_ids(q_data.get("options_json"), id_map)

    # Create questions and test (same logic as import_test)
    blocks_raw = test_data.get("blocks", [])
    created_blocks: list[tuple[dict, list[str]]] = []

    for block_data in blocks_raw:
        q_ids: list[str] = []
        for q_data in block_data.get("questions", []):
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
            q_ids.append(q.id)
        created_blocks.append((block_data, q_ids))

    test = Test(
        tenant_id=user.tenant_id,
        created_by=user.id,
        title=test_data.get("title", "Imported Test"),
        description=test_data.get("description"),
        mode=test_data.get("mode", "async"),
        access=test_data.get("access", "open"),
        time_limit_minutes=test_data.get("time_limit_minutes"),
        allow_multiple_attempts=bool(test_data.get("allow_multiple_attempts", False)),
        max_attempts=test_data.get("max_attempts"),
        randomize_questions=bool(test_data.get("randomize_questions", False)),
        randomize_options=bool(test_data.get("randomize_options", False)),
        show_score=test_data.get("show_score", "at_end"),
        show_correct_answers=test_data.get("show_correct_answers", "never"),
        passing_score_pct=test_data.get("passing_score_pct"),
        multiple_select_scoring=test_data.get("multiple_select_scoring", "all_or_nothing"),
        draw_count=test_data.get("draw_count"),
        blocks=[],
    )
    db.add(test)
    await db.flush()

    for i, (block_data, q_ids) in enumerate(created_blocks):
        block = TestBlock(
            test_id=test.id,
            order=int(block_data.get("order", i)),
            title=block_data.get("title"),
            context_json=block_data.get("context_json"),
        )
        db.add(block)
        await db.flush()
        for j, q_id in enumerate(q_ids):
            db.add(TestBlockQuestion(block_id=block.id, question_id=q_id, order=j))

    await db.commit()
    return _test_out(await _load_test(test.id, user.tenant_id, db))


@router.get("/{test_id}/export-questions")
async def export_test_questions(
    test_id: str,
    user: User = Depends(require_role("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Export just the questions for a test as a portable questions.json file."""
    test = await _load_test(test_id, user.tenant_id, db)

    all_q_ids = [bq.question_id for b in test.blocks for bq in b.block_questions]
    questions_map: dict[str, Question] = {}
    if all_q_ids:
        result = await db.execute(select(Question).where(Question.id.in_(all_q_ids)))
        for q in result.scalars():
            questions_map[q.id] = q

    questions_data = []
    for q_id in all_q_ids:
        q = questions_map.get(q_id)  # type: ignore[assignment]
        if not q:
            continue
        media_ref = None
        options_json = q.options_json
        if q.type in ("audio_prompt", "video_prompt") and isinstance(options_json, dict):
            media_ref = options_json
            options_json = None
        questions_data.append({
            "type": q.type,
            "prompt_json": q.prompt_json,
            "options_json": options_json,
            "correct_answer": q.correct_answer,
            "explanation_json": q.explanation_json,
            "media_ref": media_ref,
            "points": q.points,
            "tags": q.tags,
        })

    payload: dict[str, Any] = {
        "quizbee_version": "1.0",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source_test": test.title,
        "questions": questions_data,
    }

    slug = test.title.lower().replace(" ", "_")[:30]
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="quizbee_{slug}_questions.json"'},
    )
