from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password, require_role
from app.db import get_db
from app.models.core import User

router = APIRouter()

VALID_ROLES = {"admin", "manager", "reviewer", "candidate"}


class CreateUserRequest(BaseModel):
    email: str
    password: str
    role: str = "candidate"


class UserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_active: bool
    tenant_id: str


@router.get("", response_model=list[UserResponse])
async def list_users(
    user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.tenant_id == user.tenant_id).order_by(User.created_at)
    )
    return [
        UserResponse(id=u.id, email=u.email, role=u.role, is_active=u.is_active, tenant_id=u.tenant_id)
        for u in result.scalars().all()
    ]


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already in use")

    new_user = User(
        tenant_id=user.tenant_id,
        email=body.email,
        password_hash=hash_password(body.password),
        role=body.role,
        force_password_reset=True,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return UserResponse(
        id=new_user.id, email=new_user.email, role=new_user.role,
        is_active=new_user.is_active, tenant_id=new_user.tenant_id,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: str,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")

    target.is_active = False
    await db.commit()
