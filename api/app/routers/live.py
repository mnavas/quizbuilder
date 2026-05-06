"""
Live game (Kahoot-style trivia) endpoints.

Flow
----
1. POST /live/games              → manager creates a game from a test, gets a PIN
2. POST /live/join               → player joins by PIN + nickname, gets player_id
3. GET  /live/games/{id}/state   → everyone polls this (~1 s); auto-closes when timer expires
4. POST /live/games/{id}/next    → manager advances state
5. POST /live/games/{id}/answer  → player submits answer for the active question
6. GET  /live/games/{id}/player/{pid}/result → player fetches their score after question closes

State machine
-------------
waiting → question_active → question_closed → question_active → … → finished

Scoring
-------
Correct answer: points = question.points × 1000 × (0.5 + 0.5 × (1 − time_ms / time_limit_ms))
Wrong answer:   0 points
"""

import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.db import get_db
from app.models.core import LiveAnswer, LiveGame, LivePlayer, Question, Test, TestBlock, User
from app.scoring import score_answer

router = APIRouter()

AVATAR_COLORS = [
    "#ef4444", "#f97316", "#eab308", "#22c55e",
    "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899",
    "#14b8a6", "#f59e0b", "#84cc16", "#6366f1",
]

LIVE_QUESTION_TYPES = {"multiple_choice", "true_false"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _compute_points(question: Question, time_ms: int, time_limit_ms: int) -> int:
    ratio = max(0.0, 1.0 - time_ms / max(time_limit_ms, 1))
    return round(question.points * 1000 * (0.5 + 0.5 * ratio))


async def _get_game(game_id: str, db: AsyncSession) -> LiveGame:
    result = await db.execute(select(LiveGame).where(LiveGame.id == game_id))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


async def _close_question(game: LiveGame, db: AsyncSession) -> None:
    """Score unanswered players (0 pts) and move to question_closed."""
    q_id = game.question_ids_json[game.current_question_index]

    answered_result = await db.execute(
        select(LiveAnswer.player_id).where(
            LiveAnswer.game_id == game.id,
            LiveAnswer.question_id == q_id,
        )
    )
    answered_ids = {row[0] for row in answered_result.all()}

    players_result = await db.execute(
        select(LivePlayer).where(LivePlayer.game_id == game.id)
    )
    now = datetime.now(timezone.utc)
    for player in players_result.scalars().all():
        if player.id not in answered_ids:
            db.add(LiveAnswer(
                game_id=game.id,
                player_id=player.id,
                question_id=q_id,
                value_json=None,
                answered_at=now,
                time_ms=game.time_limit_seconds * 1000 + 1,
                points_earned=0,
                is_correct=False,
            ))

    game.state = "question_closed"


# ── Schemas ───────────────────────────────────────────────────────────────────

class CreateGameRequest(BaseModel):
    test_id: str
    time_limit_seconds: int = 20


class JoinRequest(BaseModel):
    pin: str
    nickname: str


class AnswerRequest(BaseModel):
    player_id: str
    value: dict


class PlayerInLobby(BaseModel):
    nickname: str
    avatar_color: str


class LiveQuestionOut(BaseModel):
    id: str
    type: str
    prompt_json: dict
    options_json: list | None


class LeaderboardEntry(BaseModel):
    nickname: str
    avatar_color: str
    points_earned: int | None
    is_correct: bool | None
    total_score: int
    rank: int


class GameStateOut(BaseModel):
    state: str
    game_id: str
    pin: str
    question_index: int
    question_count: int
    time_limit_seconds: int
    players: list[PlayerInLobby] | None = None
    question: LiveQuestionOut | None = None
    time_remaining_ms: int | None = None
    answered_count: int | None = None
    player_count: int | None = None
    correct_answer: dict | str | None = None
    options_json: list | None = None
    top_question: list[LeaderboardEntry] | None = None
    top_cumulative: list[LeaderboardEntry] | None = None


# ── State builder ─────────────────────────────────────────────────────────────

async def _build_state(game: LiveGame, db: AsyncSession) -> GameStateOut:
    base = dict(
        state=game.state,
        game_id=game.id,
        pin=game.pin,
        question_index=game.current_question_index,
        question_count=len(game.question_ids_json),
        time_limit_seconds=game.time_limit_seconds,
    )

    if game.state == "waiting":
        players_result = await db.execute(
            select(LivePlayer)
            .where(LivePlayer.game_id == game.id)
            .order_by(LivePlayer.joined_at)
        )
        players = players_result.scalars().all()
        return GameStateOut(
            **base,
            players=[PlayerInLobby(nickname=p.nickname, avatar_color=p.avatar_color) for p in players],
        )

    if game.state == "question_active":
        q_id = game.question_ids_json[game.current_question_index]
        q_result = await db.execute(select(Question).where(Question.id == q_id))
        q = q_result.scalar_one_or_none()

        started_ms = int(game.current_question_started_at.timestamp() * 1000)
        time_remaining_ms = max(0, game.time_limit_seconds * 1000 - (_now_ms() - started_ms))

        ans_result = await db.execute(
            select(LiveAnswer).where(
                LiveAnswer.game_id == game.id,
                LiveAnswer.question_id == q_id,
            )
        )
        answered_count = len(ans_result.scalars().all())

        p_result = await db.execute(select(LivePlayer).where(LivePlayer.game_id == game.id))
        player_count = len(p_result.scalars().all())

        question_out = None
        if q:
            opts = q.options_json if isinstance(q.options_json, list) else None
            question_out = LiveQuestionOut(id=q.id, type=q.type, prompt_json=q.prompt_json, options_json=opts)

        return GameStateOut(
            **base,
            question=question_out,
            time_remaining_ms=time_remaining_ms,
            answered_count=answered_count,
            player_count=player_count,
        )

    if game.state == "question_closed":
        q_id = game.question_ids_json[game.current_question_index]
        q_result = await db.execute(select(Question).where(Question.id == q_id))
        q = q_result.scalar_one_or_none()

        rows = (await db.execute(
            select(LiveAnswer, LivePlayer)
            .join(LivePlayer, LiveAnswer.player_id == LivePlayer.id)
            .where(LiveAnswer.game_id == game.id, LiveAnswer.question_id == q_id)
            .order_by(LiveAnswer.points_earned.desc(), LiveAnswer.time_ms.asc())
        )).all()

        top_question = [
            LeaderboardEntry(
                nickname=player.nickname,
                avatar_color=player.avatar_color,
                points_earned=ans.points_earned,
                is_correct=ans.is_correct,
                total_score=player.total_score,
                rank=i + 1,
            )
            for i, (ans, player) in enumerate(rows[:10])
        ]

        correct_answer = q.correct_answer if q else None
        opts = (q.options_json if isinstance(q.options_json, list) else None) if q else None

        return GameStateOut(
            **base,
            correct_answer=correct_answer,
            options_json=opts,
            top_question=top_question,
        )

    if game.state == "finished":
        players_result = await db.execute(
            select(LivePlayer)
            .where(LivePlayer.game_id == game.id)
            .order_by(LivePlayer.total_score.desc())
        )
        players = players_result.scalars().all()
        top_cumulative = [
            LeaderboardEntry(
                nickname=p.nickname,
                avatar_color=p.avatar_color,
                points_earned=None,
                is_correct=None,
                total_score=p.total_score,
                rank=i + 1,
            )
            for i, p in enumerate(players[:20])
        ]
        return GameStateOut(**base, top_cumulative=top_cumulative)

    return GameStateOut(**base)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/games", status_code=status.HTTP_201_CREATED)
async def create_game(
    body: CreateGameRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    test_result = await db.execute(
        select(Test)
        .where(
            Test.id == body.test_id,
            Test.tenant_id == current_user.tenant_id,
            Test.deleted_at.is_(None),
        )
        .options(selectinload(Test.blocks).selectinload(TestBlock.block_questions))
    )
    test = test_result.scalar_one_or_none()
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    all_q_ids = [
        bq.question_id
        for block in sorted(test.blocks, key=lambda b: b.order)
        for bq in sorted(block.block_questions, key=lambda x: x.order)
    ]
    if not all_q_ids:
        raise HTTPException(status_code=400, detail="This test has no questions")

    q_result = await db.execute(select(Question).where(Question.id.in_(all_q_ids)))
    questions = {q.id: q for q in q_result.scalars().all()}
    live_q_ids = [qid for qid in all_q_ids if questions.get(qid) and questions[qid].type in LIVE_QUESTION_TYPES]

    if not live_q_ids:
        raise HTTPException(
            status_code=400,
            detail="Live games require multiple_choice or true_false questions. This test has none.",
        )

    # Generate unique PIN (not reused by any active game)
    pin = "000000"
    for _ in range(20):
        candidate = str(random.randint(100000, 999999))
        existing = await db.execute(
            select(LiveGame).where(LiveGame.pin == candidate, LiveGame.state != "finished")
        )
        if not existing.scalar_one_or_none():
            pin = candidate
            break

    game = LiveGame(
        test_id=test.id,
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        pin=pin,
        state="waiting",
        current_question_index=-1,
        question_ids_json=live_q_ids,
        time_limit_seconds=max(5, min(120, body.time_limit_seconds)),
    )
    db.add(game)
    await db.commit()
    await db.refresh(game)

    return {"game_id": game.id, "pin": game.pin, "question_count": len(live_q_ids)}


@router.get("/games/{game_id}/state", response_model=GameStateOut)
async def get_state(
    game_id: str,
    db: AsyncSession = Depends(get_db),
):
    game = await _get_game(game_id, db)

    # Auto-close if timer has expired
    if game.state == "question_active" and game.current_question_started_at:
        elapsed_ms = _now_ms() - int(game.current_question_started_at.timestamp() * 1000)
        if elapsed_ms >= game.time_limit_seconds * 1000:
            await _close_question(game, db)
            await db.commit()

    return await _build_state(game, db)


@router.post("/join")
async def join_game(
    body: JoinRequest,
    db: AsyncSession = Depends(get_db),
):
    pin = body.pin.strip()
    result = await db.execute(
        select(LiveGame).where(LiveGame.pin == pin, LiveGame.state == "waiting")
    )
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found or already started")

    nickname = body.nickname.strip()[:30]
    if not nickname:
        raise HTTPException(status_code=400, detail="Nickname cannot be empty")

    existing = await db.execute(
        select(LivePlayer).where(LivePlayer.game_id == game.id, LivePlayer.nickname == nickname)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="That nickname is already taken")

    p_count_result = await db.execute(select(LivePlayer).where(LivePlayer.game_id == game.id))
    p_count = len(p_count_result.scalars().all())
    avatar_color = AVATAR_COLORS[p_count % len(AVATAR_COLORS)]

    player = LivePlayer(game_id=game.id, nickname=nickname, avatar_color=avatar_color, total_score=0)
    db.add(player)
    await db.commit()
    await db.refresh(player)

    return {
        "game_id": game.id,
        "player_id": player.id,
        "nickname": player.nickname,
        "avatar_color": player.avatar_color,
    }


@router.post("/games/{game_id}/next")
async def advance_game(
    game_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    game = await _get_game(game_id, db)

    if game.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    now = datetime.now(timezone.utc)

    if game.state == "waiting":
        game.current_question_index = 0
        game.current_question_started_at = now
        game.state = "question_active"

    elif game.state == "question_active":
        await _close_question(game, db)

    elif game.state == "question_closed":
        next_index = game.current_question_index + 1
        if next_index >= len(game.question_ids_json):
            game.state = "finished"
        else:
            game.current_question_index = next_index
            game.current_question_started_at = now
            game.state = "question_active"

    elif game.state == "finished":
        raise HTTPException(status_code=400, detail="Game is already finished")

    await db.commit()
    return {"state": game.state, "question_index": game.current_question_index}


@router.post("/games/{game_id}/answer")
async def submit_answer(
    game_id: str,
    body: AnswerRequest,
    db: AsyncSession = Depends(get_db),
):
    game = await _get_game(game_id, db)
    if game.state != "question_active":
        raise HTTPException(status_code=400, detail="No active question right now")

    player_result = await db.execute(
        select(LivePlayer).where(LivePlayer.id == body.player_id, LivePlayer.game_id == game_id)
    )
    player = player_result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    q_id = game.question_ids_json[game.current_question_index]

    existing = await db.execute(
        select(LiveAnswer).where(
            LiveAnswer.game_id == game_id,
            LiveAnswer.player_id == body.player_id,
            LiveAnswer.question_id == q_id,
        )
    )
    if existing.scalar_one_or_none():
        return {"received": True, "already_answered": True}

    now = datetime.now(timezone.utc)
    time_ms = int((now - game.current_question_started_at).total_seconds() * 1000)
    time_ms = min(time_ms, game.time_limit_seconds * 1000)

    q_result = await db.execute(select(Question).where(Question.id == q_id))
    q = q_result.scalar_one_or_none()

    is_correct = False
    points_earned = 0
    if q:
        auto_score, _ = score_answer(q, body.value)
        is_correct = (auto_score or 0) > 0
        if is_correct:
            points_earned = _compute_points(q, time_ms, game.time_limit_seconds * 1000)
            player.total_score += points_earned

    db.add(LiveAnswer(
        game_id=game_id,
        player_id=body.player_id,
        question_id=q_id,
        value_json=body.value,
        answered_at=now,
        time_ms=time_ms,
        points_earned=points_earned,
        is_correct=is_correct,
    ))
    await db.commit()

    return {"received": True, "time_ms": time_ms}


@router.get("/games/{game_id}/player/{player_id}/result")
async def get_player_result(
    game_id: str,
    player_id: str,
    question_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    player_result = await db.execute(
        select(LivePlayer).where(LivePlayer.id == player_id, LivePlayer.game_id == game_id)
    )
    player = player_result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    ans_result = await db.execute(
        select(LiveAnswer).where(
            LiveAnswer.game_id == game_id,
            LiveAnswer.player_id == player_id,
            LiveAnswer.question_id == question_id,
        )
    )
    ans = ans_result.scalar_one_or_none()

    # Compute rank by total_score
    rank_result = await db.execute(
        select(LivePlayer)
        .where(LivePlayer.game_id == game_id, LivePlayer.total_score > player.total_score)
    )
    rank = len(rank_result.scalars().all()) + 1

    if not ans:
        return {"answered": False, "is_correct": False, "points_earned": 0, "total_score": player.total_score, "rank": rank}

    return {
        "answered": True,
        "is_correct": ans.is_correct,
        "points_earned": ans.points_earned,
        "time_ms": ans.time_ms,
        "total_score": player.total_score,
        "rank": rank,
    }
