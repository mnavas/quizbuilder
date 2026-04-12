"""
Authentication and authorisation helpers.

Token strategy
--------------
Two JWTs are issued on login:
- Access token  (60 min)  — carries sub, tenant_id, role; sent on every API request
- Refresh token (30 days) — carries only sub; used to obtain a new access token

Both are stored as cookies on the client. The access token is read by the
axios interceptor in web/src/lib/api.ts and attached as a Bearer header.

Dependency injection
--------------------
  get_current_user   — decodes the access token and returns the active User row
  require_role(...)  — wraps get_current_user; raises 403 if role not in the list
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db
from app.models.core import User

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """Return a bcrypt hash of the plain-text password."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_token(data: dict, expires_delta: timedelta) -> str:
    """Encode a JWT with the given claims and an absolute expiry."""
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + expires_delta
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: str, tenant_id: str, role: str) -> str:
    """
    Issue a short-lived access token.
    The token carries tenant_id and role so endpoints can authorise without an
    extra DB round-trip.
    """
    return create_token(
        {"sub": user_id, "tenant_id": tenant_id, "role": role, "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> str:
    """
    Issue a long-lived refresh token.
    Only contains sub (user_id) — the full claims are re-fetched from DB on refresh.
    """
    return create_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency — decode the Bearer token and return the authenticated User.
    Raises 401 if the token is missing, invalid, expired, or belongs to an
    inactive user. Rejects refresh tokens presented as access tokens.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise JWTError
        user_id: str = payload.get("sub")
        if not user_id:
            raise JWTError
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*roles: str):
    """
    FastAPI dependency factory — gate an endpoint to specific roles.

    Usage::

        @router.get("/admin-only")
        async def endpoint(user: User = Depends(require_role("admin"))):
            ...

    Raises 403 if the authenticated user's role is not in the allowed list.
    """
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return _check
